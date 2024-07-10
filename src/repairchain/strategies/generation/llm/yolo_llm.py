from __future__ import annotations

import json
import math
import time
import typing as t
from dataclasses import dataclass

from loguru import logger
from openai.types.chat import (
    ChatCompletionAssistantMessageParam,
    ChatCompletionSystemMessageParam,
    ChatCompletionUserMessageParam,
)

from repairchain.actions import commit_to_diff
from repairchain.strategies.generation.base import PatchGenerationStrategy
from repairchain.strategies.generation.llm.llm import LLM
from repairchain.strategies.generation.llm.summarize_code import FunctionSummary, ReportSummary
from repairchain.strategies.generation.llm.util import (
    FileLines,
    MessagesIterable,
    PatchFile,
    RepairedFileContents,
    Util,
)

if t.TYPE_CHECKING:
    from repairchain.models.diagnosis import Diagnosis
    from repairchain.models.diff import Diff

# TODO try a version with conversation
CONTEXT_YOLO = """The following Git commit introduce a memory vulnerability:
<git-commit>
{diff}
</git-commit>
The source code of the files {code_files} modified by this Git commit is the following:
<code>
{code_context}
</code>
{analyst_report}
Only one of the files is buggy.
Please fix the buggy file and return a modified version of the code with the following properties:
- The repair is minimal
- Do not add comments
- Keep the same functionality of the code
- Do not modify the code unless it is to fix the bug
- Only modify the buggy file
- The buggy function is one of the following {code_functions}
- The modified code should only contain the buggy function
- Keep the same indentation as the original file
- Return the entire modified function without abbreviations
- Return {number_patches} potential bug fixes. These can be different functions among {code_functions}
<instructions>
Create a JSON object which enumerates all patched functions from {code_functions}.
The parent object is called "patch" that corresponds to a list of modified code.
Each child object has the modified code with the following properties:
- A property named "function_name" with a function from {code_functions}
- A property named "filename" with the corresponding filename from {code_files}
- A property named "code" with modified code that fixes the bug.
There must be {number_patches} children, each corresponding to a modified code.
</instructions>
"""


@dataclass
class FunctionContext:
    context: str
    size: int
    max_function_size: int


