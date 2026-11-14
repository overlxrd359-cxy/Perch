#!/usr/bin/env bash
# 数据库备份。
#
# 用法：
#   ./deploy/scripts/backup.sh
#   建议加到 crontab：0 3 * * * /path/to/backup.sh >> /var/log/seat-backup.log 2>&1
#
# 恢复演练（必须真做过一次）：
#   gunzip -c data/backups/xxx.sql.gz | docker compose -f deploy/docker-compose.prod.yml exec -T mysql \
#     mysql -uroot -p"$MYSQL_ROOT_PASSWORD" campus_seat

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="${COMPOSE_FILE:-${SCRIPT_DIR}/../docker-compose.prod.yml}"
BACKUP_DIR="${BACKUP_DIR:-${SCRIPT_DIR}/../data/backups}"
KEEP_DAYS="${KEEP_DAYS:-14}"
DB_NAME="${MYSQL_DATABASE:-campus_seat}"

mkdir -p "${BACKUP_DIR}"

STAMP="$(date +%Y%m%d-%H%M%S)"
TARGET="${BACKUP_DIR}/seat-${STAMP}.sql.gz"

echo "[backup] dumping ${DB_NAME} -> ${TARGET}"

docker compose -f "${COMPOSE_FILE}" exec -T mysql \
  sh -c 'exec mysqldump -uroot -p"$MYSQL_ROOT_PASSWORD" \
    --single-transaction --quick --routines --triggers --events "$MYSQL_DATABASE"' \
  | gzip -9 > "${TARGET}"

# 校验压缩包完整性，避免生成一个坏文件还以为备份成功
gzip -t "${TARGET}"
SIZE="$(du -h "${TARGET}" | cut -f1)"
echo "[backup] done, size=${SIZE}"

echo "[backup] pruning files older than ${KEEP_DAYS} days"
find "${BACKUP_DIR}" -name 'seat-*.sql.gz' -type f -mtime "+${KEEP_DAYS}" -print -delete

echo "[backup] ok"