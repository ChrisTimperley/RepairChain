from __future__ import annotations

__all__ = ("create_context",)

import typing as t

if t.TYPE_CHECKING:
    from repairchain.models.diff import Diff

CONTEXT_TEMPLATE = """The following code has a memory vulnerability in one of the files:
BEGIN CODE
{code_context}
END CODE
This code was modified with the following git commit:
{diff}
I want a patch for this program with the following properties:
- The repair is minimal
- Do not add comments
- Keep the same functionality of the code
- Do not simplify the code
Use as format the following:
BEGIN GIT DIFF PATCH
<patch>
END GIT DIFF PATCH
BEGIN DESCRIPTION
<description>
END DESCRIPTION
"""


def create_context(files: dict[str, str], diff: Diff) -> str:
    code_context = "\n".join(
        f"BEGIN FILE: {filename}\n{contents}\nEND FILE"
        for filename, contents in files.items()
    )
    return CONTEXT_TEMPLATE.format(
        code_context=code_context,
        diff=diff,
    )
