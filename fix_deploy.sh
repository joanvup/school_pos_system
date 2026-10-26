#!/usr/bin/env bash
#
# fix_deploy.sh - Despliegue seguro del backend en producción.
#
# 1. Respalda la base de datos (y uploads) antes de tocar nada.
# 2. Actualiza el código (git pull) desde un árbol limpio.
# 3. Garantiza bcrypt==4.0.1 (compatible con passlib 1.7.4).
# 4. Aplica migraciones Alembic y detecta desviaciones con `alembic check`.
# 5. Ejecuta la suite de pruebas.
# 6. Reinicia el servicio.
# 7. Verifica el health check real del backend (no el index de Nginx).
# 8. (Opcional) Prueba el login sin filtrar tokens ni contraseñas.
#
# USO:
#   ./fix_deploy.sh                             # autodetecta todo
#   SERVICE_NAME=mi-servicio ./fix_deploy.sh    # si no se detecta bien
#   BACKEND_DIR=/ruta/app/backend SERVICE_NAME=mi-servicio ./fix_deploy.sh
#
# VARIABLES OPCIONALES:
#   BACKUP_DIR=$HOME/backups/deploy   destino de los respaldos (vacío = omite)
#   HEALTH_URL=http://127.0.0.1:8000/health   health real del backend
#   SKIP_TESTS=1      omite pytest (no recomendado)
#   ALLOW_DRIFT=1     tolera diferencias de `alembic check`
#   AUTO_ROLLBACK=1   revierte el código al commit anterior si el health falla
#   ONLY_BACKUP=1     solo respalda BD/uploads y sale (útil antes de mantenimiento)
#   DOMAIN=https://pos.colegiobilingue.edu.co   para probar vía Nginx y login
#   LOGIN_EMAIL=... LOGIN_PASS=...   prueba de login (no se imprime la respuesta)
#
# Los datos de BD se leen del .env del backend y se escriben en un archivo
# temporal con permisos 600; la contraseña nunca aparece en la línea de comandos.
set -euo pipefail

# ============================ CONFIGURACIÓN ============================
BACKEND_DIR="${BACKEND_DIR:-/var/www/school_pos/backend}"
SERVICE_NAME="${SERVICE_NAME:-school_pos_backend}"
SERVICE_TYPE="${SERVICE_TYPE:-auto}"
DOMAIN="${DOMAIN:-}"
LOGIN_EMAIL="${LOGIN_EMAIL:-}"
LOGIN_PASS="${LOGIN_PASS:-}"
BACKUP_DIR="${BACKUP_DIR:-$HOME/backups/deploy}"
HEALTH_URL="${HEALTH_URL:-http://127.0.0.1:8000/health}"
SKIP_TESTS="${SKIP_TESTS:-0}"
ALLOW_DRIFT="${ALLOW_DRIFT:-0}"
AUTO_ROLLBACK="${AUTO_ROLLBACK:-0}"
# ========================================================================

GREEN="\033[1;32m"; CYAN="\033[1;36m"; YELLOW="\033[1;33m"; RED="\033[1;31m"; NC="\033[0m"
info() { echo -e "${CYAN}[INFO ]${NC} $*"; }
ok()   { echo -e "${GREEN}[ OK  ]${NC} $*"; }
warn() { echo -e "${YELLOW}[WARN ]${NC} $*"; }
err()  { echo -e "${RED}[FAIL ]${NC} $*"; }

has() { command -v "$1" >/dev/null 2>&1; }

TMP_DIR="$(mktemp -d)"
chmod 700 "$TMP_DIR"
cleanup() { rm -rf "$TMP_DIR"; }
trap cleanup EXIT

candidate_units() {
    systemctl list-unit-files --type=service --no-legend 2>/dev/null \
        | awk '{print $1}' | sed 's/\.service$//' \
        | grep -iE '\b(school|pos|almuerzo|backend|api|fastapi|uvicorn|gunicorn|lector)\b' \
        | grep -viE '\b(postgres|mysql|mariadb|redis|postfix|nginx|apache2?)\b' \
        || true
}

