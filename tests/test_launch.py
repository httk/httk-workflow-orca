"""ORCA's launch prefix is opt-in, and confined multi-node ORCA is refused."""

import sys
from pathlib import Path

import pytest

from httk.codes.orca import run_orca

PROGRAM = [sys.executable, "-c", "pass"]


def _argv(tmp_path: Path, *arguments: str, **keywords: object) -> tuple[str, ...]:
    return run_orca(list(arguments) or PROGRAM, directory=tmp_path, **keywords).process.argv  # type: ignore[arg-type]


def test_no_prefix_by_default_even_when_one_is_set(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HTTK_WORKFLOW_LAUNCH", "env A=b")
    assert _argv(tmp_path)[0] == sys.executable
    assert _argv(tmp_path, launch=False)[0] == sys.executable


def test_launch_true_prepends_the_prefix(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HTTK_WORKFLOW_LAUNCH", "env 'A=b c'")
    assert _argv(tmp_path, launch=True)[:3] == ("env", "A=b c", sys.executable)


def test_a_launcher_is_refused_with_launch_true(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HTTK_WORKFLOW_LAUNCH", "env A=b")
    with pytest.raises(ValueError, match="manager.launch_template"):
        run_orca(["srun", "orca"], directory=tmp_path, launch=True)


def test_confined_multi_node_is_refused(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HTTK_WORKFLOW_CONFINED", "1")
    monkeypatch.setenv("HTTK_WORKFLOW_NODELIST", "n1,n2")
    with pytest.raises(ValueError, match="distributed ORCA is not supported"):
        run_orca(PROGRAM, directory=tmp_path)


def test_confined_single_node_and_unconfined_multi_node_run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HTTK_WORKFLOW_CONFINED", "1")
    monkeypatch.setenv("HTTK_WORKFLOW_NODELIST", "n1")
    assert _argv(tmp_path)[0] == sys.executable
    monkeypatch.delenv("HTTK_WORKFLOW_CONFINED")
    monkeypatch.setenv("HTTK_WORKFLOW_NODELIST", "n1,n2")
    assert _argv(tmp_path)[0] == sys.executable
