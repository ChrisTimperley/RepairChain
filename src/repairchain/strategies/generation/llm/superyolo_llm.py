from __future__ import annotations

import difflib
import typing as t
from dataclasses import dataclass

from loguru import logger
from openai.types.chat import (
    ChatCompletionAssistantMessageParam,
    ChatCompletionSystemMessageParam,
    ChatCompletionUserMessageParam,
)

from repairchain.actions import commit_to_diff
from repairchain.models.diff import Diff
from repairchain.strategies.generation.base import PatchGenerationStrategy
from repairchain.strategies.generation.llm.llm import LLM
from repairchain.strategies.generation.llm.util import MessagesIterable, Util

if t.TYPE_CHECKING:
    from repairchain.models.diagnosis import Diagnosis

PATCH_FORMAT = """
<patch-format>

Return edits similar to unified diffs that `diff -U0` would produce.

Make sure you include the first 2 lines with the file paths.
Don't include timestamps with the file paths.

Start each hunk of changes with a `@@ ... @@` line.
Don't include line numbers like `diff -U0` does.
The user's patch tool doesn't need them.

The user's patch tool needs CORRECT patches that apply cleanly against the current contents of the file!
Think carefully and make sure you include and mark all lines that need to be removed or changed as `-` lines.
Make sure you mark all new or modified lines with `+`.
Don't leave out any lines or the diff patch won't apply correctly.

Indentation matters in the diffs!

Your patch must only have one hunk!

When editing a function, method, loop, etc use a hunk to replace the *entire* code block.
Delete the entire existing version with `-` lines and then add a new, updated version with `+` lines.
This will help you generate correct code and correct diffs.

To move code, delete the entire existing version with `-` lines and then add a new, updated version with `+` lines.

Minimize the number of `-` and `+` blocks. Try to create patches with only one `-` block and one `+` block.

Avoid inserting or removing lines.
If empty lines are inserted they must be marked with `+`.
If empty lines are removed they must be marked with `-`.

If you insert lines with `}` or `{` do not forget to mark them with `+`.

Make minimal changes.

An example that follows these instructions is the following:
@@ ... @@
-def factorial(n):
-    if n == 0:
-        return 1
-    else:
-        return n * factorial(n-1)
+def factorial(number):
+    if number == 0:
+        return 1
+    else:
+        return number * factorial(number-1)

An example that does not follow these instructions is the following:
@@ ... @@
-def factorial(n):
+def factorial(number):
-    if n == 0:
+    if number == 0:
         return 1
     else:
-        return n * factorial(n-1)
+        return number * factorial(number-1)

</patch-format>
"""

CONTEXT_SUPERYOLO_FILE = """The following Git commit introduce a memory vulnerability:
<git-commit>
{diff}
</git-commit>
The source code of the file {file} modified by this Git commit is the following:
<code>
{code_context}
</code>
<instructions>
Please fix the buggy file and return a modified version of the code with the following properties:
- The repair is minimal
- Do not add comments
- Keep the same functionality of the code
- Do not modify the code unless it is to fix the bug
- Keep the same indentation as the original file
- Return the entire modified file without abbreviations

The output must only contain code in the following format:
<code>
<insert modified file here>
</code>

You must use the <code> </code> tags in your output.
Between these tags, only generate code.
Do not output anything else outside these tags.
</instructions>
"""


CONTEXT_SUPERYOLO_DIFF = """The following Git commit introduce a memory vulnerability:
<git-commit>
{diff}
</git-commit>
The source code of the file {file} modified by this Git commit is the following:
<code>
{code_context}
</code>
<instructions>
Please fix the bug and return a patch in unified diffs using the following format:
{format}
The output must only contain code in the following format:
<code>
<insert unified diff here>
</code>
When making a patch make sure you follow the following instructions:
- The repair is minimal
- Do not add comments
- Keep the same functionality of the code
- Do not modify the code unless it is to fix the bug
- Keep the same indentation as the original file
</instructions>
"""


