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

## More

See [architecture.md](architecture.md) for directory layout, how the runner discovers garments, how to add a new garment program, and design decisions.
