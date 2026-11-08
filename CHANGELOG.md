# Changelog

All notable changes to this project are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versioning follows [Semantic Versioning](https://semver.org/).

## [0.1.0] — unreleased

First public cut: the breaker works, the CLI works, the ruleset is data.

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