is_app_service() {
    [ -n "$1" ] || return 1
    local ex wd
    ex=$(systemctl show -p ExecStart --value "$1" 2>/dev/null || true)
    if echo "$ex" | grep -qiE 'uvicorn|gunicorn|python'; then
        return 0
    fi
    wd=$(systemctl show -p WorkingDirectory --value "$1" 2>/dev/null || true)
    if [ -z "$wd" ] && has systemctl; then
        wd=$(systemctl cat --no-pager "$1" 2>/dev/null \
            | sed -n 's/^[[:space:]]*WorkingDirectory=[[:space:]]*//p' | head -n1)
    fi
    [ -n "$wd" ] && { [ -f "$wd/backend/main.py" ] || [ -f "$wd/.env" ]; }
}

restart_service() {
    case "$SERVICE_TYPE" in
        systemd) sudo systemctl restart "$SERVICE_NAME" ;;
        docker)  docker restart "$SERVICE_NAME" ;;
        none)    warn "Reinicia manualmente tu servicio." ;;
        auto)
            if [ -n "$SERVICE_NAME" ]; then
                if has systemctl; then
                    sudo systemctl restart "$SERVICE_NAME"
                elif has docker; then
                    docker restart "$SERVICE_NAME"
                else
                    warn "Reinicia tú: sudo systemctl restart $SERVICE_NAME"
                fi
            else
                warn "Sin SERVICE_NAME; reinicia manualmente tu servicio."
            fi
            ;;
    esac
}

check_health() {
    local code
    code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "$HEALTH_URL" 2>/dev/null || echo "000")
    [ "$code" = "200" ] && return 0
    if [ -n "$DOMAIN" ]; then
        # Nginx responde 200 en /health con el index de la SPA; usar una ruta API.
        code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 8 \
            "$DOMAIN/api/v1/settings/public" 2>/dev/null || echo "000")
        [ "$code" = "200" ] && return 0
    fi
    return 1
}

wait_for_health() {
    local i
    for i in $(seq 1 10); do
        if check_health; then
            return 0
        fi
        sleep 2
    done
    return 1
}

rollback() {
    if [ "$AUTO_ROLLBACK" != "1" ]; then
        err "Health check falló. Rollback automático desactivado (AUTO_ROLLBACK=1 para activarlo)."
        [ -n "$PREV_HEAD" ] && err "Manual: git -C $REPO_ROOT reset --hard $PREV_HEAD && sudo systemctl restart ${SERVICE_NAME:-<servicio>}"
        return 1
    fi
    warn "Health check falló; revirtiendo el código a ${PREV_HEAD:-<desconocido>}..."
    if [ -z "$PREV_HEAD" ] || [ ! -d "$REPO_ROOT/.git" ]; then
        err "No hay commit anterior para revertir."
        return 1
    fi
    if [ -n "$(git -C "$REPO_ROOT" status --porcelain)" ]; then
        err "Hay cambios locales sin commitear; no revierto automáticamente."
        return 1
    fi
    git -C "$REPO_ROOT" reset --hard "$PREV_HEAD"
    restart_service
    if wait_for_health; then
        ok "Rollback completado en $PREV_HEAD."
        warn "Si el deploy aplicó migraciones nuevas, evalúa 'alembic downgrade' antes de confiar en el esquema."
        return 0
    fi
    err "El servicio sigue sin responder tras el rollback."
    return 1
}

