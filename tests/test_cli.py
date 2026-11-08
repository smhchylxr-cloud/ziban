"""The CLI is the part people actually touch first."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import List, Optional

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"


def run(args: List[str], stdin: Optional[str] = None) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(SRC)
    env["PYTHONIOENCODING"] = "utf-8"
    return subprocess.run(
        [sys.executable, "-m", "ziban", *args],
        input=stdin,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
        timeout=60,
    )


def test_json_output_matches_the_library():
    proc = run(["wrap", "-", "--width-em", "5", "--json"], stdin="你好，世界。")
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["engine"]["name"] == "ziban"
    assert [line["text"] for line in payload["lines"]] == ["你好，世界。"]
    assert payload["lines"][0]["adjustments"][0]["kind"] == "hang"


def test_terminal_output_draws_the_box():
    proc = run(["wrap", "-", "--width-em", "6"], stdin="第一行\n第二行")
    assert proc.returncode == 0, proc.stderr
    assert "|" in proc.stdout
    assert "第一行" in proc.stdout
    assert "2 line(s)" in proc.stdout


def test_hang_can_be_switched_off_from_the_cli():
    proc = run(["wrap", "-", "--width-em", "5", "--no-hang", "--json"], stdin="你好，世界。")
    payload = json.loads(proc.stdout)
    assert [line["text"] for line in payload["lines"]] == ["你好，世", "界。"]


def test_rules_command_prints_the_ruleset():
    proc = run(["rules", "--json"])
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert "，" in payload["head_forbidden"]
    assert payload["compressed_ratio"] == 0.5


def test_missing_file_is_a_clean_error():
    proc = run(["wrap", "definitely-not-here.txt"])
    assert proc.returncode == 2
    assert "file not found" in proc.stderr


def test_no_subcommand_prints_help():
    proc = run([])
    assert proc.returncode == 0
    assert "usage" in proc.stdout.lower()


def test_themes_are_listed():
    proc = run(["themes"])
    assert proc.returncode == 0, proc.stderr
    for name in ("ikb", "ink", "citron"):
        assert name in proc.stdout


def test_card_renders_a_spec(tmp_path: Path):
    pytest.importorskip("PIL", reason="card rendering needs Pillow")
    from ziban.fonts import FontSet

    try:
        FontSet.discover()
    except RuntimeError as exc:  # pragma: no cover - depends on the machine
        pytest.skip(str(exc))

    spec = Path(__file__).resolve().parents[1] / "examples" / "cards" / "specs" / "cover.json"
    out = tmp_path / "card.png"
    proc = run(["card", str(spec), "--theme", "ink", "--out", str(out)])
    assert proc.returncode == 0, proc.stderr
    assert out.exists()
    assert out.stat().st_size > 10_000
    assert "ink" in proc.stdout


def test_card_rejects_a_missing_spec():
    proc = run(["card", "no-such-spec.json"])
    assert proc.returncode == 2
    assert "not found" in proc.stderr
