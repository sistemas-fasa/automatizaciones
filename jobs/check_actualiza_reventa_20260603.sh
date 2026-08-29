#!/usr/bin/env bash
set -u

echo "--- latest actualiza log ---"
dir="/home/ferreteria/automatizaciones/logs/linux/actualiza_lista_reventa"
latest="$(find "$dir" -maxdepth 1 -type f -name 'actualiza_lista_reventa-*.log' -printf '%T@ %p\n' 2>/dev/null | sort -nr | head -1 | cut -d' ' -f2-)"
echo "$latest"
if [ -n "$latest" ]; then
  tail -120 "$latest"
fi

echo "--- env keys utiles ---"
grep -nE '^(DB|MYSQL|REVENTA|REV|HOST|DATABASE|USER|PORT|PASSWORD)' /var/www/html/utiles/.env | sed -E 's/(PASSWORD|PASS|CLAVE)=.*/\1=***MASKED***/I' || true

echo "--- ModeloBase db config refs ---"
grep -nE 'ModeloBaseReventa|database|host|port|user|password|DB_|REV|REVENTA|os.getenv|config' /var/www/html/utiles/modelos/ModeloBase.py | sed -E 's/(password[^=]*=).*/\1 ***MASKED***/I' || true

echo "--- Actualiza db refs ---"
grep -nE 'ModeloBaseReventa|ModeloBase|select|save|api_|Stock|Articulo|Oferta|FormaPago|Localidad' /var/www/html/utiles/ActualizaListaReventa.py | head -80 || true
