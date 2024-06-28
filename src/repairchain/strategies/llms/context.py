from __future__ import annotations

__all__ = ("create_context_all_files_git_diff",)

import typing as t

if t.TYPE_CHECKING:
    from repairchain.models.diff import Diff

CONTEXT_TEMPLATE = """The following Git commit introduce a memory vulnerability:
BEGIN GIT COMMIT
{diff}
END GIT COMMIT
The source code of the files modified by this Git commit is the following:
BEGIN CODE
{code_context}
END CODE
BEGIN INSTRUCTIONS
Only one of the files is buggy.
Please fix the buggy file and return a modified version of the code with the following properties:
- The repair is minimal
- Do not add comments
- Keep the same functionality of the code
- Do not modify the code unless it is to fix the bug
- Only modify the buggy file
- The modified code should only contain the buggy function
- Keep the same indentation as the original file
- Return 10 potential bug fixes. These can cover different functions
Use as format the following for each bug fix:
BEGIN BUG FIX
<number>
BEGIN MODIFIED FILENAME
<filemame>
END MODIFIED FILENAME
BEGIN MODIFIED FUNCTION NAME
<function>
END MODIFIED FUNCTION NAME
BEGIN MODIFIED CODE
<code>
END MODIFIED CODE
BEGIN DESCRIPTION
<description>
END DESCRIPTION
END BUG FIX
END INSTRUCTIONS
"""


def create_context_all_files_git_diff(files: dict[str, str], diff: Diff) -> str:
    code_context = "\n".join(
        f"BEGIN FILE: {filename}\n{contents}\nEND FILE"
        for filename, contents in files.items()
    )
    return CONTEXT_TEMPLATE.format(
        code_context=code_context,
        diff=diff,
    )
