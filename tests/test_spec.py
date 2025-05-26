import pathlib
import sys
from unittest import mock

import pytest

from conda_env_spec_v2.spec import EnvironmentFile, EnvSpecV2

if sys.version_info < (3, 11):
    from tomli import loads
else:
    from tomllib import loads


def test_model(simple_env):
    """Test that the EnvironmentSpec model parses a valid environment spec."""
    EnvironmentFile.model_validate(loads(simple_env))


def test_spec_v2():
    """Test that an environment file parses into a valid conda.env.env.Environment."""
    spec = EnvSpecV2(pathlib.Path(__file__).parent / "data" / "simple.toml")
    environment = spec.environment()

    assert spec.can_handle()
    assert environment.name == "test-env-v2"
    assert environment.filename.name == "simple.toml"
    assert environment.channels == ["conda-forge"]

    assert set(environment.dependencies["conda"]) == {
        "python",
        "numpy",
        "pip",
    }
    assert set(environment.dependencies["pip"]) == {
        "my-lab-dependency",
    }

    assert environment.dependencies
    assert environment.prefix is None
    assert environment.variables == {"ENVVAR": "value", "ENVVAR2": "value2"}


@pytest.mark.parametrize(
    "platform",
    [
        "linux",
        "win",
        "mac",
    ],
)
def test_model_group_py38(platform):
    """Get the dependencies from the model including group 'py38'."""
    spec = EnvSpecV2(pathlib.Path(__file__).parent / "data" / "simple.toml")

    with (
        mock.patch("conda_env_spec_v2.spec.on_linux", platform == "linux"),
        mock.patch("conda_env_spec_v2.spec.on_win", platform == "win"),
        mock.patch("conda_env_spec_v2.spec.on_mac", platform == "mac"),
    ):
        deps = spec.model.dump_dependencies("py38")

    expected_conda = ["python", "numpy", "python=3.8", "pip"]
    expected_pypi = ["my-lab-dependency"]

    if platform == "win":
        expected_conda.append("pywin32")
    if platform == "mac":
        expected_pypi.append("my-lab-dependency-osx")

    conda_deps, pypi_deps = [], []
    for dep in deps:
        if isinstance(dep, str):
            conda_deps.append(dep)
        if isinstance(dep, dict):
            pypi_deps = dep["pip"]

    assert set(conda_deps) == set(expected_conda)
    assert set(pypi_deps) == set(expected_pypi)


@pytest.mark.parametrize(
    "platform",
    [
        "linux",
        "win",
        "mac",
    ],
)
def test_model_group_test(platform):
    """Get the dependencies from the model including group 'test'."""
    spec = EnvSpecV2(pathlib.Path(__file__).parent / "data" / "simple.toml")

    with (
        mock.patch("conda_env_spec_v2.spec.on_linux", platform == "linux"),
        mock.patch("conda_env_spec_v2.spec.on_win", platform == "win"),
        mock.patch("conda_env_spec_v2.spec.on_mac", platform == "mac"),
    ):
        deps = spec.model.dump_dependencies("test")

    expected_conda = ["python", "numpy", "pip", "pytest", "pytest-cov"]
    expected_pypi = ["my-lab-dependency", "some-test-dependency-only-on-pypi"]

    if platform == "mac":
        expected_pypi.append("my-lab-dependency-osx")
    if platform == "win":
        expected_conda.extend(["pywin32", "pytest-windows"])

    conda_deps, pypi_deps = [], []
    for dep in deps:
        if isinstance(dep, str):
            conda_deps.append(dep)
        if isinstance(dep, dict):
            pypi_deps = dep["pip"]

    assert set(conda_deps) == set(expected_conda)
    assert set(pypi_deps) == set(expected_pypi)


@pytest.mark.parametrize(
    "platform",
    [
        "linux",
        "win",
        "mac",
    ],
)
def test_model_group_test_py38(platform):
    """Get the dependencies from the model including groups ['test', 'py38']."""
    spec = EnvSpecV2(pathlib.Path(__file__).parent / "data" / "simple.toml")

    with (
        mock.patch("conda_env_spec_v2.spec.on_linux", platform == "linux"),
        mock.patch("conda_env_spec_v2.spec.on_win", platform == "win"),
        mock.patch("conda_env_spec_v2.spec.on_mac", platform == "mac"),
    ):
        deps = spec.model.dump_dependencies(["test", "py38"])

    expected_conda = ["python", "numpy", "pip", "pytest", "pytest-cov", "python=3.8"]
    expected_pypi = ["my-lab-dependency", "some-test-dependency-only-on-pypi"]

    if platform == "mac":
        expected_pypi.append("my-lab-dependency-osx")
    if platform == "win":
        expected_conda.extend(["pywin32", "pytest-windows"])

    conda_deps, pypi_deps = [], []
    for dep in deps:
        if isinstance(dep, str):
            conda_deps.append(dep)
        if isinstance(dep, dict):
            pypi_deps = dep["pip"]

    assert set(conda_deps) == set(expected_conda)
    assert set(pypi_deps) == set(expected_pypi)