db_backup() {
    local stamp dump file
    [ -n "$BACKUP_DIR" ] || { warn "BACKUP_DIR vacío: se omite el respaldo."; return 0; }
    if [ ! -f "$BACKEND_DIR/.env" ]; then
        err "Sin $BACKEND_DIR/.env no se puede respaldar la base."
        return 1
    fi
    has mysqldump || { err "mysqldump no está instalado."; return 1; }

    stamp=$(date +%Y%m%d-%H%M%S)
    mkdir -p "$BACKUP_DIR"
    chmod 750 "$BACKUP_DIR"

    DB_NAME=$("$PYTHON_BIN" - "$BACKEND_DIR/.env" "$TMP_DIR/my.cnf" <<'PY'
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse

env_path, out_path = Path(sys.argv[1]), Path(sys.argv[2])
url = ""
for line in env_path.read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if line.startswith("DATABASE_URL="):
        url = line.split("=", 1)[1].strip().strip('"').strip("'")
        break
if not url:
    raise SystemExit("DATABASE_URL no encontrada")

parsed = urlparse(url)
if not parsed.scheme.startswith("mysql"):
    raise SystemExit(f"motor no soportado para mysqldump: {parsed.scheme}")

def esc(value):
    return (value or "").replace("\\", "\\\\").replace('"', '\\"')

out_path.write_text(
    "[client]\n"
    f'user="{esc(unquote(parsed.username or ""))}"\n'
    f'password="{esc(unquote(parsed.password or ""))}"\n'
    f'host="{esc(parsed.hostname or "localhost")}"\n'
    f"port={parsed.port or 3306}\n",
    encoding="utf-8",
)
out_path.chmod(0o600)
print((parsed.path or "/").lstrip("/"))
PY
)
    if [ -z "$DB_NAME" ]; then
        err "No pude obtener el nombre de la base desde DATABASE_URL."
        return 1
    fi

    dump="$BACKUP_DIR/school_pos_${stamp}.sql.gz"
    # HOME aislado: evita que un ~/.my.cnf con credenciales viejas pise las del archivo temporal.
    if ! HOME="$TMP_DIR" MYSQL_HOME="$TMP_DIR" mysqldump \
        --defaults-extra-file="$TMP_DIR/my.cnf" --no-tablespaces \
        --single-transaction --quick --routines --triggers --no-create-db \
        "$DB_NAME" | gzip -9 > "$dump"; then
        err "El respaldo de la base falló."
        rm -f "$dump"
        return 1
    fi
    if ! gzip -t "$dump" 2>/dev/null || [ ! -s "$dump" ]; then
        err "El respaldo quedó vacío o corrupto: $dump"
        return 1
    fi
    chmod 600 "$dump"
    ok "Base respaldada en $dump ($(du -h "$dump" | cut -f1))."

    if [ -d "$BACKEND_DIR/uploads" ]; then
        file="$BACKUP_DIR/school_pos_uploads_${stamp}.tar.gz"
        if tar czf "$file" -C "$BACKEND_DIR" uploads && gzip -t "$file"; then
            chmod 600 "$file"
            ok "Uploads respaldados en $file."
        else
            err "El respaldo de uploads falló."
            return 1
        fi
    fi
}

# ------------------------------------------------------------------
# 0/8 Autodetección de servicio (systemd) y ruta del backend
# ------------------------------------------------------------------
if [ -z "$SERVICE_NAME" ] && has systemctl; then
    CAND=$(candidate_units | tr '\n' ' ')
    [ -n "$CAND" ] && info "Candidatos systemd: $CAND"
    for s in $(candidate_units); do
        if is_app_service "$s"; then
            SERVICE_NAME="$s"
            break
        fi
    done
    if [ -z "$SERVICE_NAME" ]; then
        SERVICE_NAME=$(candidate_units | head -n1)
        [ -n "$SERVICE_NAME" ] && warn "Uso '$SERVICE_NAME' sin verificar; revisa los candidatos de arriba."
    fi
    [ -n "$SERVICE_NAME" ] && info "Servicio: $SERVICE_NAME"
fi

