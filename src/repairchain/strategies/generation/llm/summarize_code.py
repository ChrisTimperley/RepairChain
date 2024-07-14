from __future__ import annotations

__all__ = ("CodeSummary", "FunctionSummary", "ReportSummary")

import json
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
from repairchain.strategies.generation.llm.llm import LLM
from repairchain.strategies.generation.llm.util import Util

if t.TYPE_CHECKING:
    from repairchain.models.diagnosis import Diagnosis
    from repairchain.models.diff import Diff
    from repairchain.strategies.generation.llm.util import MessagesIterable

PREFILL_SUMMARY = ("{\n"
                   '"report": [\n'
                   "{\n")

CONTEXT_SUMMARY = """The following Git commit introduces a memory vulnerability:
<git-commit>
{diff}
</git-commit>
The sanitizer {sanitizer} has the following report for this memory vulnerability:
<sanitizer-report>
{sanitizer_report}
</sanitizer-report>
The source code of the files {code_files} modified by this Git commit are the following:
<code>
{code_context}
</code>
Only one of the functions {code_functions} is vulnerable.
<instructions>
Create a JSON object which enumerates all modified functions from {code_functions}.
The parent object is called "report" that corresponds to a list of code function analyses.
Each child object has the following properties:
- A property named "function_name" with a function from {code_functions}
- A property named "filename" with the corresponding filename from {code_files}
- A property named "summary" with a summary of that function
- A property named "recommendations" with recommendations to fix potential vulnerabilities
- A property named "cwe" with one or more CWEs among {cwe_c} for C code and {cwe_java} for Java code
If there are no vulnerabilities then "cwe" property should be "None"
</instructions>
"""


@dataclass
class FunctionSummary:
    function_name: str
    filename: str
    summary: str
    recommendations: str
    cwe: str


@dataclass
class CodeSummary:
    report: list[FunctionSummary]


