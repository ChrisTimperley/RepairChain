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


CONTEXT_SUPERYOLO = """The following Git commit introduce a memory vulnerability:
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
        )

    def _create_system_prompt(self) -> str:
        return """
        You are an expert security analyst.
        You can find security vulnerabilities and suggest patches to fix them.
        You always do minimal changes to the code.
        You always provide a patch to the code in valid unified diffs format.
        """

    def _create_user_prompt(self, contents: str) -> str:
        code_context = contents

        return CONTEXT_SUPERYOLO.format(
            diff=self.diff,
            code_context=code_context,
            file=list(self.files.keys()),
            format=PATCH_FORMAT,
        )

    def _get_llm_output(self) -> list[Diff]:

        diffs = []
        for file in self.files:
            system_prompt = self._create_system_prompt()
            user_prompt = self._create_user_prompt(self.files[file])

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
                original_contents = self.files[file]
                patch_contents = Util.apply_patch(original_contents, llm_output)
                logger.debug(f"patch=\n{patch_contents}")

                if not patch_contents:
                    logger.debug(f"Failed to generate patch "
                                 f"{attempt + 1} / {self.number_patches} "
                                 f"with model {self.model}")
                    logger.debug(f"Failed output:\n {llm_output}\n")
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

    def run(self) -> list[Diff]:

        return self._get_llm_output()
