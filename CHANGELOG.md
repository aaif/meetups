# Changelog

All notable changes to the **AAIF Meetups Toolkit** plugin are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the
plugin version is the `version` field in `.claude-plugin/plugin.json`.

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
