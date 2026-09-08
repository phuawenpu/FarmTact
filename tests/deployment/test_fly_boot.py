from __future__ import annotations

import os
from pathlib import Path
import signal
import subprocess
import tomllib
from types import SimpleNamespace

import pytest

from scripts import fly_boot


ROOT = Path(__file__).parents[2]


def test_postgres_is_unix_socket_only() -> None:
    command = fly_boot.postgres_command()
    rendered = " ".join(command)
    assert command[0] == "postgres"
    assert "listen_addresses=" in command
    assert f"unix_socket_directories={fly_boot.SOCKET}" in command
    assert "port=" not in rendered
    assert "log_min_error_statement=panic" in command


def test_public_environment_removes_every_known_credential(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for name in fly_boot.SECRET_NAMES:
        monkeypatch.setenv(name, f"sentinel-{name}")
    monkeypatch.setenv("FARMTACT_DATA_MODE", "synthetic_demo")

    public = fly_boot.public_environment()

    assert all(name not in public for name in fly_boot.SECRET_NAMES)
    assert public["FARMTACT_DATA_MODE"] == "synthetic_demo"


def test_boot_refuses_to_supervise_as_root(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(fly_boot.os, "geteuid", lambda: 0)
    with pytest.raises(RuntimeError, match="unprivileged"):
        fly_boot.main()


def test_wrong_persistent_postgres_major_fails_before_starting_processes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pgdata = tmp_path / "postgres"
    pgdata.mkdir()
    (pgdata / "PG_VERSION").write_text("17\n", encoding="utf-8")
    real_path = Path
    monkeypatch.setattr(fly_boot, "PGDATA", pgdata)
    monkeypatch.setattr(
        fly_boot,
        "Path",
        lambda value: tmp_path / "public-data" if value == "/data/public-data" else real_path(value),
    )
    monkeypatch.setattr(fly_boot.os, "geteuid", lambda: 10001)
    monkeypatch.setattr(
        fly_boot.subprocess,
        "run",
        lambda *args, **kwargs: pytest.fail("must fail before invoking a command"),
    )
    monkeypatch.setattr(
        fly_boot.subprocess,
        "Popen",
        lambda *args, **kwargs: pytest.fail("must fail before starting a process"),
    )

    with pytest.raises(RuntimeError, match="explicit migration"):
        fly_boot.main()


class _Process:
    def __init__(self, command: list[str], waits: list[float], *, force_kill: bool) -> None:
        self.command = command
        self.returncode: int | None = None
        self.signals: list[signal.Signals] = []
        self.killed = False
        self._waits = waits
        self._force_kill = force_kill
        self._first_wait = True

    def poll(self) -> int | None:
        return self.returncode

    def send_signal(self, sig: signal.Signals) -> None:
        self.signals.append(sig)

    def wait(self, timeout: float) -> int:
        self._waits.append(timeout)
        if self._force_kill and self._first_wait:
            self._first_wait = False
            raise subprocess.TimeoutExpired(self.command, timeout)
        self.returncode = -9 if self.killed else 0
        return self.returncode

    def kill(self) -> None:
        self.killed = True


def _exercise_supervisor(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    force_kill: bool = False,
) -> tuple[list[tuple[list[str], dict]], list[_Process], list[float]]:
    pgdata = tmp_path / "postgres"
    pgdata.mkdir()
    (pgdata / "PG_VERSION").write_text("18\n", encoding="utf-8")
    real_path = Path
    handlers: dict[int, object] = {}
    popen_calls: list[tuple[list[str], dict]] = []
    processes: list[_Process] = []
    waits: list[float] = []

    monkeypatch.setattr(fly_boot, "PGDATA", pgdata)
    monkeypatch.setattr(
        fly_boot,
        "Path",
        lambda value: tmp_path / "public-data" if value == "/data/public-data" else real_path(value),
    )
    monkeypatch.setattr(fly_boot.os, "geteuid", lambda: 10001)
    monkeypatch.setattr(fly_boot.signal, "signal", lambda sig, callback: handlers.setdefault(sig, callback))

    def fake_run(command, **kwargs):
        if command[0] == "pg_isready":
            return SimpleNamespace(returncode=0, stdout="")
        if command[0] == "psql":
            return SimpleNamespace(returncode=0, stdout="1\n")
        if str(command[0]) == os.fspath(Path(fly_boot.sys.executable)):
            return SimpleNamespace(returncode=0, stdout="")
        pytest.fail(f"unexpected command: {command}")

    def fake_popen(command, **kwargs):
        copied_command = [str(part) for part in command]
        popen_calls.append((copied_command, dict(kwargs)))
        process = _Process(copied_command, waits, force_kill=force_kill)
        processes.append(process)
        return process

    stopped = False

    def fake_sleep(_: float) -> None:
        nonlocal stopped
        if len(processes) == 3 and not stopped:
            stopped = True
            handlers[signal.SIGTERM](signal.SIGTERM, None)  # type: ignore[operator]

    monkeypatch.setattr(fly_boot.subprocess, "run", fake_run)
    monkeypatch.setattr(fly_boot.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(fly_boot.time, "sleep", fake_sleep)

    assert fly_boot.main() == 0
    return popen_calls, processes, waits


def test_child_processes_receive_only_the_credentials_they_need(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    for name in fly_boot.SECRET_NAMES:
        monkeypatch.setenv(name, f"sentinel-{name}")

    calls, processes, _ = _exercise_supervisor(tmp_path, monkeypatch)
    postgres_call, web_call, refresh_call = calls
    postgres_env = postgres_call[1]["env"]
    refresh_env = refresh_call[1]["env"]
    # An omitted env means Popen inherits every credential from the supervisor.
    web_env = web_call[1].get("env", os.environ)

    assert all(name not in postgres_env for name in fly_boot.SECRET_NAMES)
    assert all(name not in refresh_env for name in fly_boot.SECRET_NAMES)
    assert web_env["DEEPSEEK_API_KEY"] == "sentinel-DEEPSEEK_API_KEY"
    assert all(
        name not in web_env
        for name in fly_boot.SECRET_NAMES
        if name != "DEEPSEEK_API_KEY"
    )
    assert processes[0].signals == [signal.SIGINT]
    assert processes[1].signals == [signal.SIGTERM]


def test_forced_shutdown_wait_budget_fits_inside_fly_kill_timeout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, _, waits = _exercise_supervisor(tmp_path, monkeypatch, force_kill=True)
    fly_config = tomllib.loads((ROOT / "fly.toml").read_text(encoding="utf-8"))
    # Leave time for PID 1 scheduling, loop latency, and filesystem cleanup.
    assert sum(waits) + 5 <= fly_config["kill_timeout"]


def test_signal_handler_precedes_bounded_initdb_and_prevents_postgres_start(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pgdata = tmp_path / "postgres"
    real_path = Path
    handlers: dict[int, object] = {}
    initdb_timeout: list[float] = []

    monkeypatch.setattr(fly_boot, "PGDATA", pgdata)
    monkeypatch.setattr(
        fly_boot,
        "Path",
        lambda value: tmp_path / "public-data" if value == "/data/public-data" else real_path(value),
    )
    monkeypatch.setattr(fly_boot.os, "geteuid", lambda: 10001)
    monkeypatch.setattr(fly_boot.signal, "signal", lambda sig, callback: handlers.setdefault(sig, callback))

    def interrupt_initdb(command, **kwargs):
        assert command[0] == "initdb"
        assert signal.SIGTERM in handlers
        assert isinstance(kwargs.get("timeout"), (int, float))
        initdb_timeout.append(kwargs["timeout"])
        handlers[signal.SIGTERM](signal.SIGTERM, None)  # type: ignore[operator]
        return SimpleNamespace(returncode=0, stdout="")

    monkeypatch.setattr(fly_boot.subprocess, "run", interrupt_initdb)
    monkeypatch.setattr(
        fly_boot.subprocess,
        "Popen",
        lambda *args, **kwargs: pytest.fail("termination during init must prevent PostgreSQL start"),
    )

    assert fly_boot.main() == 0
    fly_config = tomllib.loads((ROOT / "fly.toml").read_text(encoding="utf-8"))
    assert initdb_timeout[0] + 5 <= fly_config["kill_timeout"]


def test_signal_during_database_probe_prevents_remaining_startup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pgdata = tmp_path / "postgres"
    pgdata.mkdir()
    (pgdata / "PG_VERSION").write_text("18\n", encoding="utf-8")
    real_path = Path
    handlers: dict[int, object] = {}
    commands: list[str] = []
    waits: list[float] = []
    database = _Process(["postgres"], waits, force_kill=False)

    monkeypatch.setattr(fly_boot, "PGDATA", pgdata)
    monkeypatch.setattr(
        fly_boot,
        "Path",
        lambda value: tmp_path / "public-data" if value == "/data/public-data" else real_path(value),
    )
    monkeypatch.setattr(fly_boot.os, "geteuid", lambda: 10001)
    monkeypatch.setattr(fly_boot.signal, "signal", lambda sig, callback: handlers.setdefault(sig, callback))
    monkeypatch.setattr(fly_boot.subprocess, "Popen", lambda command, **kwargs: database)

    def interrupt_probe(command, **kwargs):
        commands.append(command[0])
        if command[0] == "pg_isready":
            return SimpleNamespace(returncode=0, stdout="")
        if command[0] == "psql":
            handlers[signal.SIGTERM](signal.SIGTERM, None)  # type: ignore[operator]
            return SimpleNamespace(returncode=0, stdout="1\n")
        pytest.fail(f"termination must prevent remaining startup command: {command}")

    monkeypatch.setattr(fly_boot.subprocess, "run", interrupt_probe)

    assert fly_boot.main() == 0
    assert commands == ["pg_isready", "psql"]
    assert database.signals == [signal.SIGINT]


def test_schema_failure_stops_database_and_never_starts_web(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pgdata = tmp_path / "postgres"
    pgdata.mkdir()
    (pgdata / "PG_VERSION").write_text("18\n", encoding="utf-8")
    real_path = Path
    handlers: dict[int, object] = {}
    waits: list[float] = []
    database = _Process(["postgres"], waits, force_kill=False)
    popen_count = 0

    monkeypatch.setattr(fly_boot, "PGDATA", pgdata)
    monkeypatch.setattr(
        fly_boot,
        "Path",
        lambda value: tmp_path / "public-data" if value == "/data/public-data" else real_path(value),
    )
    monkeypatch.setattr(fly_boot.os, "geteuid", lambda: 10001)
    monkeypatch.setattr(fly_boot.signal, "signal", lambda sig, callback: handlers.setdefault(sig, callback))

    def fake_popen(command, **kwargs):
        nonlocal popen_count
        popen_count += 1
        if popen_count > 1:
            pytest.fail("web must not start after schema initialization fails")
        return database

    def fake_run(command, **kwargs):
        if command[0] == "pg_isready":
            return SimpleNamespace(returncode=0, stdout="")
        if command[0] == "psql":
            return SimpleNamespace(returncode=0, stdout="1\n")
        raise subprocess.CalledProcessError(1, command)

    monkeypatch.setattr(fly_boot.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(fly_boot.subprocess, "run", fake_run)

    with pytest.raises(subprocess.CalledProcessError):
        fly_boot.main()
    assert popen_count == 1
    assert database.signals == [signal.SIGINT]


def test_fly_image_has_runtime_import_smoke_and_no_database_port() -> None:
    dockerfile = (ROOT / "Dockerfile.fly").read_text(encoding="utf-8")
    fly_config = (ROOT / "fly.toml").read_text(encoding="utf-8")
    assert "FROM postgres:18-bookworm" in dockerfile
    assert "EXPOSE 5432" not in dockerfile
    assert "internal_port = 8080" in fly_config
    assert "5432" not in fly_config
    assert "chmod -R a+rX /app" in dockerfile
    assert "chown -R farmtact:farmtact /app" not in dockerfile
    assert "gosu farmtact python" in dockerfile
    # Copying /usr/local between Bookworm images is portable only if the compiled
    # runtime dependency set is verified during the image build.
    for module in ("psycopg", "sqlalchemy", "duckdb", "pyarrow", "ortools", "PIL"):
        assert module in dockerfile
