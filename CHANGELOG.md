# Changelog

All notable changes to this project are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versioning follows [Semantic Versioning](https://semver.org/).

## [0.2.0] — 2026-11-09

The library can now finish the job: it draws the lines it broke, and ships four
card layouts that use it.

### Added

- **`ziban.draw`** — paints laid-out lines and honours the breaker's decisions:
  compressed punctuation is drawn compressed, hung punctuation crosses the
  margin, justified lines open the gaps the breaker counted, centred lines are
  centred on measured width.  Without this half, every caller re-implemented
  drawing and dropped the adjustments.
- **`ziban.cards`** — four layouts (`cover` / `list` / `steps` / `note`) that
  take a plain dict and return a 1080×1440 image plus diagnostics.
- **`ziban.theme`** — three palettes (`ikb`, `ink`, `citron`) and one type
  scale; a fourth theme is data, not code.
- **`ziban.fonts`** — probes Windows / macOS / Linux for a CJK font instead of
  bundling one, and selects the weight axis on variable fonts.
- **`ziban card` / `ziban themes`** CLI commands; `examples/cards/build.py`
  renders 12 cards and a contact sheet, failing loudly on `TEXT_OVERFLOW`.
- 36 new tests (994 total): rendering, determinism, theme application, font
  probing, and the drawing primitives.

### Fixed

- **Variable fonts defaulted to Thin.** Noto Sans SC-VF's default instance is
  weight 100, so every heading rendered in a hairline weight while looking
  plausible.  The weight axis is now selected explicitly for both regular and
  bold; `test_bold_is_actually_bolder` guards the regression.

- **Bold in `.ttc` collections.** macOS PingFang and Noto CJK ship several
  faces in one file; loading without an index always returns face 0, so bold
  rendered exactly like regular.  The loader now walks the faces and matches a
  semibold/bold style name.

### Known limitations

- **macOS PingFang still has no reachable bold face.** Pillow cannot address
  the semibold face of that collection reliably, so headings fall back to
  regular weight there.  Windows (Noto VF / YaHei Bold) and Linux
  (Noto CJK Bold) are unaffected.  Planned for 0.3: synthetic bold via
  `stroke_width`, or an explicit face index in `FontSet`.

## [0.1.1] — 2026-11-09

Packaging and metadata only; the engine is unchanged. First release published
by GitHub Actions through Trusted Publishing (OIDC) — no API token involved.

### Added

- Project links on PyPI (Homepage, Repository, Issues, Changelog).
- `build` and `twine` in the `dev` extra, so `pip install -e ".[dev]"` can
  build and check a release without extra installs.

### Changed

- `.gitignore` also covers tool output (`.dsh-pilot/`, `*.log`, coverage).
- Removed a local username from the publishing handbook; a public repo should
  not carry the machine account name.

## [0.1.0] — 2026-11-08

First public cut: the breaker works, the CLI works, the ruleset is data.
Published to PyPI as <https://pypi.org/project/ziban/0.1.0/>.

### Added

- **Line breaking for CJK**: greedy filling with kinship-aware repair
  (避头尾), so closing marks never start a line and opening marks never end one.
- **Punctuation compression** (标点挤压): a full-width mark is drawn at half
  width when that is what makes the line fit.
- **Hanging punctuation** (行末悬挂): a mark may sit outside the margin, capped
  at one em *and* a quarter of the measure, so narrow columns do not bleed.
- **Diagnostics as data**: `OVERFLOW`, `NO_BREAK_OPPORTUNITY`,
  `KINSOKU_FALLBACK`, `ORPHAN_LINE`, each with a line number, a message and a
  suggested fix. The engine never silently produces a bad line.
- **Metrics abstraction**: `EmMetrics` (font-free, deterministic) and
  `PillowMetrics` (real font files, 4× supersampled).
- **Rule sets as TOML** (`src/ziban/data/clreq.toml`), derived from
  [CLREQ](https://www.w3.org/TR/clreq/), with additive overrides in Python.
- **CLI**: `ziban wrap` (terminal view, ruler, `--json`) and `ziban rules`.
- **958 tests**: 24 paragraphs × 6 measures × 6 invariants, plus golden cases,
  unit tests, CLI tests and a 100k-character stress test.

### Known limitations

- Horizontal text only.
- No pair compression yet (`「。」` still costs two em on some lines).
- No justification across Latin word spaces beyond a uniform extra gap.
- No font probing: you pass a path or use `EmMetrics`.
