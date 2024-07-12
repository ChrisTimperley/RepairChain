from __future__ import annotations

import json
import typing as t
from dataclasses import dataclass

from openai.types.chat import (
    ChatCompletionSystemMessageParam,
    ChatCompletionUserMessageParam,
)

if t.TYPE_CHECKING:
    from repairchain.strategies.generation.llm.llm import LLM
    from repairchain.strategies.generation.llm.util import MessagesIterable


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
        You can find security vulnerabilities related to memory.
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

    def _create_memory_alloc_prompt(self, context: str, code: str, line: str) -> str:
        return context.format(
            code=code,
            line=line,
            number_patches=5,
        )

    def help_with_memory_allocation(self, code: str, line: str) -> Code:
        system_prompt = self._create_system_prompt()
        user_prompt = self._create_memory_alloc_prompt(CONTEXT_MEMORY, code, line)

        messages: MessagesIterable = []
        system_message = ChatCompletionSystemMessageParam(role="system", content=system_prompt)
        user_message = ChatCompletionUserMessageParam(role="user", content=user_prompt)
        messages.append(system_message)
        messages.append(user_message)

        llm_output = self.llm._call_llm_json(messages)

        # Parse the JSON string into a dictionary
        data = json.loads(llm_output)

        patch_contents = [LineCode(**item) for item in data["code"]]

        return Code(code=patch_contents)

    def _create_bounds_check_prompt(self, context: str, code: str, line: str, varname: str) -> str:
        return context.format(
            code=code,
            line=line,
            varname=varname,
            number_patches=5,
        )

    def help_with_bounds_check(self, code: str, line: str, varname: str) -> Code:
        system_prompt = self._create_system_prompt()
        user_prompt = self._create_bounds_check_prompt(CONTEXT_BOUNDS, code, line, varname)

        messages: MessagesIterable = []
        system_message = ChatCompletionSystemMessageParam(role="system", content=system_prompt)
        user_message = ChatCompletionUserMessageParam(role="user", content=user_prompt)
        messages.append(system_message)
        messages.append(user_message)

        llm_output = self.llm._call_llm_json(messages)

        # Parse the JSON string into a dictionary
        data = json.loads(llm_output)

        patch_contents = [LineCode(**item) for item in data["code"]]

        return Code(code=patch_contents)
