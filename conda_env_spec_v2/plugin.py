from collections.abc import Generator

from conda import plugins

from .spec import EnvSpecV2


@plugins.hookimpl
def conda_environment_specifiers() -> Generator:
    """Initialize the environment specification."""
    yield plugins.CondaEnvSpec(
        name="EnvSpecV2",
        environment_spec=EnvSpecV2,
    )
