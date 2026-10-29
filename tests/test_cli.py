import json
import stat
import subprocess
import sys
from pathlib import Path

import pytest

from aci_blueprint.cli import main
from aci_blueprint.model import MAX_BYTES, InputError, load, sha256


@pytest.fixture
def source(tmp_path, design):
    path = tmp_path / "input.json"
    path.write_text(json.dumps(design))
    return path


def test_cli_build_and_no_overwrite(source, tmp_path, capsys):
    output = tmp_path / "result"
    args = ["build", "--input", str(source), "--output", str(output)]
    assert main(args) == 0
    assert "no APIC connection" in capsys.readouterr().out
    before = {p.name: p.read_bytes() for p in output.iterdir()}
    assert main(args) == 2
    assert "No files overwritten" in capsys.readouterr().err
    assert before == {p.name: p.read_bytes() for p in output.iterdir()}
    assert stat.S_IMODE(output.stat().st_mode) == 0o700
    assert all(stat.S_IMODE(p.stat().st_mode) == 0o600 for p in output.iterdir())


def test_symlink_destination_refused(source, tmp_path):
    existing = tmp_path / "existing"
    existing.mkdir()
    link = tmp_path / "link"
    link.symlink_to(existing, target_is_directory=True)
    assert main(["build", "--input", str(source), "--output", str(link)]) == 2
    assert list(existing.iterdir()) == []


def test_invalid_build_emits_no_payload(source, tmp_path, design):
    design["flows"][0]["consumer"] = "Store/Missing"
    source.write_text(json.dumps(design))
    output = tmp_path / "invalid"
    assert main(["build", "--input", str(source), "--output", str(output)]) == 1
    assert not (output / "tenant.json").exists()
    assert json.loads((output / "manifest.json").read_text())["result"] == "invalid-model"


def test_validate_is_read_only(source, tmp_path, capsys):
    assert main(["validate", "--input", str(source)]) == 0
    assert json.loads(capsys.readouterr().out)["valid"]
    assert list(tmp_path.iterdir()) == [source]


@pytest.mark.parametrize(
    "content",
    [
        b'{"a":1,"a":2}',
        b'{"a":NaN}',
        b'{"a":Infinity}',
        b'{"a":-Infinity}',
        b"[]",
        b"null",
        b"\xff",
        b"{",
        b"[" * 2000 + b"]" * 2000,
    ],
)
def test_malformed_json(tmp_path, content):
    path = tmp_path / "input"
    path.write_bytes(content)
    with pytest.raises(InputError):
        load(path)


def test_file_size_limit(tmp_path):
    path = tmp_path / "large"
    path.write_bytes(b" " * (MAX_BYTES + 1))
    with pytest.raises(InputError):
        load(path)


def test_hash_original_bytes(source, design):
    raw = (json.dumps(design, indent=4) + "\r\n").encode()
    source.write_bytes(raw)
    _, digest = load(source)
    assert digest == sha256(raw)


def test_unknown_fields_do_not_leak(source, design, tmp_path, capsys):
    design["password"] = "PRIVATE_TEST_SENTINEL"
    source.write_text(json.dumps(design))
    target = tmp_path / "should-not-exist"
    assert main(["build", "--input", str(source), "--output", str(target)]) == 2
    captured = capsys.readouterr()
    assert "PRIVATE_TEST_SENTINEL" not in captured.out + captured.err
    assert not target.exists()


def test_os_error_omits_private_path(tmp_path, capsys):
    assert main(["validate", "--input", str(tmp_path / "private-organization.json")]) == 2
    assert "private-organization" not in capsys.readouterr().err


def test_partial_write_has_no_manifest(source, tmp_path, monkeypatch):
    real_open = __import__("os").open

    def failing_open(path, *args):
        if Path(path).name == "tenant.json":
            raise OSError("simulated disk failure")
        return real_open(path, *args)

    monkeypatch.setattr("aci_blueprint.cli.os.open", failing_open)
    target = tmp_path / "partial"
    assert main(["build", "--input", str(source), "--output", str(target)]) == 2
    assert not (target / "manifest.json").exists()


def test_module_exit_status(source, tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "aci_blueprint.cli",
            "build",
            "--input",
            str(source),
            "--output",
            str(tmp_path / "subprocess"),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_offline_build_does_not_use_network(source, tmp_path, monkeypatch):
    def deny(*args, **kwargs):
        pytest.fail("Compiler attempted a network operation")

    monkeypatch.setattr("socket.socket", deny)
    monkeypatch.setattr("socket.create_connection", deny)
    assert main(["build", "--input", str(source), "--output", str(tmp_path / "offline")]) == 0