@dataclass
class SuperYoloLLMStrategy(PatchGenerationStrategy):
    diagnosis: Diagnosis
    model: str
    llm: LLM
    diff: Diff
    files: dict[str, str]
    number_patches: int
    whole_file: bool

    @classmethod
    def build(
        cls,
        diagnosis: Diagnosis,
    ) -> SuperYoloLLMStrategy:
        llm = LLM.from_settings(diagnosis.project.settings)
        diff = commit_to_diff.commit_to_diff(diagnosis.project.triggering_commit)
        files = commit_to_diff.commit_to_files(diagnosis.project.head, diff)

        return cls(
            diagnosis=diagnosis,
            model=llm.model,
            llm=llm,
            diff=diff,
            files=files,
            number_patches=Util.number_patches,
            whole_file=True,
        )

    def _set_model(self, model: str) -> None:
        self.model = model
        self.llm.model = model

    def _create_system_prompt_file(self) -> str:
        return """
        You are an expert security analyst.
        You can find security vulnerabilities and suggest patches to fix them.
        You always do minimal changes to the code.
        You always provide a patch to the code by returning the entire modified file.
        """

    def _create_system_prompt_diffs(self) -> str:
        return """
        You are an expert security analyst.
        You can find security vulnerabilities and suggest patches to fix them.
        You always do minimal changes to the code.
        You always provide a patch to the code in valid unified diffs format.
        """

    def _create_user_prompt_diffs(self, contents: str, filename: str) -> str:
        code_context = contents

        return CONTEXT_SUPERYOLO_DIFF.format(
            diff=self.diff,
            code_context=code_context,
            file=filename,
            format=PATCH_FORMAT,
        )

    def _create_user_prompt_file(self, contents: str, filename: str) -> str:
        code_context = contents

        return CONTEXT_SUPERYOLO_FILE.format(
            diff=self.diff,
            code_context=code_context,
            file=filename,
        )

    def _get_llm_output_diffs(self, file: str) -> list[Diff]:

        diffs: list[Diff] = []
        system_prompt = self._create_system_prompt_diffs()
        user_prompt = self._create_user_prompt_diffs(self.files[file], file)

        logger.info(f"user prompt tokens: {Util.count_tokens(user_prompt, self.model)}")
        logger.info(f"system prompt tokens: {Util.count_tokens(system_prompt, self.model)}")

        messages: MessagesIterable = []
        system_message = ChatCompletionSystemMessageParam(role="system", content=system_prompt)
        user_message = ChatCompletionUserMessageParam(role="user", content=user_prompt)
        messages.append(system_message)
        messages.append(user_message)

        attempt = 0
        while attempt < self.number_patches:

            llm_output = self.llm._simple_call_llm(messages)
            if not llm_output:
                logger.debug("Failed to get output from LLM")
                attempt += 1
                continue

            original_contents = self.files[file]
            patch_contents = Util.apply_patch(original_contents, llm_output)

            if not patch_contents:
                logger.debug(f"Failed to generate patch "
                                f"{attempt + 1} / {self.number_patches} "
                                f"with model {self.model}")
            else:
                logger.debug(f"Successfully generated a patch "
                                f"{attempt + 1} / {self.number_patches} "
                                f"with model {self.model}")
                # Generate the diff
                diff = difflib.unified_diff(
                    original_contents.splitlines(keepends=True),
                    patch_contents.splitlines(keepends=True),
                    fromfile=file,
                    tofile=file,
                )

                # Convert the diff to a string and add to the diffs list
                diff_patch = "".join(diff)
                diffs.append(Diff.from_unidiff(diff_patch))

            last_llm_output = ChatCompletionAssistantMessageParam(role="assistant",
                                                                    content=llm_output)
            messages.append(last_llm_output)
            user_new_patch = ChatCompletionUserMessageParam(role="user",
                                                            content="Can you get me a different patch?")
            messages.append(user_new_patch)
            attempt += 1

        logger.info(f"Found {len(diffs)} patches")
        return diffs

    # TODO: a lot of code duplication; refactor later
    def _get_llm_output_file(self, file: str) -> list[Diff]:

        diffs: list[Diff] = []
        system_prompt = self._create_system_prompt_file()
        user_prompt = self._create_user_prompt_file(self.files[file], file)

        logger.info(f"user prompt tokens: {Util.count_tokens(user_prompt, self.model)}")
        logger.info(f"system prompt tokens: {Util.count_tokens(system_prompt, self.model)}")

        messages: MessagesIterable = []
        system_message = ChatCompletionSystemMessageParam(role="system", content=system_prompt)
        user_message = ChatCompletionUserMessageParam(role="user", content=user_prompt)
        messages.append(system_message)
        messages.append(user_message)

        attempt = 0
        while attempt < self.number_patches:

            llm_output = self.llm._simple_call_llm(messages)
            if not llm_output:
                logger.debug("Failed to get output from LLM")
                attempt += 1
                continue

            logger.debug(f"LLM output=\n{llm_output}")
            original_contents = self.files[file]
            patch_lines = llm_output.split("\n")
            if len(patch_lines) < 2:  # noqa: PLR2004
                logger.debug(f"Failed to generate patch "
                                f"{attempt + 1} / {self.number_patches} "
                                f"with model {self.model}")
            else:
                patch_lines = patch_lines[1:len(patch_lines) - 1]
                patch_contents = "\n".join(patch_lines)
                logger.debug(f"Successfully generated a patch "
                                f"{attempt + 1} / {self.number_patches} "
                                f"with model {self.model}")
                # Generate the diff
                diff = difflib.unified_diff(
                    original_contents.splitlines(keepends=True),
                    patch_contents.splitlines(keepends=True),
                    fromfile=file,
                    tofile=file,
                )

                # Convert the diff to a string and add to the diffs list
                diff_patch = "".join(diff)
                diffs.append(Diff.from_unidiff(diff_patch))

            last_llm_output = ChatCompletionAssistantMessageParam(role="assistant",
                                                                    content=llm_output)
            messages.append(last_llm_output)
            user_new_patch = ChatCompletionUserMessageParam(role="user",
                                                            content="Can you get me a different patch?")
            messages.append(user_new_patch)
            attempt += 1

        logger.info(f"Found {len(diffs)} patches")
        return diffs

    def _get_llm_output(self) -> list[Diff]:

        diffs = []
        for file in self.files:
            tokens_file = Util.count_tokens(self.files[file], self.model)
            if tokens_file * 1.25 > Util.limit_llm_output:
                logger.warning(f"File {file} is too large for SuperYolo whole file approach")
                if self.whole_file:
                    continue

            if self.whole_file:
                logger.info(f"SuperYolo using whole file approach for {file}")
                diffs.extend(self._get_llm_output_file(file))
            else:
                logger.info(f"SuperYolo using diff approach for {file}")
                diffs.extend(self._get_llm_output_diffs(file))

        return diffs

    def run(self) -> list[Diff]:

        return self._get_llm_output()
