Author: Imaad Ullah Khan Yameen  
Email: yameenimaad@gmail.com  
*This code is not for sale*

# Contributing

Thanks for helping. Please read the [LICENSE](LICENSE) first: contributions are accepted under the same
noncommercial licence, and the author may also relicense them for commercial licences he grants. By opening a
pull request you confirm that you wrote the change (or may share it) and agree to this.

## Rules
1. Every new source file starts with the author header (`# Author: Imaad Ullah Khan Yameen` / e-mail /
   `# This code is not for sale.`; for Markdown the same three lines). A test enforces this.
2. Run `python -m pytest` before sending anything. All tests must pass.
3. Colours, fonts and padding come from `DESIGN.md`; undocumented values fail the design test.
4. No secrets, keys, telemetry or new network hosts. If you add a network call, update `policy.json`,
   `PRIVACY.md` and the wiki `Security.md`.
5. Keep versions in step (`atlasa0/__init__.py`, `pyproject.toml`, `policy.json`, installer, SECURITY.md).
6. Add tests for new behaviour and update `milestone.md` and the wiki.

## Setup
```
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
python -m pytest
```
Security problems: do not open a public issue; see [SECURITY.md](SECURITY.md).
