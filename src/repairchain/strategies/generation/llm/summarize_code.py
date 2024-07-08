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

CONTEXT_SUMMARY = """The following Git commit introduces a memory vulnerability:
BEGIN GIT COMMIT
{diff}
END GIT COMMIT
The sanitizer {sanitizer} has the following report for this memory vulnerability:
BEGIN SANITIZER REPORT
{sanitizer_report}
END SANITIZER REPORT
The source code of the files modified by this Git commit are the following:
BEGIN CODE
{code_context}
END CODE
Only one of the functions {code_functions} is vulnerable.
BEGIN INSTRUCTIONS
Create a JSON object which enumerates all modified functions from {code_functions}.
Each parent object corresponds to a function from {code_functions}.
Each child object has the following properties:
- A property named "name" with a function from {code_functions}
- A property named "summary" with a summary of that function
- A property named "recommendations" with recommendations to fix potential vulnerabilities
- A property named "cwe" with one or more CWEs among {cwe_c} for C code and {cwe_java} for Java code
If there are no vulnerabilities then "cwe" property should be "None"
END INSTRUCTIONS
"""


@dataclass
class FunctionSummary:
    name: str
    summary: str
    recommendations: str
    cwe: str


@dataclass
class CodeSummary:
    function: FunctionSummary


@dataclass
class ReportSummary:
    model: str

    def __init__(self, model: str = "oai-gpt-4o") -> None:
        self.model = model

    def _call_llm_summarize_code(self, llm_object: LLM, messages: MessagesIterable) -> str:
        return llm_object._call_llm_json(messages)

    def _create_user_prompt(self, diagnosis: Diagnosis, files: dict[str, str], diff: Diff, function_names: str) -> str:
        code_context = "\n".join(
            f"BEGIN FILE: {filename}\n{contents}\nEND FILE"
            for filename, contents in files.items()
        )

        cwe_c = "CWE-125, CWE-787, CWE-119, CWE-416, CWE-415, CWE-476, CWE-190"
        cwe_java = "CWE-22, CWE-77, CWE-78, CWE-94, CWE-190, CWE-434, CWE-502, CWE-918"

        sanitizer_report: str = diagnosis.sanitizer_report.contents
        sanitizer: str = diagnosis.sanitizer_report._find_sanitizer(sanitizer_report)
        sanitizer_report_tokens: int = Util.count_tokens(sanitizer_report)

        if sanitizer_report_tokens > Util.context_size:
            logger.info(f"report tokens is larger then limit: {sanitizer_report_tokens}")
            sanitizer_report = ""  # report is too large to be considered

        return CONTEXT_SUMMARY.format(
            diff=diff,
            sanitizer=sanitizer,
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
        "function": {
            "name": "string",
            "summary": "string",
            "recommendations": "string",
            "cwe": [
            "string"
            ]
        }
        }
        """

    def _get_llm_code_report(self, diagnosis: Diagnosis) -> CodeSummary | None:

        diff = commit_to_diff.commit_to_diff(diagnosis.project.triggering_commit)
        files = commit_to_diff.commit_to_files(diagnosis.project.head, diff)
        function_names = ", ".join(
            function_diagnosis.name for function_diagnosis in diagnosis.implicated_functions_at_head)
        user_prompt = self._create_user_prompt(diagnosis, files, diff, function_names)
        system_prompt = self._create_system_prompt()
        llm = LLM(self.model)

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
                llm_output = llm._call_llm_json(messages)
                logger.info(f"output prompt tokens: {Util.count_tokens(llm_output, self.model)}")

                # Parse the JSON string into a dictionary
                data = json.loads(llm_output)

                # Convert the dictionary to an instance of the dataclass
                return CodeSummary(function=FunctionSummary(**data["function"]))

            # TODO: test if the these error handling is working properly
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
