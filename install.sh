#!/bin/bash
# Uso: bash install.sh <nombre-del-sitio>
# Ejemplo: bash install.sh workaholic.omniaos.ai

SITE=${1:?"Uso: bash install.sh <nombre-del-sitio>"}
APP="gastos_prorrateados"
BENCH_DIR="/home/frappe/frappe-bench"
APPS_TXT="$BENCH_DIR/sites/apps.txt"

echo "==> Obteniendo $APP desde GitHub..."
cd "$BENCH_DIR" && bench get-app https://github.com/OmniaOs/gastos_prorrateados.git --skip-assets

echo "==> Registrando en apps.txt..."
grep -q "$APP" "$APPS_TXT" || echo "$APP" >> "$APPS_TXT"

echo "==> Instalando en el sitio $SITE..."
bench --site "$SITE" install-app "$APP"

echo "==> Ejecutando migraciones..."
bench --site "$SITE" migrate

echo ""
echo "✓ $APP instalado correctamente en $SITE"
