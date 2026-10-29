import json
from pathlib import Path

import pytest


@pytest.fixture
def design():
    return json.loads((Path(__file__).parents[1] / "examples/three-tier.json").read_text())
