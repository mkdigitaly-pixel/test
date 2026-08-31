#!/bin/bash
# Автозапуск слотов на сегодня (МСК). Вызывается cron / Cloud Agent timer.
set -euo pipefail
cd "$(dirname "$0")"
python3 publish.py schedule sync-urls
python3 publish.py schedule run
