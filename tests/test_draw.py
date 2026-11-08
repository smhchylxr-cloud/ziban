"""Drawing must honour what the breaker decided."""

from __future__ import annotations

from ziban import Adjustment, Line, Style, layout
from ziban.draw import draw_line, draw_lines
from ziban.metrics import EmMetrics


class Recorder:
    """A stand-in for PIL's ImageDraw: records what lands where."""

    def __init__(self) -> None:
        self.calls = []

    def text(self, xy, text, font=None, fill=None):  # noqa: A003 - PIL's name
        self.calls.append((round(xy[0], 2), round(xy[1], 2), text))


def _line(text: str, **kwargs) -> Line:
    return Line(text=text, width=0.0, start=0, end=len(text), **kwargs)


def test_plain_line_advances_by_measured_width():
    metrics = EmMetrics(36)
    rec = Recorder()
    end = draw_line(rec, 100, 0, _line("中文"), font=None, metrics=metrics, fill="#000")
    assert end == 100 + 72
    assert [c[2] for c in rec.calls] == ["中", "文"]


def test_compressed_cluster_takes_less_room():
    metrics = EmMetrics(36)
    plain = draw_line(Recorder(), 0, 0, _line("中文，"), font=None, metrics=metrics, fill="#000")
    squeezed = draw_line(
        Recorder(),
        0,
        0,
        _line("中文，", adjustments=(Adjustment("compress", 2, 14.0),)),
        font=None,
        metrics=metrics,
        fill="#000",
    )
    assert squeezed == plain - 14.0


def test_hang_does_not_shrink_the_line():
    metrics = EmMetrics(36)
    plain = draw_line(Recorder(), 0, 0, _line("中文。"), font=None, metrics=metrics, fill="#000")
    hung = draw_line(
        Recorder(),
        0,
        0,
        _line("中文。", adjustments=(Adjustment("hang", 2, 18.0),)),
        font=None,
        metrics=metrics,
        fill="#000",
    )
    assert hung == plain  # the mark still occupies its full advance


def test_justification_opens_the_gaps():
    metrics = EmMetrics(36)
    plain = draw_line(Recorder(), 0, 0, _line("中文图"), font=None, metrics=metrics, fill="#000")
    justified = draw_line(
        Recorder(),
        0,
        0,
        _line("中文图"),
        font=None,
        metrics=metrics,
        fill="#000",
        justify=6.0,
    )
    assert justified == plain + 12.0  # two gaps between three clusters


def test_draw_lines_reports_the_y_below_the_block():
    metrics = EmMetrics(40)
    laid = layout("一二三四五六七八九十", width=200, style=Style(size=40, leading=1.5), metrics=metrics)
    rec = Recorder()
    bottom = draw_lines(
        rec,
        10,
        100,
        laid,
        font=None,
        metrics=metrics,
        fill="#000",
        leading=1.5,
    )
    assert bottom == 100 + len(laid.lines) * 60
    assert len(rec.calls) == sum(len(line.text) for line in laid.lines)


def test_centred_line_is_shifted_by_half_the_slack():
    metrics = EmMetrics(40)
    laid = layout("一二三", width=400, style=Style(size=40, align="center"), metrics=metrics)
    rec = Recorder()
    draw_lines(rec, 0, 0, laid, font=None, metrics=metrics, fill="#000", width=400)
    first_x = rec.calls[0][0]
    assert first_x == (400 - 120) / 2
