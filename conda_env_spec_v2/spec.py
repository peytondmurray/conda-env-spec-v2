from __future__ import annotations

import pathlib
import sys
from typing import Any

from conda.common.compat import on_linux, on_mac, on_win
from conda.env.env import Environment
from conda.plugins.types import EnvironmentSpecBase
from pydantic import BaseModel, Field

if sys.version_info < (3, 11):
    from tomli import load
else:
    from tomllib import load


class ConditionalRequirement(BaseModel):
    """A requirement that only comes into effect if the specified package is present.

    Attributes
    ----------
    has : Name of a package; if present, the packages under ``self.then`` are also
        included in the requirements
    then : Packages to conditionally include
    """

    has: str = Field(alias="if")
    then: str | list[str]


Requirement = str | ConditionalRequirement


class Group(BaseModel):
    """A group of requirements.

    Attributes
    ----------
    name : Name of the requirement group
    requirements : A set of conda requirements that are part of the group
    pypi_requirements : A set of pip requirements that are part of the group
    """

    name: str
    requirements: list[Requirement] = []
    pypi_requirements: list[Requirement] = []


class EnvironmentFile(BaseModel):
    """An model representing the contents of an environment file."""

    name: str = ""
    description: str = ""
    config: dict[str, Any] = {}
    platforms: list[str] = []
    requirements: list[Requirement] = []
    pypi_requirements: list[Requirement] = []
    groups: list[Group] = []
    metadata: dict[str, Any] = {}

    def dump_dependencies(
        self, groups: str | list[str] | None = None
    ) -> list[str, dict[str, list[str]]]:
        """Dump the dependencies of the environment.

        For legacy reasons ``conda.env.env.Dependencies`` has some
        "public" attributes that are accessed in various places of the conda
        code base. This function dumps the dependencies as a dict which is used
        to construct a ``conda.env.env.Dependencies``.

        Parameters
        ----------
        groups : str | list[str] | None
            Dependency group(s) to include. For now, all groups are included

        Returns
        -------
        list[str, dict[str, list[str]]]
            List of conda dependencies; if pypi dependencies are present,
            include those in a separate mapping.
        """
        conda_deps, pypi_deps = self._get_group_dependencies(groups)
        conda_deps.extend(self.requirements)
        pypi_deps.extend(self.pypi_requirements)

        conda_deps = self._preprocess_conditional_requirements(conda_deps)
        pypi_deps = self._preprocess_conditional_requirements(pypi_deps)

        if pypi_deps:
            conda_deps.append("pip")
            return conda_deps + [{"pip": pypi_deps}]

        return conda_deps

    @staticmethod
    def _preprocess_conditional_requirements(
        requirements: list[Requirement],
    ) -> list[str]:
        """Replace conditional requirements with resolved requirements if applicable.

        Currently only the following virtual packages are allowed in the `if` condition:

            __osx: OSX version if applicable.
            __linux: Available when running on Linux.
            __unix: Available when running on OSX or Linux.
            __win: Available when running on Win.

        Parameters
        ----------
        requirements : list[Requirement]
            List of requirements to be searched for ConditionalRequirement objects,
            which should be replaced with resolved requirements

        Returns
        -------
        list[str]
            The requirements that were passed in with conditional requirements replaced
            or removed, as appropriate depending on the system running this function
        """
        resolved = []
        for req in requirements:
            if isinstance(req, str):
                resolved.append(req)
            else:
                if (
                    (req.has == "__win" and on_win)
                    or (req.has == "__osx" and on_mac)
                    or (req.has == "__unix" and (on_mac or on_linux))
                    or (req.has == "__linux" and on_linux)
                ):
                    if isinstance(req.then, str):
                        resolved.append(req.then)
                    else:
                        resolved.extend(req.then)
        return resolved

    def _get_group_dependencies(
        self,
        groups: str | list[str] | None = None,
    ) -> tuple[list[Requirement], list[Requirement]]:
        """Get the dependencies of the specified groups.

        Parameters
        ----------
        groups : str | list[str] | None
            Name or names of the groups for which dependencies should be returned. If
            None, don't return any groups

        Returns
        -------
        tuple[list[Requirement], list[Requirement]]
            Two lists of dependencies from the requested groups: one for conda requirements,
            the other for pypi requirements
        """
        group_map = {group.name: group for group in self.groups}

        # If the user doesn't specify a group, don't include
        if groups is None:
            groups = []
        elif isinstance(groups, str):
            groups = [groups]

        conda_deps, pypi_deps = [], []
        for group in groups:
            if group not in group_map:
                raise ValueError(
                    f"Group '{group}' is not specified in the {self.name} environment."
                )

            conda_deps.extend(group_map[group].requirements)
            pypi_deps.extend(group_map[group].pypi_requirements)

        return conda_deps, pypi_deps


class EnvSpecV2(EnvironmentSpecBase):
    """An implementation of a conda environment specification."""

    extensions = {".toml"}

    def __init__(self, filename: str):
        self.filename = filename
        self._model = None

    @property
    def model(self) -> EnvironmentFile:
        """Get the model that holds the parsed environment file.

        If not parsed, the environment file will be loaded and parsed.

        Returns
        -------
        EnvironmentFile
            Model containing the parsed environment
        """
        if not self._model:
            with open(self.filename, "rb") as file:
                self._model = EnvironmentFile.model_validate(load(file))
        return self._model

    def can_handle(self) -> bool:
        """Check whether the spec can parse ``self.filename``.

        Returns
        -------
        bool
            True if the spec can parse the file, False otherwise
        """
        # Return early if no filename was provided
        if self.filename is None:
            return False

        file = pathlib.Path(self.filename)
        return file.suffix in self.extensions and file.exists()

    def environment(self) -> Environment:
        """Parse the contents of `self.filename` to a valid conda environment.

        Returns
        -------
        Environment
            An environment as specified in `self.filename` according to the
            V2 environment spec. See ``EnvironmentSpec`` for a Pydantic model
            which implements the spec.
        """
        return Environment(
            name=self.model.name,
            filename=self.filename,
            channels=self.model.config.get("channels"),
            dependencies=self.model.dump_dependencies(),
            prefix=None,
            variables=self.model.config.get("variables"),
        )
