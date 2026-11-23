#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if ! docker info >/dev/null 2>&1; then
  echo "O Docker nao esta aberto, entao o MUFASA ja esta desligado."; exit 0
fi
docker compose stop
echo "[ok] MUFASA desligado. Para ligar de novo: ./iniciar_mufasa.sh"
