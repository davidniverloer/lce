from __future__ import annotations

import os
from pathlib import Path


def prepare_crewai_runtime() -> None:
    repo_root = Path(__file__).resolve().parents[4]
    runtime_home = os.environ.get(
        "CREWAI_RUNTIME_HOME",
        str(repo_root / ".crewai-home"),
    )

    runtime_home_path = Path(runtime_home)
    runtime_home_path.mkdir(parents=True, exist_ok=True)
    os.environ["HOME"] = str(runtime_home_path)
