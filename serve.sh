#!/usr/bin/env bash
set -e

python run.py
python -m http.server 8000 --directory results
