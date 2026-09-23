from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

SEED = Path(__file__).resolve().parents[1] / "examples" / "seed-nest.sh"


@pytest.fixture(scope="session")
def nest(tmp_path_factory) -> Path:
    if shutil.which("ctx") is None:
        pytest.skip("ctx not installed (npm install -g @promptowl/contextnest-cli)")
    d = tmp_path_factory.mktemp("nest")
    subprocess.run(["sh", str(SEED), str(d)], check=True, capture_output=True)
    return d
