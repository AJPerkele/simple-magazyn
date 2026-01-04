#!/usr/bin/env bash
VENV_DIR="${HOME}/simple_mag_venv"
if [ -d "$VENV_DIR" ]; then
  source "$VENV_DIR/bin/activate"
fi
python3 app.py
