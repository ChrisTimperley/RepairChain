from __future__ import annotations

import json
import typing as t
from dataclasses import dataclass

from loguru import logger
from openai.types.chat import (
    ChatCompletionAssistantMessageParam,
    ChatCompletionSystemMessageParam,
    ChatCompletionUserMessageParam,
)

from repairchain.strategies.generation.llm.util import Util

if t.TYPE_CHECKING:
    from repairchain.strategies.generation.llm.llm import LLM
    from repairchain.strategies.generation.llm.util import MessagesIterable

PREFILL_HELPER = ("{\n"
                '"code": [\n'
                "{"
                )

# TODO: I actually think that it makes more sense to put these strings into the individual
# templates using them, but it's nice to have them here for now to make it easy for CLG to ask
# RM for feedback/improvement.

CONTEXT_MEMORY = """
The following code has a memory vulnerability related to memory allocation:
{code}
The following line has an issue with memory allocation:
{line}
<instructions>
Fix the line by increasing the allocation while keeping the same allocation function.
Create a JSON object that changes the line.
The parent object is called "code" that corresponds to fixes for the line of code.
Each child object has the following properties:
- A property named "line" with a modified code line
There must be {number_patches} children, each corresponding to a modified line.
</instructions>
"""

CONTEXT_UNINIT_MEMORY = """
The following code has a security vulnerability related to uninitialized memory access:
{code}
The following line has an issue with accessing uninitialized memory:
{line}
<instructions>
Fix the line by creating a new line of code that initializes the memory.
Create a JSON object with the new line of code.
The parent object is called "code" that corresponds to fixes for the line of code.
Each child object has the following properties:
- A property named "line" with a modified code line
There must be {number_patches} children, each corresponding to a modified line.
</instructions>
"""


CONTEXT_BOUNDS = """
The following code has a memory vulnerability related to memory allocation:
{code}
The following line has an issue with memory access:
{line}
The variable being accessed incorrectly is:
{varname}
<instructions>
Provide a bounds check on {varname} to be inserted before the memory access that cleans up
and returns from the function if the access is unsafe.
Create a JSON object with the new line of code.
The parent object is called "code" that corresponds to fixes for the line of code.
Each child object has the following properties:
- A property named "line" with a modified code line
There must be {number_patches} children, each corresponding to a modified line.
</instructions>
"""

CONTEXT_UPCAST_NO_HELPER = """
The following code has a vulnerability related to an integer overflow:
{code}
The following line has the issue with an integer overflow:
{line}
The variable being overflowed is:
{varname}
<instructions>
Rewrite the vulnerable line of code to upcast the variable {varname} such that
the overflow is avoided.
Create a JSON object with the new line of code.
The parent object is called "code" that corresponds to fixes for the line of code.
Each child object has the following properties:
- A property named "line" with a modified code line
There must be {number_patches} children, each corresponding to a modified line.
</instructions>
"""


CONTEXT_UPCAST_HELPER_DECL = """
The following code has a vulnerability related to an overflow of type {type_str}:
{code}
The variable being overflowed is declared by the following variable declaration:
{decl}
<instructions>
Rewrite the variable declaration code so that instead of type {type_str}, the variable is of type {uptype}.
Create a JSON object with the new line of code.
The parent object is called "code" that corresponds to fixes for the variable declaration code line.
Each child object has the following properties:
- A property named "line" with a modified code line
There must be {number_patches} children, each corresponding to a modified line.
</instructions>
"""

CONTEXT_UPCAST_HELPER_EXPR = """
The following code has a vulnerability related to an integer overflow:
{code}
The expression being overflowed is:
{expression}
<instructions>
Rewrite the code to upcast the subexpressions in the overflowing expression to type {uptype},
so that the overall expression does not overflow type {type_str}.
Create a JSON object with the new line of code containing the modified expression.
The parent object is called "code" that corresponds to fixes for the line of code.
Each child object has the following properties:
- A property named "line" with a modified code line
There must be {number_patches} children, each corresponding to a modified line.
</instructions>
"""


@dataclass
class LineCode:
    line: str


@dataclass
class Code:
    code: list[LineCode]

# Usage example:
# llm = LLM.from_settings(diagnosis.project.settings)
# helper = CodeHelper(llm)
# output = helper.help_with_memory_allocation(code, "int *array = (int *)malloc(n);")


