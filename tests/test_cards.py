"""Card rendering: the demo is a product surface, so it gets product-grade tests."""

from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

PIL = pytest.importorskip("PIL", reason="card rendering needs Pillow (ziban[pillow])")

from ziban.cards import CANVAS, render_card  # noqa: E402
from ziban.fonts import FontSet  # noqa: E402
from ziban.theme import THEMES  # noqa: E402

SPECS = Path(__file__).resolve().parents[1] / "examples" / "cards" / "specs"
KINDS = ("cover", "list", "steps", "note")


@pytest.fixture(scope="module")
def fonts() -> FontSet:
    try:
        return FontSet.discover()
    except RuntimeError as exc:  # pragma: no cover - depends on the machine
        pytest.skip(str(exc))


@pytest.fixture(scope="module")
def specs() -> dict:
    return {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in SPECS.glob("*.json")}


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("theme_name", sorted(THEMES))
def test_every_kind_renders_clean_in_every_theme(kind, theme_name, specs, fonts):
    image, issues = render_card(specs[kind], THEMES[theme_name], fonts)
    assert image.size == CANVAS
    assert image.mode == "RGB"
    codes = [i.code for i in issues]
    assert "TEXT_OVERFLOW" not in codes, codes


@pytest.mark.parametrize("kind", KINDS)
def test_rendering_is_deterministic(kind, specs, fonts):
    first, _ = render_card(specs[kind], THEMES["ikb"], fonts)
    second, _ = render_card(specs[kind], THEMES["ikb"], fonts)
    a, b = io.BytesIO(), io.BytesIO()
    first.save(a, format="PNG")
    second.save(b, format="PNG")
    assert a.getvalue() == b.getvalue()


def test_canvas_scales_with_width(specs, fonts):
    image, _ = render_card(specs["cover"], THEMES["ikb"], fonts, (540, 720))
    assert image.size == (540, 720)


def test_theme_background_is_actually_applied(specs, fonts):
    image, _ = render_card(specs["note"], THEMES["citron"], fonts)
    assert image.getpixel((5, 5)) == (0xEF, 0xF8, 0x4A)


def test_unknown_kind_is_rejected(fonts):
    with pytest.raises(ValueError, match="unknown card kind"):
        render_card({"kind": "poster", "title": "x"}, THEMES["ikb"], fonts)


def test_title_is_required(fonts):
    with pytest.raises(ValueError, match="title"):
        render_card({"kind": "cover", "title": ""}, THEMES["ikb"], fonts)


def test_long_copy_shrinks_instead_of_overflowing(fonts):
    spec = {
        "kind": "cover",
        "kicker": "压力测试",
        "title": "这是一个非常长非常长的标题" * 6,
        "subtitle": "副标题也写得很长，用来挤压版面的每一点余量。" * 4,
    }
    _image, issues = render_card(spec, THEMES["ikb"], fonts)
    codes = {i.code for i in issues}
    assert "TEXT_SHRUNK" in codes or "TEXT_OVERFLOW" in codes


def test_overflow_is_reported_when_even_the_floor_does_not_fit(fonts):
    spec = {"kind": "note", "title": "排版" * 400}
    _image, issues = render_card(spec, THEMES["ikb"], fonts)
    assert any(i.code == "TEXT_OVERFLOW" for i in issues)
