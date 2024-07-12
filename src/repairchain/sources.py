from __future__ import annotations

__all__ = (
    "ProjectSources",
    "SourceFileVersion",
)

import difflib
import typing as t
from dataclasses import dataclass, field
from pathlib import Path

from sourcelocation import Location, LocationRange

from repairchain.models.diff import Diff
from repairchain.models.replacement import Replacement

if t.TYPE_CHECKING:
    import git

    from repairchain.models.project import Project


@dataclass(frozen=True)
class SourceFileVersion:
    version: git.Commit
    filename: Path
    contents: str
    num_lines: int
    _line_to_start_and_end_offset: t.Sequence[tuple[int, int]] = field(repr=False)

    @classmethod
    def build(
        cls,
        version: git.Commit,
        filename: Path,
    ) -> SourceFileVersion:
        """Builds a source file from a given commit and filename."""
        blob = version.tree / str(filename)
        raw_contents = blob.data_stream.read()
        contents = raw_contents.decode("utf-8")
        return cls.build_from_contents(
            version=version,
            filename=filename,
            contents=contents,
        )

    @classmethod
    def build_from_contents(
        cls,
        version: git.Commit,
        filename: Path,
        contents: str,
    ) -> SourceFileVersion:
        """Builds a source file from a given commit, filename, and contents."""
        line_start_and_end_offsets = cls._compute_line_start_and_end_offsets(contents)
        num_lines = len(line_start_and_end_offsets)
        return cls(
            version=version,
            filename=filename,
            contents=contents,
            num_lines=num_lines,
            _line_to_start_and_end_offset=line_start_and_end_offsets,
        )

    @classmethod
    def _compute_line_start_and_end_offsets(
        cls,
        contents: str,
    ) -> t.Sequence[tuple[int, int]]:
        """Computes the offsets for each line within a given file.

        Parameters
        ----------
        contents: str
            The contents of the given file.
        """
        line_to_start_end: list[tuple[int, int]] = []
        offset_file_end = len(contents)
        offset_line_start = 0
        while True:
            offset_line_break = contents.find("\n", offset_line_start)
            if offset_line_break == -1:
                start_end = (offset_line_start, offset_file_end)
                line_to_start_end.append(start_end)
                break
            start_end = (offset_line_start, offset_line_break)  # is this end-inclusive?
            line_to_start_end.append(start_end)
            offset_line_start = offset_line_break + 1
        return tuple(line_to_start_end)

    def location_to_offset(self, location: Location) -> int:
        """Transforms a location to an offset in this file."""
        return self.line_col_to_offset(location.line, location.column)

    def line_col_to_offset(self, line: int, col: int) -> int:
        """Transforms a line and column in this file to an offset."""
        offset_line_start = self._line_to_start_and_end_offset[line - 1][0]
        return offset_line_start + col

    def read_chars(self, at: LocationRange) -> str:
        loc_start = at.start
        loc_stop = at.stop
        offset_start = self.line_col_to_offset(loc_start.line, loc_start.column)
        offset_stop = self.line_col_to_offset(loc_stop.line, loc_stop.column)
        return self.contents[offset_start:offset_stop]

    def line_to_location_range(self, num: int) -> LocationRange:
        offset_start, offset_stop = self._line_to_start_and_end_offset[num - 1]
        length = offset_stop - offset_start
        start = Location(num, 0)
        stop = Location(num, length)
        return LocationRange(start, stop)

    def read_line(self, num: int, *, keep_newline: bool = False) -> str:
        range_ = self.line_to_location_range(num)
        contents = self.read_chars(range_)
        return contents + "\n" if keep_newline else contents

    def with_replacements(self, replacements: t.Sequence[Replacement]) -> str:
        """Returns the result of applying replacements to this file."""
        # exclude conflicting replacements
        replacements = Replacement.resolve(replacements)
        contents = self.contents
        for replacement in replacements:
            loc = replacement.location
            offset_start = self.location_to_offset(loc.start)
            offset_stop = self.location_to_offset(loc.stop)
            contents = \
                contents[:offset_start] + replacement.text + contents[offset_stop:]
        return contents


@dataclass
class ProjectSources:
    project: Project
    _version_to_files: dict[
        git.Commit, dict[Path, SourceFileVersion],
    ] = field(default_factory=dict)

    @classmethod
    def for_project(cls, project: Project) -> ProjectSources:
        return cls(project)

    def source(
        self,
        filename: Path | str,
        version: git.Commit | None = None,
    ) -> SourceFileVersion:
        """Retrieves a given file and its contents from the repository.

        Arguments:
        ---------
        filename: Path | str
            The path to the file to retrieve, relative to the root of
            the repository.
        version: git.Commit | None
            The version of the file to retrieve.
            If None, the HEAD is used.

        Returns:
        -------
        str
            The contents of the file.

        Raises:
        ------
        ValueError
            If the given filename is not a relative path.
        FileNotFoundError
            If the file does not exist in the repository (version).
        """
        if version is None:
            version = self.project.head

        if isinstance(filename, str):
            filename = Path(filename)

        if not filename.is_absolute():
            message = f"filename must be a relative path: {filename}"
            raise ValueError(message)

        # retrieve the file cache for this commit
        if version not in self._version_to_files:
            self._version_to_files[version] = {}

        file_cache = self._version_to_files[version]

        # is the file already cached?
        if filename in file_cache:
            return file_cache[filename]

        # if not, build the file and store it in the cache
        file_version = SourceFileVersion.build(version, filename)
        file_cache[filename] = file_version

        return file_version

    def replacements_to_diff(
        self,
        replacements: list[Replacement],
        version: git.Commit | None = None,
    ) -> Diff:
        if version is None:
            version = self.project.head

        # group replacements by file
        file_to_replacements: dict[Path, list[Replacement]] = {}
        for replacement in replacements:
            filename = Path(replacement.filename)
            if filename not in file_to_replacements:
                file_to_replacements[filename] = []
            file_to_replacements[filename].append(replacement)

        file_unidiffs: list[str] = []
        for filename, file_replacements in file_to_replacements.items():
            file_version = self.source(filename, version)
            original = file_version.contents
            mutated = file_version.with_replacements(file_replacements)
            diff_lines = difflib.unified_diff(
                original.splitlines(keepends=True),
                mutated.splitlines(keepends=True),
                fromfile=str(filename),
                tofile=str(filename),
            )
            unidiff = "".join(diff_lines)
            file_unidiffs.append(unidiff)

        unidiff = "\n".join(file_unidiffs)
        return Diff.from_unidiff(unidiff)
