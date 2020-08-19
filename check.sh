#!/bin/sh
#
# Small script to ensure quality checks pass before submitting a commit/PR.
#
python -m black trafic
python -m flake8 trafic
python -m mypy  --ignore-missing-imports --warn-unused-ignores trafic
