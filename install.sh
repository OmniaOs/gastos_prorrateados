#!/bin/bash
# Uso: bash install.sh <nombre-del-sitio>
# Ejemplo: bash install.sh workaholic.omniaos.ai

set -e
SITE=${1:?"Uso: bash install.sh <nombre-del-sitio>"}
APP="gastos_prorrateados"
BENCH_DIR="/home/frappe/frappe-bench"
APPS_TXT="$BENCH_DIR/sites/apps.txt"
ENV_PY="$BENCH_DIR/env/bin/python"

echo "==> Limpiando instalaciones anteriores..."
# Eliminar app directories previos
rm -rf "$BENCH_DIR/apps/$APP" 2>/dev/null || true
rm -rf "$BENCH_DIR/apps/erpnext-$APP" 2>/dev/null || true

# Eliminar editable installs huérfanos del virtualenv
find "$BENCH_DIR/env/lib" \
  -name "*gastos*" -o -name "*erpnext-gastos*" 2>/dev/null \
  | xargs rm -f 2>/dev/null || true

# Desinstalar si quedó registrado
"$BENCH_DIR/env/bin/pip" uninstall -y "$APP" 2>/dev/null || true

# Limpiar apps.txt de entradas previas y reconstruir solo con base
grep -vE "gastos|erpnext-gastos" "$APPS_TXT" > /tmp/apps_clean.txt 2>/dev/null || true
mv /tmp/apps_clean.txt "$APPS_TXT"

echo "==> Obteniendo $APP desde GitHub..."
cd "$BENCH_DIR"
bench get-app "https://github.com/OmniaOs/$APP.git" --skip-assets

echo "==> Registrando en apps.txt..."
grep -qxF "$APP" "$APPS_TXT" || echo "$APP" >> "$APPS_TXT"

echo "==> Instalando en el sitio $SITE..."
bench --site "$SITE" install-app "$APP"

echo "==> Ejecutando migraciones..."
bench --site "$SITE" migrate

echo ""
echo "✓ $APP instalado correctamente en $SITE"
