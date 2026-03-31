@echo off
python run.py
python -m http.server 8000 --directory results