if [ -z "$BACKEND_DIR" ] && [ -n "$SERVICE_NAME" ] && has systemctl; then
    wd=$(systemctl show -p WorkingDirectory --value "$SERVICE_NAME" 2>/dev/null || true)
    if [ -z "$wd" ]; then
        wd=$(systemctl cat --no-pager "$SERVICE_NAME" 2>/dev/null \
            | sed -n 's/^[[:space:]]*WorkingDirectory=[[:space:]]*//p' | head -n1)
    fi
    if [ -n "$wd" ] && [ -d "$wd" ]; then
        BACKEND_DIR="$wd"
        [ -f "$BACKEND_DIR/backend/main.py" ] && BACKEND_DIR="$BACKEND_DIR/backend"
        info "Ruta del backend: $BACKEND_DIR"
    fi
fi

BACKEND_DIR="${BACKEND_DIR:-/var/www/school_pos/backend}"

if [ ! -d "$BACKEND_DIR" ]; then
    err "No existe el directorio del backend: $BACKEND_DIR"
    err "Usa: BACKEND_DIR=/ruta/al/backend ./fix_deploy.sh"
    exit 1
fi
cd "$BACKEND_DIR"

PYTHON_BIN=""
for cand in ".venv/bin/python" "venv/bin/python" "../venv/bin/python" "../.venv/bin/python"; do
    if [ -x "$BACKEND_DIR/$cand" ]; then
        PYTHON_BIN="$BACKEND_DIR/$cand"
        break
    fi
done
if [ -z "$PYTHON_BIN" ] && has python3; then
    PYTHON_BIN="python3"
fi
[ -n "$PYTHON_BIN" ] || { err "No encontré intérprete de Python."; exit 1; }

REPO_ROOT="$BACKEND_DIR"
if [ ! -d "$REPO_ROOT/.git" ] && [ -d "$(dirname "$BACKEND_DIR")/.git" ]; then
    REPO_ROOT="$(dirname "$BACKEND_DIR")"
fi

PREV_HEAD=""
if [ -d "$REPO_ROOT/.git" ]; then
    PREV_HEAD=$(git -C "$REPO_ROOT" rev-parse HEAD 2>/dev/null || true)
    if [ -n "$(git -C "$REPO_ROOT" status --porcelain)" ]; then
        err "El árbol de $REPO_ROOT tiene cambios sin commitear; cancela el despliegue."
        exit 1
    fi
fi

# ------------------------------------------------------------------
info "1/8 Respaldando base de datos y uploads..."
db_backup || exit 1
if [ "${ONLY_BACKUP:-0}" = "1" ]; then
    ok "ONLY_BACKUP=1: respaldo listo, no se toca el código ni el servicio."
    exit 0
fi

# ------------------------------------------------------------------
info "2/8 Actualizando el código (git pull)..."
if [ -d "$REPO_ROOT/.git" ]; then
    git -C "$REPO_ROOT" pull --ff-only && ok "Código actualizado." \
        || { err "git pull falló; se cancela el despliegue."; exit 1; }
else
    warn "No hay repo git en $REPO_ROOT; continúo con los archivos actuales."
fi

# ------------------------------------------------------------------
info "3/8 Verificando bcrypt==4.0.1 (compatibilidad con passlib)..."
CURRENT_BCRYPT=$("$PYTHON_BIN" -c "import bcrypt; print(getattr(bcrypt,'__version__','?'))" 2>/dev/null || echo "none")
info "  bcrypt actual: $CURRENT_BCRYPT  ($PYTHON_BIN)"
if [ "$CURRENT_BCRYPT" != "4.0.1" ]; then
    "$PYTHON_BIN" -m pip install "bcrypt==4.0.1" || { err "No pude instalar bcrypt==4.0.1."; exit 1; }
else
    ok "  bcrypt correcto."
fi

# ------------------------------------------------------------------
info "4/8 Aplicando migraciones de base de datos..."
if "$PYTHON_BIN" -c "import alembic" >/dev/null 2>&1; then
    "$PYTHON_BIN" -m alembic upgrade head \
        || { err "Falló 'alembic upgrade head'. NO se reinicia el servicio."; exit 1; }
    ok "  Esquema al día."
    if "$PYTHON_BIN" -m alembic check >/dev/null 2>&1; then
        ok "  Sin diferencias entre modelos y migraciones."
    elif [ "$ALLOW_DRIFT" = "1" ]; then
        warn "  'alembic check' reporta diferencias (ALLOW_DRIFT=1)."
    else
        err "  'alembic check' reporta diferencias entre modelos y esquema. Aborta."
        exit 1
    fi
