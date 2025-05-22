import pathlib

import pytest


@pytest.fixture
def simple_env() -> str:
    """Read the simple v2 environment file and return the contents as a string.

    Returns
    -------
    str
        Contents of `simple.toml`
    """
    with open(pathlib.Path(__file__).parent / "data" / "simple.toml") as f:
        return f.reads()
