from __future__ import annotations

import pathlib
import sys
from collections.abc import Generator
from typing import Any

import yaml
from conda.env.env import Environment
from conda.plugins.types import EnvironmentSpecBase
from pydantic import BaseModel, Field

if sys.version_info >= (3, 11):
    from tomllib import load
else:
    from tomli import load


class ConditionalRequirement(BaseModel):
    """A requirement that only comes into effect if the specified package is present.

    Attributes
    ----------
    _if : Name of a package; if present, the packages under ``self.then`` are also
        included in the requirements
    then : Packages to conditionally include
    """

    _if: str = Field(alias="if")
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
    requirements: list[Requirement]
    pypi_requirements: list[Requirement]


class EnvironmentSpec(BaseModel):
    """An model representing the contents of an environment file."""

    name: str = ""
    description: str = ""
    config: dict[str, Any] = {}
    platforms: list[str] = []
    requirements: list[Requirement] = []
    pypi_requirements: list[Requirement] = []
    groups: list[Group] = []
    metadata: dict[str, Any] = {}

    def dump_dependencies(self, groups: str | list[str] | None = None) -> str:
        """Dump the dependencies of the environment.

        For legacy reasons ``conda.env.env.Dependencies`` has some
        "public" attributes that are accessed in various places of the conda
        code base. This function dumps the dependencies as a yaml-formatted
        string which is used by conda to construct a
        ``conda.env.env.Dependencies``.

        Parameters
        ----------
        groups : str | list[str] | None
            Dependency group(s) to include. For now, all groups are included

        Returns
        -------
        str
            A yaml-formatted string of dependencies that can be parsed by
            ``conda.env.env.Dependencies``
        """
        conda_deps, pypi_deps = self.get_group_dependencies(groups)
        conda_deps.extend(self.requirements)
        pypi_deps.extend(self.pypi_requirements)

        mutating = True
        while mutating:
            mutating = False
            for dep_list in (conda_deps, pypi_deps):
                for dep in self._get_pending_requirements(dep_list[:]):
                    if dep.name in conda_deps + pypi_deps:
                        dep_list.append(dep.name)
                        mutating = True

        if any(self._get_pending_requirements(conda_deps + pypi_deps)):
            raise ValueError(
                "Unable to resolve conditional dependencies: "
                + str(self._get_pending_requirements(conda_deps + pypi_deps))
            )

        return yaml.dumps(conda_deps + [{"pip": pypi_deps}])

    @staticmethod
    def _get_pending_requirements(
        requirements: list[Requirement],
    ) -> Generator[Requirement, None, None]:
        """Get a list of ConditionalRequirement objects from the input.

        Parameters
        ----------
        requirements : list[Requirement]
            A list of Requirement objects to inspect

        Returns
        -------
        Generator[Requirement, None, None]
            The ConditionalRequirement objects from the input
        """
        for req in requirements:
            if isinstance(req, ConditionalRequirement):
                yield req

    def get_group_dependencies(
        self,
        groups: str | list[str] | None = None,
    ) -> list[Requirement]:
        """Get the dependencies of the specified groups.

        Parameters
        ----------
        groups : str | list[str] | None
            Name or names of the groups for which dependencies should be returned

        Returns
        -------
        list[Requirement]
            A list of dependencies for the specified group name
        """
        group_map = {group.name: group for group in self.groups}

        # If the user doesn't specify a group, just use the requirements from
        # every single group
        if groups is None:
            groups = list(group_map)

        conda_deps, pypi_deps = [], []
        for group in groups:
            if group not in group_map:
                raise ValueError(
                    f"Group '{group}' is not specified in the {self.name} environment."
                )

            conda_deps.append(group_map[group].get_conda_reqs())
            pypi_deps.append(group_map[group].get_pypi_reqs())

        return conda_deps, pypi_deps


class EnvSpecV2(EnvironmentSpecBase):
    """An implementation of a conda environment specification."""

    extensions = {".toml"}

    def __init__(self, filename: str):
        self.filename = filename

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
        with open(self.filename, "rb") as file:
            spec = EnvironmentSpec.model_validate(load(file))

        return Environment(
            name=spec.name,
            filename=self.filename,
            channels=spec.config.get("channels"),
            dependencies=spec.dump_dependencies(),
            prefix=None,
            variables=spec.config.get("variables"),
        )
