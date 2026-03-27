#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${BACKEND_DIR}"

if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi

. ".venv/bin/activate"
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

export DATABASE_URL="${DATABASE_URL:-mysql+pymysql://root:root@127.0.0.1:3306/exam_recognition?charset=utf8mb4}"
export LIBREOFFICE_CMD="${LIBREOFFICE_CMD:-soffice}"

python -m uvicorn app.main:app --host 0.0.0.0 --port 8001