else
    err "  No encontré alembic con $PYTHON_BIN."
    err "  Instala dependencias: $PYTHON_BIN -m pip install -r requirements.txt"
    exit 1
fi

# ------------------------------------------------------------------
info "5/8 Ejecutando pruebas..."
if [ "$SKIP_TESTS" = "1" ]; then
    warn "  SKIP_TESTS=1: se omite pytest."
elif "$PYTHON_BIN" -c "import pytest" >/dev/null 2>&1; then
    if "$PYTHON_BIN" -m pytest -q; then
        ok "  Pruebas en verde."
    else
        err "  Las pruebas fallaron. NO se reinicia el servicio."
        exit 1
    fi
else
    warn "  pytest no está instalado; se omite."
fi

# ------------------------------------------------------------------
info "6/8 Reiniciando el servicio (${SERVICE_NAME:-auto})..."
restart_service
sleep 4
if [ -n "$SERVICE_NAME" ] && has systemctl; then
    STATE=$(systemctl is-active "$SERVICE_NAME" 2>/dev/null || true)
    [ "$STATE" = "active" ] && ok "Servicio activo." || warn "Estado: ${STATE:-desconocido}."
fi

# ------------------------------------------------------------------
info "7/8 Verificando el health check del backend..."
if wait_for_health; then
    ok "Backend responde en $HEALTH_URL."
else
    rollback || true
    exit 1
fi

if [ -n "$SERVICE_NAME" ] && has journalctl; then
    journalctl -u "$SERVICE_NAME" --since "2 minutes ago" --no-pager 2>/dev/null | tail -n 20 || true
fi

# ------------------------------------------------------------------
info "8/8 Verificación opcional del login..."
if [ -n "$DOMAIN" ] && [ -n "$LOGIN_EMAIL" ] && [ -n "$LOGIN_PASS" ]; then
    "$PYTHON_BIN" - "$TMP_DIR/login.form" "$LOGIN_EMAIL" "$LOGIN_PASS" <<'PY'
import sys
from pathlib import Path
from urllib.parse import urlencode

Path(sys.argv[1]).write_text(
    urlencode({"username": sys.argv[2], "password": sys.argv[3]}),
    encoding="utf-8",
)
PY
    chmod 600 "$TMP_DIR/login.form"
    RESP=$(curl -s -o "$TMP_DIR/login.json" -w "%{http_code}" --max-time 10 \
        -X POST "$DOMAIN/api/v1/auth/login/access-token" \
        -H "Content-Type: application/x-www-form-urlencoded" \
        --data @"$TMP_DIR/login.form" 2>/dev/null || echo "000")
    if [ "$RESP" = "200" ]; then
        ok "El login responde 200."
    else
        # Solo el detalle del error: la respuesta puede contener tokens.
        "$PYTHON_BIN" - "$TMP_DIR/login.json" <<'PY' || true
import json, sys
from pathlib import Path
try:
    data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    detail = data.get("detail") if isinstance(data, dict) else None
    if detail:
        print(f"  detalle: {detail}")
except Exception:
    pass
PY
        warn "Login devolvió HTTP $RESP."
    fi
    rm -f "$TMP_DIR/login.json" "$TMP_DIR/login.form"
else
    warn "Define DOMAIN, LOGIN_EMAIL y LOGIN_PASS para probar el login."
fi

echo ""
ok "Proceso terminado. Revisa arriba si hubo [WARN]/[FAIL]."
echo "  Logs: journalctl -u ${SERVICE_NAME:-<servicio>} --since \"10 minutes ago\" | tail -100"
