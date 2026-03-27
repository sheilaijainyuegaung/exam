#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUN_DIR="${ROOT_DIR}/.deploy_run"

BACKEND_PORT="${BACKEND_PORT:-8001}"
FRONTEND_PORT="${FRONTEND_PORT:-8080}"

BACKEND_PID_FILE="${RUN_DIR}/backend.pid"
FRONTEND_PID_FILE="${RUN_DIR}/frontend.pid"

kill_pid_if_exists() {
  local pid_file="$1"
  local service_name="$2"

  if [ ! -f "${pid_file}" ]; then
    return 1
  fi

  local pid
  pid="$(cat "${pid_file}" 2>/dev/null || true)"
  if [ -z "${pid}" ]; then
    rm -f "${pid_file}"
    return 1
  fi

  if kill -0 "${pid}" >/dev/null 2>&1; then
    echo "[INFO] 停止${service_name}进程: ${pid}"
    kill "${pid}" >/dev/null 2>&1 || true
    sleep 2
    if kill -0 "${pid}" >/dev/null 2>&1; then
      kill -9 "${pid}" >/dev/null 2>&1 || true
    fi
    rm -f "${pid_file}"
    return 0
  fi

  rm -f "${pid_file}"
  return 1
}

find_pid_by_port() {
  local port="$1"

  if command -v lsof >/dev/null 2>&1; then
    lsof -tiTCP:"${port}" -sTCP:LISTEN 2>/dev/null | head -n 1
    return 0
  fi

  if command -v ss >/dev/null 2>&1; then
    ss -ltnp 2>/dev/null | awk -v port=":${port}" '$4 ~ port {print $NF}' | sed -n 's/.*pid=\([0-9]\+\).*/\1/p' | head -n 1
    return 0
  fi

  return 1
}

kill_by_port_if_needed() {
  local port="$1"
  local service_name="$2"
  local pid

  pid="$(find_pid_by_port "${port}" || true)"
  if [ -z "${pid}" ]; then
    return 1
  fi

  if kill -0 "${pid}" >/dev/null 2>&1; then
    echo "[INFO] 通过端口 ${port} 停止${service_name}进程: ${pid}"
    kill "${pid}" >/dev/null 2>&1 || true
    sleep 2
    if kill -0 "${pid}" >/dev/null 2>&1; then
      kill -9 "${pid}" >/dev/null 2>&1 || true
    fi
    return 0
  fi

  return 1
}

backend_stopped=0
frontend_stopped=0

if kill_pid_if_exists "${BACKEND_PID_FILE}" "后端"; then
  backend_stopped=1
elif kill_by_port_if_needed "${BACKEND_PORT}" "后端"; then
  backend_stopped=1
fi

if kill_pid_if_exists "${FRONTEND_PID_FILE}" "前端"; then
  frontend_stopped=1
elif kill_by_port_if_needed "${FRONTEND_PORT}" "前端"; then
  frontend_stopped=1
fi

if [ "${backend_stopped}" -eq 0 ]; then
  echo "[INFO] 未发现运行中的后端进程"
fi

if [ "${frontend_stopped}" -eq 0 ]; then
  echo "[INFO] 未发现运行中的前端进程"
fi

echo "[DONE] 停服脚本执行完成。"