@dataclass
class YoloLLMStrategy(PatchGenerationStrategy):
    diagnosis: Diagnosis
    model: str
    use_report: bool  # option to use report in context
    use_context_files: bool  # option to use full files in context
    llm: LLM
    diff: Diff
    files: dict[str, str]

    @classmethod
    def build(
        cls,
        diagnosis: Diagnosis,
    ) -> YoloLLMStrategy:
        model = "oai-gpt-4o"
        llm = LLM.from_settings(diagnosis.project.settings, model=model)
        diff = commit_to_diff.commit_to_diff(diagnosis.project.triggering_commit)
        files = commit_to_diff.commit_to_files(diagnosis.project.head, diff)

        return cls(
            diagnosis=diagnosis,
            model=model,
            use_report=True,
            use_context_files=True,
            llm=llm,
            diff=diff,
            files=files,
        )

    def _set_model(self, model: str) -> None:
        self.model = model
        self.llm.model = model

    def _set_use_report(self, report: bool) -> None:
        self.use_report = report

    def _set_use_context_files(self, files: bool) -> None:
        self.use_context_files = files

    def _create_sanitizer_report_prompt(self, summary: list[FunctionSummary] | None) -> str:

        if summary is None:
            return ""

        # TODO: see if cwe has an impact on the prompt ; seems unreliable
        code_summary = (
            "\n<analyst-report>\n"
            "A security analyst analyzed the code and gave the following recommendations to fix it:\n"
            )
        for code in summary:
            code_summary += (
                f"<function:{code.function_name}>\n"
                f"<filename> {code.filename} </filename>\n"
                f"<function-summary>\n{code.summary}\n</function-summary>\n"
                f"<analyst-recommendations>\n{code.recommendations}\n</analyst-recommendations>\n"
                f"</function:{code.function_name}>\n"
            )

        code_summary += "</analyst-report>\n"
        return code_summary

    def _create_function_context(self, function_names: list[str]) -> FunctionContext:
        code_context = "\n"
        max_function_size = 0
        max_function_name = ""
        max_function_filename = ""

        for name in function_names:
            fl: FileLines | None = Util.extract_begin_end_lines(self.diagnosis, name)
            filename: str | None = Util.function_to_filename(self.diagnosis, name)
            if fl is None:
                logger.info(f"function was not found: {name}")
                continue

            if filename is None:
                logger.info(f"filename was not found: {filename}")
                continue

            # Check if the key 'filename' exists in the dictionary files
            if filename in self.files:
                contents = Util.extract_lines_between_indices(self.files[filename], fl.begin, fl.end)
            else:
                # Handle the case where the key 'name' does not exist
                logger.info(f"Key {name} does not exist in the dictionary files.")
                logger.info(f"keys {print(list(self.files.keys()))}")
                contents = ""

            if contents is None:
                logger.info(f"Could not extract function {name} from {filename}")
                contents = ""

            logger.debug(f"Contents of function: {contents}")

            current_function_size = Util.count_tokens(contents, self.model)
            if current_function_size > max_function_size:
                max_function_size = current_function_size
                max_function_name = name
                max_function_filename = filename

            code_context += (rf"<file:{filename}>\n{contents}\</file:{filename}>\n")
            logger.debug(f"Contents of context: {code_context}")

        logger.info(f"Function {max_function_name} in {max_function_filename} needs {max_function_size} tokens")

        return FunctionContext(code_context,
                               Util.count_tokens(code_context, self.model),
                               max_function_size)

    def _create_user_prompt(self, function_names: list[str], sanitizer_prompt: str, number_patches: int) -> str:

        code_context = "\n"
        function_context: FunctionContext = self._create_function_context(function_names)

        if self.use_context_files:
            code_context = "\n".join(
                f"<file:{filename}>\n{contents}\n</file:{filename}>"
                for filename, contents in self.files.items()
            )
        else:
            code_context = function_context.context

        local_number_patches = number_patches
        llm_limit = (Util.limit_llm_output / 2)  # being conservative since output has more than code
        if function_context.max_function_size * number_patches > llm_limit:
            logger.info(f"Function too large to ask for {number_patches} patches")
            if function_context.max_function_size > llm_limit:
                logger.info("Function too large to ask for one patch!")
                local_number_patches = 0
            else:
                local_number_patches = max(1, math.floor(llm_limit / function_context.max_function_size))
                logger.info(f"Changed the number of patches to {local_number_patches}")

        return CONTEXT_YOLO.format(
            diff=self.diff,
            code_files=list(self.files.keys()),
            analyst_report=sanitizer_prompt,
            code_context=code_context,
            code_functions=function_names,
            number_patches=local_number_patches,
        )

    # FIXME: create some examples for few-shot of format
    def _create_system_prompt(self) -> str:
        return """
        You are an expert security analyst.
        You can find security vulnerabilities and suggest patches to fix them.
        You always do minimal changes to the code.
        You always provide an output in valid JSON.
        The resulting JSON object should be in this format:
        {
        "patch": [
            {
            "function_name": "string",
            "filename": "string",
            "code": "string"
            },
            {
            "function_name": "string",
            "filename": "string",
            "code": "string"
            },
            {
            "function_name": "string",
            "filename": "string",
            "code": "string"
            }
            ]
        }
        """

    # TODO: refactor code to minimize duplication
    def _get_llm_output(self, user_prompt: str, system_prompt: str) -> PatchFile | None:

        logger.info(f"user prompt tokens: {Util.count_tokens(user_prompt, self.model)}")
        logger.info(f"system prompt tokens: {Util.count_tokens(system_prompt, self.model)}")

        messages: MessagesIterable = []
        system_message = ChatCompletionSystemMessageParam(role="system", content=system_prompt)
        user_message = ChatCompletionUserMessageParam(role="user", content=user_prompt)
        messages.append(system_message)
        messages.append(user_message)

        retry_attempts = Util.retry_attempts
        for attempt in range(retry_attempts):
            try:
                llm_output = self.llm._call_llm_json(messages)
                logger.info(f"output prompt tokens: {Util.count_tokens(llm_output, self.model)}")
                logger.debug(f"LLM output in JSON: {llm_output}")

                # Parse the JSON string into a dictionary
                data = json.loads(llm_output)

                # Convert each dictionary in the 'patch' list to an instance of RepairedFileContents
                patch_contents = [RepairedFileContents(**item) for item in data["patch"]]

                return PatchFile(patch=patch_contents)

            # TODO: test if the error handling is working properly
            except json.JSONDecodeError as e:
                logger.info(f"Failed to decode JSON: {e}. Retrying {attempt + 1}/{retry_attempts}...")
                messages.append(ChatCompletionAssistantMessageParam(role="assistant", content=llm_output))
                error_message = (
                    f"The JSON is not valid. Failed to decode JSON: {e}."
                    "Please fix the issue and return a fixed JSON.")
                messages.append(ChatCompletionUserMessageParam(role="user", content=error_message))
            except KeyError as e:
                logger.info(f"Missing expected key in JSON data: {e}. Retrying {attempt + 1}/{retry_attempts}...")
                messages.append(ChatCompletionAssistantMessageParam(role="assistant", content=llm_output))
                error_message = (f"The JSON is not valid. Missing expected key in JSON data: {e}."
                                "Please fix the issue and return a fixed JSON.")
                messages.append(ChatCompletionUserMessageParam(role="user", content=error_message))
            except TypeError as e:
                logger.info(f"Unexpected type encountered: {e}. Retrying {attempt + 1}/{retry_attempts}...")
                messages.append(ChatCompletionAssistantMessageParam(role="assistant", content=llm_output))
                error_message = (f"The JSON is not valid. Unexpected type encountered: {e}."
                                "Please fix the issue and return a fixed JSON.")
                messages.append(ChatCompletionUserMessageParam(role="user", content=error_message))

            # Wait briefly before retrying
            time.sleep(Util.short_sleep)

        # If all attempts fail, return None
        return None

    def run(self) -> list[Diff]:
        summary: ReportSummary = ReportSummary()
        code_summary: list[FunctionSummary] | None = None
        if self.use_report:
            code_summary = summary._get_llm_code_report(self.diagnosis)

        system_prompt = self._create_system_prompt()

        sanitizer_prompt = self._create_sanitizer_report_prompt(code_summary)

        # TODO: maybe change the number of patches to be dynamic depending on size
        # FIXME: check the size of the user context
        user_prompt = self._create_user_prompt(Util.implied_functions_to_str(self.diagnosis),
                                               sanitizer_prompt,
                                               Util.number_patches)

        logger.info(f"system prompt tokens: {Util.count_tokens(system_prompt, self.model)}")
        logger.debug(f"system prompt: {system_prompt}")
        logger.info(f"user prompt tokens: {Util.count_tokens(user_prompt, self.model)}")
        logger.debug(f"user prompt: {user_prompt}")

        sanitizer_prompt = self._create_sanitizer_report_prompt(code_summary)

        repaired_files: PatchFile | None = self._get_llm_output(user_prompt, system_prompt)
        if repaired_files is None:
            return []
        return Util.extract_patches(self.diagnosis, self.files, repaired_files.patch)
