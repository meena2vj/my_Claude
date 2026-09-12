# Pharma Data Security & Compliance Demo

A Streamlit demo app built to the guardrails in [CLAUDE.md](CLAUDE.md):
synthetic pharma data only, role-based access, audit logging, and a
documented demo-only risk model. See [docs/dataset_dictionary.md](docs/dataset_dictionary.md)
and [docs/model_card.md](docs/model_card.md) for details.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt   # or requirements.txt for runtime-only
cp .env.example .env                  # demo users/passwords live here
```

## Run

```bash
streamlit run app.py --server.port 8501 --server.address 0.0.0.0
```

Open http://localhost:8501. Synthetic data is generated automatically into a
gitignored `data/` folder on first run.

Demo logins (see `.env.example` to change or add users):

| Username | Password | Role |
|---|---|---|
| admin | admin-demo-123 | admin — all tabs, audit log |
| analyst | analyst-demo-123 | analyst — most tabs, aggregated export |
| viewer | viewer-demo-123 | viewer — read-only overview |

## Test / scan

```bash
python -m pytest -q
python -m bandit -r . -x ./.venv,./tests
python -m pip-audit -r requirements.txt
```

## Pre-commit hooks

```bash
pre-commit install
```

Blocks committing `.env`, scans for private keys, and enforces the synthetic
data marker on any committed `data/*.csv` (data files are gitignored by
default and shouldn't normally be committed at all).
