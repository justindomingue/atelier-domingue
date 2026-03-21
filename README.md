# Atelier Domingue

A pattern-drafting system for garments — trouser blocks, selvedge jeans, and a basic shirt — built from historical tailoring methods.

## Quick start

```bash
pip install -r requirements.txt

# Interactive (uses fzf to pick program, measurements, units)
python run.py

# Non-interactive
python run.py -p "1873 Selvedge Denim Jeans" -m measurements/justin_1873_jeans.yaml --units cm
```

Output is written to `Logs/`.

## Running tests

```bash
python -m pytest tests/
```

### Regression tests

Geometry-snapshot tests lock the coordinates returned by each `draft_*`
function so refactors can't silently shift a seam:

```bash
python -m pytest tests/test_regression_snapshots.py
```

After an intentional geometry change, regenerate the baselines:

```bash
python -m tests.regression.generate_snapshots
```

## More

See [architecture.md](architecture.md) for directory layout, how the runner discovers garments, how to add a new garment program, and design decisions.
