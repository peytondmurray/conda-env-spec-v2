import pathlib
import tomllib

from conda_env_spec_v2 import EnvironmentFile, EnvSpecV2


def test_model(simple_env):
    """Test that the EnvironmentSpec model parses a valid environment spec."""
    EnvironmentFile.model_validate(tomllib.loads(simple_env))


def test_spec_v2():
    """Test that an environment file parses into a valid conda.env.env.Environment."""
    spec = EnvSpecV2(pathlib.Path(__file__).parent / "data" / "simple.toml")
    environment = spec.environment()

    assert spec.can_handle()
    assert environment.name == "test-env-v2"
    assert environment.filename == "simple.toml"
    assert environment.channels == ["conda-forge"]
    assert environment.dependencies is None
    assert environment.prefix is None
    assert environment.variables == {"ENVVAR": "value", "ENVVAR2": "value2"}

    deps = environment.dependencies
    conda_deps, pypi_deps = deps["conda"], deps["pip"]

    assert set(conda_deps) == {
        "python",
        "numpy",
        "pytest",
        "pytest-cov",
    }
    assert set(pypi_deps) == {"my-lab-dependency", "some-test-dependency-only-on-pypi"}
