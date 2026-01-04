#!/usr/bin/env bash
set -e
VENV_DIR="${HOME}/simple_mag_venv"
PYTHON="$(which python3 || true)"
if [ -z "$PYTHON" ]; then
  echo "Zainstaluj python3 najpierw (np. sudo apt install python3 python3-venv)"
  exit 1
fi

echo "Tworzę venv w $VENV_DIR..."
$PYTHON -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"
pip install --upgrade pip

# Sprawdź czy istnieje requirements.txt
if [ -f "requirements.txt" ]; then
  echo "Instaluję zależności z requirements.txt..."
  pip install -r requirements.txt
else
  echo "Instaluję podstawowe zależności..."
  pip install pyside6 requests openpyxl
fi

echo "Gotowe. Uruchom: source $VENV_DIR/bin/activate && python app.py"
