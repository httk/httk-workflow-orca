"""Shared test configuration: isolate the httk configuration of every test."""

import json
import os
import shlex
import shutil
from collections.abc import Iterator
from pathlib import Path

import pytest

# Keep each BLAS runtime of the many short-lived runner processes to one thread;
# child runners inherit this.
for _thread_limit in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_thread_limit] = "1"


@pytest.fixture(autouse=True)
def _isolated_httk_config(tmp_path_factory: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch) -> None:
    """Give every test its own httk config and data home, so no workspace registry leaks between tests."""

    monkeypatch.setenv("HTTK_CONFIG_HOME", str(tmp_path_factory.mktemp("httk-config")))
    monkeypatch.setenv("HTTK_DATA_HOME", str(tmp_path_factory.mktemp("httk-store")))
    # A developer's launch prefix or confinement must not leak into the tests.
    for name in ("HTTK_WORKFLOW_LAUNCH", "HTTK_WORKFLOW_CONFINED", "HTTK_WORKFLOW_NODELIST"):
        monkeypatch.delenv(name, raising=False)


DATA = Path(__file__).resolve().parent / "data"
REPO_ROOT = Path(__file__).resolve().parent.parent


def orca_command() -> list[str] | None:
    """The real ORCA command from ``HTTK_TEST_ORCA_COMMAND``, else ``None``.

    There is deliberately no ``PATH`` fallback: ``orca`` on ``PATH`` is often the
    unrelated GNOME screen reader.
    """

    command = os.environ.get("HTTK_TEST_ORCA_COMMAND")
    return shlex.split(command) if command else None


requires_orca = pytest.mark.skipif(
    orca_command() is None,
    reason="needs a real, licensed ORCA: set HTTK_TEST_ORCA_COMMAND to its absolute path (no PATH lookup)",
)


@pytest.fixture
def installed_plugin(tmp_path_factory: pytest.TempPathFactory) -> Iterator[None]:
    """Install this repository's ``httk_plugin.toml`` workflows into the isolated data home."""

    from httk.core.plugins import install_plugin
    from httk.workflow.packages import _reset_plugin_workflow_cache

    source = tmp_path_factory.mktemp("plugin-source") / "httk-workflow-orca"
    shutil.copytree(REPO_ROOT / "workflows", source / "workflows", ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copy2(REPO_ROOT / "httk_plugin.toml", source)
    install_plugin(source)
    _reset_plugin_workflow_cache()
    yield
    _reset_plugin_workflow_cache()


def run_singlepoint(tmp_path: Path, command: str, capsys: pytest.CaptureFixture[str], **parameters: object) -> float:
    """Run and collect one ``orca.singlepoint`` job of water with *command*; return the stored energy in eV."""

    store = pytest.importorskip("httk.store")
    from httk.core import Run, TotalEnergyRecord
    from httk.core.cli import CLIContext
    from httk.workflow import TaskManager, Workspace
    from httk.workflow.registry import register_workspace
    from httk.workflow.scaffold import new_job
    from httk.workflow.workflow_cli import command as workflow_command

    workspace = Workspace.initialize(tmp_path / "workspace")
    workspace.set_setting("orca.command", command)
    job = new_job(workspace, "orca.singlepoint", inputs={"molecule": DATA / "water.xyz"}, parameters=parameters)
    with TaskManager(workspace, heartbeat_interval=0.01) as manager:
        manager.run_until_idle(timeout=600.0)
    marker = workspace.find_marker_by_id(job.job_id)
    assert marker is not None
    assert marker.kind == "succeeded", workspace.read_state(marker).get("failure")

    register_workspace("orca", str(workspace.root))
    database = tmp_path / "results.sqlite"
    arguments = ["collect", "--workspace", "orca", "--into", str(database), "--id-base", "httk.test", "--no-id-ledger"]
    assert workflow_command(arguments, CLIContext("httk", tmp_path)) == 0
    report = json.loads(capsys.readouterr().out.splitlines()[0])
    assert set(report["outputs"]) == {"total_energy"} and report["stored"]["run"]

    with store.Backend.sqlite(database) as backend:
        searcher = store.SqlStore(backend).searcher()
        energies = [row.energy for row in searcher.results(energy=searcher.variable(TotalEnergyRecord))]
        searcher = store.SqlStore(backend).searcher()
        runs = list(searcher.results(run=searcher.variable(Run)))
    assert len(energies) == 1 and len(runs) == 1
    return float(energies[0].total_energy)
