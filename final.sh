#!/usr/bin/env bash
# Partido final (o ensayo) en un solo comando. Se corre desde Git Bash en la notebook, en la carpeta del repo.
#
#   ./final.sh http://DIRECCION-QUE-DA-LA-ORGANIZACION   partido final: el motor contra el simulador del jurado
#   ./final.sh --ensayo [acelerar]                         ensayo: levanta el simulador de práctica acá (por defecto x10)
#
# El juez firma desde el celular en https://desafio-futbol-iota.vercel.app/juez/ con el PIN (JUEZ_PIN de .env.local).
# La notebook NO se puede suspender mientras corre el partido.
set -euo pipefail
cd "$(dirname "$0")"

WEB="https://desafio-futbol-iota.vercel.app"
PY=python
for candidato in ../.venv/Scripts/python.exe .venv/Scripts/python.exe .venv/bin/python; do
  [ -x "$candidato" ] && PY="$candidato" && break
done
export PYTHONUTF8=1

if [ ! -f .env.local ]; then
  echo "Falta .env.local. Bajalo con: vercel env pull .env.local   (proyecto desafio-futbol)" >&2
  exit 2
fi
set -a; . ./.env.local; set +a
if [ -z "${DATABASE_URL:-}" ]; then
  echo "En .env.local no está DATABASE_URL (la base Neon)." >&2
  exit 2
fi

uso() { sed -n '4,5p' "$0" | sed 's/^# *//'; exit 2; }
[ $# -ge 1 ] || uso

SIM_PID=""
terminar() { [ -n "$SIM_PID" ] && kill "$SIM_PID" 2>/dev/null || true; }
trap terminar EXIT

if [ "$1" = "--ensayo" ]; then
  MODO=ensayo
  ACELERAR="${2:-10}"
  PUERTO="${ENSAYO_PUERTO:-8080}"
  SIM="http://localhost:$PUERTO"
  mkdir -p salida
  "$PY" simulador/servidor.py --acelerar "$ACELERAR" --puerto "$PUERTO" --log salida/registro.jsonl > salida/ensayo-simulador.log 2>&1 &
  SIM_PID=$!
  sleep 3
  EXTRA=()
  # Solo para probar el ensayo sin nadie firmando. En el final nunca se usa.
  [ "${ENSAYO_JUEZ_AUTOMATICO:-0}" = 1 ] && EXTRA=(--juez-automatico)
else
  MODO=final
  SIM="${1%/}"
  EXTRA=(--exportar-entrega)
fi

if ! curl -sf --max-time 10 "$SIM/estado" > /dev/null; then
  echo "No llego al simulador en $SIM/estado. Revisá la dirección y que estés en la red del evento." >&2
  exit 1
fi

echo "=============================================================="
echo " Modo:              $MODO"
echo " Simulador:         $SIM"
echo " Pantalla del juez: $WEB/juez/      (PIN: JUEZ_PIN en .env.local)"
echo " Registro público:  $WEB/juez/publico.html"
echo " NO suspender la notebook hasta que el motor diga 'Partido cerrado'."
echo "=============================================================="

"$PY" -m plataforma.main --sim "$SIM" --base --sin-web "${EXTRA[@]}"

if [ "$MODO" = ensayo ]; then
  sleep 2
  echo
  echo "=== Verificador oficial sobre el ensayo ==="
  "$PY" evaluacion/verificar.py --log salida/registro.jsonl | tee salida/ensayo-verificador.txt
else
  echo
  echo "Partido final cerrado. Ahora, ANTES del cierre de la entrega:"
  echo "  git add entrega && git commit -m 'Entrega: expediente y auditoría del partido final' && git push"
fi
