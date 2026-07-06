# Changelog

All notable changes to the **AAIF Meetups Toolkit** plugin are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the
plugin version is the `version` field in `.claude-plugin/plugin.json`.

## [0.3.0]

### Added
- `aaif-sync-chapters` skill — sync organizer decisions from the **Intake Ops**
  sheet into the **Chapters List**: merge `Accepted` / `Existing (from MLOps)`
  organizers into each city row's Organizers column and append rows for net-new
  cities (with their Luma link). Report-and-propose by default, one atomic
  `batchUpdate` on approval, idempotent, with unresolved-city and near-miss-city
  guardrails. Unit tests for the pure merge/slug/near-miss logic.

### Fixed
- `gws` JSON parsing (`gws_json` in the sync, create-chapter, and
  create-online-series engines) now splits output on `\n` only — Python's
  `splitlines()` also splits on U+2028 (line separator) *inside* string values,
  which corrupted the JSON when rejoined (hit by a real intake row).
- `aaif-clean-data` treats **any** `Other…` city placeholder as unresolved — the
  form emits both `Other` and `Other (PLEASE TELL US WHERE IN NEXT QUESTION)`,
  and the exact-string match left long-variant rows unflagged (24 on live data)
  and wrongly painted their `City (Existing)` green. The green rule now checks
  the `Other` prefix; retired formulas are tracked in `LEGACY_COLOR_FORMULAS` so
  `install-colors` replaces old rules instead of stacking duplicates.

## [0.2.0]

### Added
- `aaif-create-online-series` skill — clone the **TemplateSeries** folder under the
  top-level **Online** Drive folder and rebrand it for a new online event series
  (reading group, paper club, webinar). The online sibling of `aaif-create-chapter`.
- Repo hardening: `$schema` references on both manifests, `.pre-commit-config.yaml`,
  Ruff config (`pyproject.toml`), and a `validate` CI workflow (pre-commit +
  `claude plugin validate`).

### Changed
- Manifest descriptions and tags now cover **online** meetups/series, not just
  in-person chapters.

## [0.1.0]

### Added
- Initial release: 11 skills for running AAIF in-person meetup chapters — content
  writing (announcement, carousel, Luma description, speaker invite/bio, day-of
  slides, attendee reminder, recap) and chapter ops (`aaif-create-chapter`,
  `aaif-triage-intake`, `aaif-clean-data`).
- One-plugin marketplace (`aaif`) packaging the toolkit for `/plugin install`.
