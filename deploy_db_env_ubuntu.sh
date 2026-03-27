#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="${ROOT_DIR}/backend"
SQL_FILE="${BACKEND_DIR}/sql/schema.sql"
ENV_FILE="${BACKEND_DIR}/.env"

MYSQL_HOST="${MYSQL_HOST:-127.0.0.1}"
MYSQL_PORT="${MYSQL_PORT:-3306}"
MYSQL_USER="${MYSQL_USER:-root}"
MYSQL_PASSWORD="${MYSQL_PASSWORD:-root}"
DB_NAME="${DB_NAME:-exam_recognition}"

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "[ERROR] 缺少命令: $1"
    exit 1
  fi
}

require_cmd mysql

if [ ! -f "${SQL_FILE}" ]; then
  echo "[ERROR] 未找到 SQL 文件: ${SQL_FILE}"
  exit 1
fi

echo "[INFO] 检查 MySQL 连接..."
mysql --protocol=TCP \
  -h "${MYSQL_HOST}" \
  -P "${MYSQL_PORT}" \
  -u"${MYSQL_USER}" \
  -p"${MYSQL_PASSWORD}" \
  -e "SELECT 1;" >/dev/null

echo "[INFO] 创建数据库和数据表..."
mysql --protocol=TCP \
  -h "${MYSQL_HOST}" \
  -P "${MYSQL_PORT}" \
  -u"${MYSQL_USER}" \
  -p"${MYSQL_PASSWORD}" \
  < "${SQL_FILE}"

mkdir -p "${BACKEND_DIR}/storage/uploads" "${BACKEND_DIR}/storage/pages"

if [ -f "${ENV_FILE}" ]; then
  cp "${ENV_FILE}" "${ENV_FILE}.bak.$(date +%Y%m%d%H%M%S)"
fi

cat > "${ENV_FILE}" <<EOF
DATABASE_URL=mysql+pymysql://${MYSQL_USER}:${MYSQL_PASSWORD}@${MYSQL_HOST}:${MYSQL_PORT}/${DB_NAME}?charset=utf8mb4
LIBREOFFICE_CMD=soffice
ALLOWED_ORIGINS=*
AUTO_CREATE_TABLES=true
EOF

echo "[DONE] 数据库初始化完成。"
echo "[INFO] 数据库: ${DB_NAME}"
echo "[INFO] 配置文件: ${ENV_FILE}"