@dataclass
class CodeHelper:
    llm: LLM

    def _create_system_prompt(self) -> str:
        return """
        You are an expert security analyst.
        You can find security vulnerabilities.
        You always provide an output in valid JSON.
        The resulting JSON object should be in this format:
        {
        "code": [
            {
            "line": "string"
            },
            {
            "line": "string"
            }
        ]
        }
        """

    def _help_with_template(self, user_prompt: str) -> Code | None:
        system_prompt = self._create_system_prompt()

        messages: MessagesIterable = []
        system_message = ChatCompletionSystemMessageParam(role="system", content=system_prompt)
        user_message = ChatCompletionUserMessageParam(role="user", content=user_prompt)
        messages.append(system_message)
        messages.append(user_message)

        # TODO: code that we use in yolo_llm;  refactor later
        # claude-3.5-sonnet is not as good for JSON and requires some prefill
        retry_attempts = Util.retry_attempts
        for attempt in range(retry_attempts):
            try:
                llm_output = ""
                if self.llm.model == "claude-3.5-sonnet":
                    llm_output += PREFILL_HELPER
                    llm_output += self.llm._call_llm_json(messages)
                else:
                    llm_output = self.llm._call_llm_json(messages)

                logger.info(f"output prompt tokens: {Util.count_tokens(llm_output, self.llm.model)}")
                logger.debug(f"LLM output in JSON: {llm_output}")

                # Parse the JSON string into a dictionary
                data = json.loads(llm_output)

                patch_contents = [LineCode(**item) for item in data["code"]]

                return Code(code=patch_contents)

            except json.JSONDecodeError as e:
                logger.info(f"Failed to decode JSON: {e}. Retrying {attempt + 1}/{retry_attempts}...")
                messages.append(ChatCompletionAssistantMessageParam(role="assistant", content=llm_output))
                error_message = (
                    f"The JSON is not valid. Failed to decode JSON: {e}."
                    "Please fix the issue and return a fixed JSON.")
                messages.append(ChatCompletionUserMessageParam(role="user", content=error_message))

                if self.llm.model == "claude-3.5-sonnet":
                    # force a prefill for clause-3.5
                    prefill_message = ChatCompletionAssistantMessageParam(role="assistant", content=PREFILL_HELPER)
                    messages.append(prefill_message)

            except KeyError as e:
                logger.info(f"Missing expected key in JSON data: {e}. Retrying {attempt + 1}/{retry_attempts}...")
                messages.append(ChatCompletionAssistantMessageParam(role="assistant", content=llm_output))
                error_message = (f"The JSON is not valid. Missing expected key in JSON data: {e}."
                                "Please fix the issue and return a fixed JSON.")
                messages.append(ChatCompletionUserMessageParam(role="user", content=error_message))

                if self.llm.model == "claude-3.5-sonnet":
                    # force a prefill for clause-3.5
                    prefill_message = ChatCompletionAssistantMessageParam(role="assistant", content=PREFILL_HELPER)
                    messages.append(prefill_message)

            except TypeError as e:
                logger.info(f"Unexpected type encountered: {e}. Retrying {attempt + 1}/{retry_attempts}...")
                messages.append(ChatCompletionAssistantMessageParam(role="assistant", content=llm_output))
                error_message = (f"The JSON is not valid. Unexpected type encountered: {e}."
                                "Please fix the issue and return a fixed JSON.")
                messages.append(ChatCompletionUserMessageParam(role="user", content=error_message))

                if self.llm.model == "claude-3.5-sonnet":
                    # force a prefill for clause-3.5
                    prefill_message = ChatCompletionAssistantMessageParam(role="assistant", content=PREFILL_HELPER)
                    messages.append(prefill_message)

        return None

    def help_with_memory_allocation(self, code: str, line: str) -> Code | None:
        user_prompt = CONTEXT_MEMORY.format(
            code=code,
            line=line,
            number_patches=5,
        )
        return self._help_with_template(user_prompt)

    def help_with_memory_initialization(self, code: str, line: str) -> Code | None:
        user_prompt = CONTEXT_UNINIT_MEMORY.format(
            code=code,
            line=line,
            number_patches=5,
        )
        return self._help_with_template(user_prompt)

    def help_with_bounds_check(self, code: str, line: str, varname: str) -> Code | None:
        user_prompt = CONTEXT_BOUNDS.format(
            code=code,
            line=line,
            varname=varname,
            number_patches=5,
        )
        return self._help_with_template(user_prompt)

    def help_with_upcast_no_info(self, code: str, line: str, varname: str) -> Code | None:
        user_prompt = CONTEXT_UPCAST_NO_HELPER.format(
            code=code,
            line=line,
            varname=varname,
            number_patches=5,
        )
        return self._help_with_template(user_prompt)

    def help_with_upcast_decl(self, code: str, decl: str, type_str: str, uptype: str) -> Code | None:
        user_prompt = CONTEXT_UPCAST_HELPER_DECL.format(
            code=code,
            decl=decl,
            type_str=type_str,
            uptype=uptype,
            number_patches=5,
        )
        return self._help_with_template(user_prompt)

    def help_with_upcast_expr(self, code: str, expression: str, type_str: str, uptype: str) -> Code | None:
        user_prompt = CONTEXT_UPCAST_HELPER_EXPR.format(
            code=code,
            expression=expression,
            type_str=type_str,
            uptype=uptype,
            number_patches=5,
        )
        return self._help_with_template(user_prompt)