@dataclass
class ReportSummary:
    model: str

    def __init__(self, model: str) -> None:
        self.model = model

    def _call_llm_summarize_code(self, llm_object: LLM, messages: MessagesIterable) -> str:
        summary = llm_object._call_llm_json(messages)
        if summary is None:
            return ""
        return summary

    def _create_user_prompt(self, diagnosis: Diagnosis,
                            files: dict[str, str],
                            diff: Diff, function_names: list[str]) -> str:
        code_context = "\n".join(
            f"<file:{filename}>\n{contents}\n</file:{filename}>"
            for filename, contents in files.items()
        )

        cwe_c = "CWE-125, CWE-787, CWE-119, CWE-416, CWE-415, CWE-476, CWE-190"
        cwe_java = "CWE-22, CWE-77, CWE-78, CWE-94, CWE-190, CWE-434, CWE-502, CWE-918"

        sanitizer_report: str = diagnosis.sanitizer_report.contents
        sanitizer: str = diagnosis.sanitizer_report._find_sanitizer(sanitizer_report)
        sanitizer_report_tokens: int = Util.count_tokens(sanitizer_report, self.model)

        if sanitizer_report_tokens > Util.sanitizer_report_size:
            logger.info(f"sanitizer report larger then limit: {sanitizer_report_tokens} tokens")
            sanitizer_report = ""  # report is too large to be considered

        return CONTEXT_SUMMARY.format(
            diff=diff,
            sanitizer=sanitizer,
            code_files=list(files.keys()),
            code_context=code_context,
            sanitizer_report=sanitizer_report,
            code_functions=function_names,
            cwe_c=cwe_c,
            cwe_java=cwe_java,
        )

    # FIXME: create some examples for few-shot of format and CWE
    def _create_system_prompt(self) -> str:
        return """
        You are an expert security analyst.
        You can find security vulnerabilities and CWEs related to vulnerable code.
        You can also suggest recommendations to fix them.
        You always provide an output in valid JSON.
        The resulting JSON object should be in this format:
        {
        "report": [
            {
            "function_name": "string",
            "filename": "string",
            "summary": "string",
            "recommendations": "string",
            "cwe": "string"
            },
            {
            "function_name": "string",
            "filename": "string",
            "summary": "string",
            "recommendations": "string",
            "cwe": "string"
            }
        ]
        }
        """

    def _check_prefill(self, messages: MessagesIterable) -> None:
        if self.model == "claude-3.5-sonnet":
            # force a prefill for clause-3.5
            prefill_message = ChatCompletionAssistantMessageParam(role="assistant", content=PREFILL_SUMMARY)
            messages.append(prefill_message)

    def _get_llm_code_report(self, diagnosis: Diagnosis) -> list[FunctionSummary] | None:

        diff = commit_to_diff.commit_to_diff(diagnosis.project.triggering_commit)
        files = commit_to_diff.commit_to_files(diagnosis.project.triggering_commit, diff)
        user_prompt = self._create_user_prompt(diagnosis, files, diff,
                                               Util.implied_functions_to_str(diagnosis))
        system_prompt = self._create_system_prompt()
        llm = LLM.from_settings(diagnosis.project.settings, model=self.model)

        logger.debug(f"system prompt tokens: {Util.count_tokens(system_prompt, self.model)}")
        logger.debug(f"system prompt: {system_prompt}")
        logger.debug(f"user prompt tokens: {Util.count_tokens(user_prompt, self.model)}")
        logger.debug(f"user prompt: {user_prompt}")

        messages: MessagesIterable = []
        system_message = ChatCompletionSystemMessageParam(role="system", content=system_prompt)
        user_message = ChatCompletionUserMessageParam(role="user", content=user_prompt)
        messages.append(system_message)
        messages.append(user_message)

        self._check_prefill(messages)

        retry_attempts = Util.retry_attempts
        for attempt in range(retry_attempts):
            try:
                llm_output = ""
                if self.model == "claude-3.5-sonnet":
                    llm_output += PREFILL_SUMMARY
                    llm_call = llm._call_llm_json(messages)
                    if llm_call is None:
                        return None
                    llm_output += llm_call
                else:
                    llm_call = llm._call_llm_json(messages)
                    if llm_call is None:
                        return None
                    llm_output = llm_call

                logger.debug(f"output prompt tokens: {Util.count_tokens(llm_output, self.model)}")

                logger.debug(f"LLM output in JSON: {llm_output}")

                # Parse the JSON string into a dictionary
                data = json.loads(llm_output)

                # Convert each dictionary in the 'report' list to an instance of FunctionSummary
                return [FunctionSummary(**item) for item in data["report"]]

            # TODO: test if the these error handling is working properly
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to decode JSON: {e}. Retrying {attempt + 1}/{retry_attempts}...")
                messages.append(ChatCompletionAssistantMessageParam(role="assistant", content=llm_output))
                error_message = (
                    f"The JSON is not valid. Failed to decode JSON: {e}."
                    "Please fix the issue and return a fixed JSON.")
                messages.append(ChatCompletionUserMessageParam(role="user", content=error_message))
                self._check_prefill(messages)

            except KeyError as e:
                logger.warning(f"Missing expected key in JSON data: {e}. Retrying {attempt + 1}/{retry_attempts}...")
                messages.append(ChatCompletionAssistantMessageParam(role="assistant", content=llm_output))
                error_message = (f"The JSON is not valid. Missing expected key in JSON data: {e}."
                                "Please fix the issue and return a fixed JSON.")
                messages.append(ChatCompletionUserMessageParam(role="user", content=error_message))
                self._check_prefill(messages)

            except TypeError as e:
                logger.warning(f"Unexpected type encountered: {e}. Retrying {attempt + 1}/{retry_attempts}...")
                messages.append(ChatCompletionAssistantMessageParam(role="assistant", content=llm_output))
                error_message = (f"The JSON is not valid. Unexpected type encountered: {e}."
                                "Please fix the issue and return a fixed JSON.")
                messages.append(ChatCompletionUserMessageParam(role="user", content=error_message))
                self._check_prefill(messages)

            # Wait briefly before retrying
            time.sleep(Util.short_sleep)

        # If all attempts fail, return None
        return None
