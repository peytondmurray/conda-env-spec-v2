import pathlib
import sys

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
        "python=3.8",
        "pytest",
        "pytest-cov",
        "python",
        "numpy",
        "pip",
    }
    assert set(environment.dependencies["pip"]) == {
        "my-lab-dependency",
        "some-test-dependency-only-on-pypi",
    }

    assert environment.dependencies
    assert environment.prefix is None
    assert environment.variables == {"ENVVAR": "value", "ENVVAR2": "value2"}
