#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="${ROOT_DIR}/backend"
FRONTEND_DIR="${ROOT_DIR}/前端项目源码（fre）"

BACKEND_HOST="${BACKEND_HOST:-0.0.0.0}"
BACKEND_PORT="${BACKEND_PORT:-8001}"
FRONTEND_HOST="${FRONTEND_HOST:-0.0.0.0}"
FRONTEND_PORT="${FRONTEND_PORT:-8080}"

LOG_DIR="${ROOT_DIR}/.deploy_logs"
RUN_DIR="${ROOT_DIR}/.deploy_run"
BACKEND_PID_FILE="${RUN_DIR}/backend.pid"
FRONTEND_PID_FILE="${RUN_DIR}/frontend.pid"
BACKEND_LOG_FILE="${LOG_DIR}/backend.log"
FRONTEND_LOG_FILE="${LOG_DIR}/frontend.log"
BACKEND_ENV_FILE="${BACKEND_DIR}/.env"
BACKEND_VENV_DIR="${BACKEND_DIR}/.venv"

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "[ERROR] 缺少命令: $1"
    exit 1
  fi
}

port_in_use() {
  local port="$1"
  if command -v ss >/dev/null 2>&1; then
    ss -ltn | awk '{print $4}' | grep -Eq "(^|:)$port$"
    return $?
  fi

  if command -v lsof >/dev/null 2>&1; then
    lsof -iTCP:"${port}" -sTCP:LISTEN >/dev/null 2>&1
    return $?
  fi

  return 1
}

stop_managed_process() {
  local pid_file="$1"
  local service_name="$2"

  if [ ! -f "${pid_file}" ]; then
    return 0
  fi

  local pid
  pid="$(cat "${pid_file}")"
  if [ -n "${pid}" ] && kill -0 "${pid}" >/dev/null 2>&1; then
    echo "[INFO] 停止已有${service_name}进程: ${pid}"
    kill "${pid}" >/dev/null 2>&1 || true
    sleep 2
    if kill -0 "${pid}" >/dev/null 2>&1; then
      kill -9 "${pid}" >/dev/null 2>&1 || true
    fi
  fi

  rm -f "${pid_file}"
}

ensure_port_free() {
  local port="$1"
  local service_name="$2"
  if port_in_use "${port}"; then
    echo "[ERROR] ${service_name}端口 ${port} 已被占用，请先释放端口。"
    exit 1
  fi
}

require_cmd python3
require_cmd node
require_cmd npm

if ! command -v soffice >/dev/null 2>&1; then
  echo "[ERROR] 未找到 soffice，请先安装 LibreOffice。"
  echo "[HINT] sudo apt-get update && sudo apt-get install -y libreoffice"
  exit 1
fi

if [ ! -d "${BACKEND_DIR}" ] || [ ! -f "${BACKEND_DIR}/app/main.py" ]; then
  echo "[ERROR] 后端目录无效: ${BACKEND_DIR}"
  exit 1
fi

if [ ! -d "${FRONTEND_DIR}" ] || [ ! -f "${FRONTEND_DIR}/package.json" ]; then
  echo "[ERROR] 前端目录无效: ${FRONTEND_DIR}"
  exit 1
fi

mkdir -p "${LOG_DIR}" "${RUN_DIR}"

if [ ! -f "${BACKEND_ENV_FILE}" ]; then
  echo "[WARN] 未找到 ${BACKEND_ENV_FILE}，将使用默认数据库配置。"
fi

echo "[INFO] 准备后端 Python 环境..."
if [ ! -d "${BACKEND_VENV_DIR}" ]; then
  python3 -m venv "${BACKEND_VENV_DIR}"
fi
"${BACKEND_VENV_DIR}/bin/python" -m pip install --upgrade pip
"${BACKEND_VENV_DIR}/bin/pip" install -r "${BACKEND_DIR}/requirements.txt"

echo "[INFO] 安装前端依赖..."
cd "${FRONTEND_DIR}"
if [ -f "package-lock.json" ]; then
  npm ci --no-audit --no-fund
else
  npm install --no-audit --no-fund
fi

echo "[INFO] 构建前端..."
npm run build

stop_managed_process "${BACKEND_PID_FILE}" "后端"
stop_managed_process "${FRONTEND_PID_FILE}" "前端"

ensure_port_free "${BACKEND_PORT}" "后端"
ensure_port_free "${FRONTEND_PORT}" "前端"

echo "[INFO] 启动后端..."
cd "${BACKEND_DIR}"
if [ -f "${BACKEND_ENV_FILE}" ]; then
  set -a
  # shellcheck disable=SC1090
  . "${BACKEND_ENV_FILE}"
  set +a
else
  export DATABASE_URL="mysql+pymysql://root:root@127.0.0.1:3306/exam_recognition?charset=utf8mb4"
  export LIBREOFFICE_CMD="soffice"
fi

nohup "${BACKEND_VENV_DIR}/bin/python" -m uvicorn app.main:app --host "${BACKEND_HOST}" --port "${BACKEND_PORT}" > "${BACKEND_LOG_FILE}" 2>&1 &
echo $! > "${BACKEND_PID_FILE}"

echo "[INFO] 启动前端..."
cd "${FRONTEND_DIR}"
nohup npx --yes serve@14 -s dist -l "tcp://${FRONTEND_HOST}:${FRONTEND_PORT}" > "${FRONTEND_LOG_FILE}" 2>&1 &
echo $! > "${FRONTEND_PID_FILE}"

echo "[DONE] 前后端已启动。"
echo "[INFO] 前端地址: http://$(hostname -I | awk '{print $1}'):${FRONTEND_PORT}"
echo "[INFO] 后端地址: http://$(hostname -I | awk '{print $1}'):${BACKEND_PORT}"
echo "[INFO] Swagger: http://$(hostname -I | awk '{print $1}'):${BACKEND_PORT}/docs"
echo "[INFO] 后端日志: ${BACKEND_LOG_FILE}"
echo "[INFO] 前端日志: ${FRONTEND_LOG_FILE}"
