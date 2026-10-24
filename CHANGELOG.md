# Changelog

All notable changes to this project will be documented in this file.

## [1.1.0] - 2026-10-23
### Added
- **Dynamic Role Assignment**: Roles are rebalanced between matches based on the previous match’s outcome.
- **Sub-Agent Framework**: Bots are split into Analyst, Speechwriter, and Strategist sub-agents.
- **GM Penalty for Silence**: Bots silent for 2 consecutive days receive an automatic vote.
- **Token Budget Enforcement**: Enforces the 10,000-token limit per bot per cycle.
- **Setup Scripts**: `setup.py` automates keypair generation and `seats.json` population.
- **GM Action Reliability**: Dynamic cron scheduling and manual triggers for testing.
- **Encryption Improvements**: Key validation and ephemeral keys for matches.

- **Debugging Tools**: Verbose mode for bots (`--verbose` flag).

### Changed
- Updated `README.md` and `setup/rules.md` to reflect improvements.
- Adjusted win conditions to reduce Mafia advantage.

### Fixed
- GM Action race conditions with concurrency control.
- Encryption failures with key validation.

## [1.0.0] - 2026-10-20
### Added
- Initial release of *Bazaar of Lies: Omertà Edition*.
- Core game logic (GM, roles, phases, encryption).
- Example personas and doctrines.