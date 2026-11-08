"""Font probing: never ship a font, never silently render at the wrong weight."""

from __future__ import annotations

from pathlib import Path

import pytest

PIL = pytest.importorskip("PIL", reason="font loading needs Pillow (ziban[pillow])")

from PIL import Image, ImageDraw  # noqa: E402

from ziban.fonts import FontSet, candidates, find_bold, find_regular  # noqa: E402


def _ink(font, text: str = "排版Ab") -> int:
    canvas = Image.new("L", (360, 180), 255)
    ImageDraw.Draw(canvas).text((10, 10), text, font=font, fill=0)
    return sum(1 for value in canvas.tobytes() if value < 128)


def test_candidates_are_ordered_and_absolute():
    table = candidates()
    assert table, "every platform needs at least one candidate"
    assert all(path.is_absolute() for triple in table for path in triple)


def test_discover_finds_three_files_or_skips():
    try:
        fonts = FontSet.discover()
    except RuntimeError as exc:  # pragma: no cover - depends on the machine
        pytest.skip(str(exc))
    assert fonts.regular.exists()
    assert fonts.bold.exists()
    assert fonts.mono.exists()
    assert find_regular().exists()
    assert find_bold().exists()


def _can_go_bolder(fonts: FontSet) -> bool:
    """True when this machine actually offers a bolder face than regular."""
    if fonts.bold.resolve() != fonts.regular.resolve():
        return True  # a distinct bold file
    face = fonts.load(72, weight="bold")
    try:
        if face.get_variation_axes():
            return True  # variable font: the weight axis can be set numerically
    except Exception:
        pass
    style = (face.getname()[1] or "").strip().lower()
    return style not in ("", "regular", "book")


def test_bold_is_actually_bolder():
    """A variable font's default instance is not always Regular.

    Noto Sans SC-VF defaults to weight 100 (Thin), so "load the same file twice"
    renders every heading in a hairline weight and looks plausible until you put
    it next to a real bold.  This test is the guard against that regression.

    Skipped only where the platform genuinely ships a single CJK weight —
    macOS PingFang.ttc exposes several faces but Pillow cannot reach the
    semibold one, which is a known limitation, not a pass.
    """
    try:
        fonts = FontSet.discover()
    except RuntimeError as exc:  # pragma: no cover
        pytest.skip(str(exc))

    if not _can_go_bolder(fonts):
        pytest.skip(f"{fonts.regular.name} exposes no bolder face on this platform")

    regular_ink = _ink(fonts.load(72, weight="regular"))
    bold_ink = _ink(fonts.load(72, weight="bold"))
    assert regular_ink > 0
    assert bold_ink > regular_ink * 1.2, f"bold ink {bold_ink} vs regular {regular_ink} — weight not applied"


def test_from_path_rejects_missing_file(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        FontSet.from_path(tmp_path / "nope.ttf")


def test_from_path_uses_one_file_for_all_weights(tmp_path: Path):
    try:
        base = FontSet.discover().regular
    except RuntimeError as exc:  # pragma: no cover
        pytest.skip(str(exc))
    fonts = FontSet.from_path(base)
    assert fonts.regular == fonts.bold == fonts.mono
    assert fonts.load(24, weight="bold").size == 24
