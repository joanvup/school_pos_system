#!/usr/bin/env bash
#
# fix_deploy.sh - Corrige el despliegue en producción.
#
# 1. Detecta el servicio systemd y la ruta real del backend.
# 2. Actualiza el código (git pull).
# 3. Garantiza bcrypt==4.0.1 (compatible con passlib 1.7.4).
# 4. Reinicia el servicio.
# 5. Verifica/ejecuta la migración automática de pending_balance.
# 6. (Opcional) Prueba el login vía API.
#
# USO:
#   ./fix_deploy.sh                             # autodetecta todo
#   SERVICE_NAME=mi-servicio ./fix_deploy.sh    # si no se detecta bien
#   BACKEND_DIR=/ruta/app/backend SERVICE_NAME=mi-servicio ./fix_deploy.sh
#
# Los datos de BD se leen automáticamente del .env del backend (DATABASE_URL).
set -euo pipefail

# ============================ CONFIGURACIÓN ============================
BACKEND_DIR="${BACKEND_DIR:-}"                        # Ruta del backend (vacío = autodetecta)
SERVICE_NAME="${SERVICE_NAME:-}"                      # Nombre del unit systemd (vacío = autodetecta)
SERVICE_TYPE="${SERVICE_TYPE:-auto}"                  # systemd | docker | none | auto
DOMAIN="${DOMAIN:-}"                                  # Ej: https://pos.colegiobilingue.edu.co (opcional)
LOGIN_EMAIL="${LOGIN_EMAIL:-}"                        # Correo para probar login (opcional)
LOGIN_PASS="${LOGIN_PASS:-}"                          # Contraseña para probar login (opcional)
# ========================================================================

GREEN="\033[1;32m"; CYAN="\033[1;36m"; YELLOW="\033[1;33m"; RED="\033[1;31m"; NC="\033[0m"
info() { echo -e "${CYAN}[INFO ]${NC} $*"; }
ok()   { echo -e "${GREEN}[ OK  ]${NC} $*"; }
warn() { echo -e "${YELLOW}[WARN ]${NC} $*"; }
err()  { echo -e "${RED}[FAIL ]${NC} $*"; }

has() { command -v "$1" >/dev/null 2>&1; }

# ------------------------------------------------------------------
# 0/6 Autodetección de servicio (systemd) y ruta del backend
# ------------------------------------------------------------------
if [ -z "$SERVICE_NAME" ] && has systemctl; then
    SERVICE_NAME=$(systemctl list-unit-files --type=service --no-legend 2>/dev/null \
        | awk '{print $1}' \
        | grep -iE "school|pos|almuerzo|backend|api|fastapi|uvicorn|gunicorn" \
        | head -n1 | sed 's/\.service$//')
    [ -n "$SERVICE_NAME" ] && info "Servicio detectado: $SERVICE_NAME"
fi

if [ -z "$BACKEND_DIR" ] && [ -n "$SERVICE_NAME" ] && has systemctl; then
    wd=$(systemctl show -p WorkingDirectory --value "$SERVICE_NAME" 2>/dev/null || true)
    if [ -z "$wd" ]; then
        wd=$(systemctl cat --no-pager "$SERVICE_NAME" 2>/dev/null \
            | sed -n 's/^[[:space:]]*WorkingDirectory?=[[:space:]]*//p' | head -n1)
    fi
    if [ -n "$wd" ] && [ -d "$wd" ]; then
        BACKEND_DIR="$wd"
        [ -f "$BACKEND_DIR/backend/main.py" ] && BACKEND_DIR="$BACKEND_DIR/backend"
        info "Ruta detectada desde el servicio: $BACKEND_DIR"
    fi
fi

BACKEND_DIR="${BACKEND_DIR:-/opt/school_pos/backend}"

if [ ! -d "$BACKEND_DIR" ]; then
    err "No existe el directorio del backend: $BACKEND_DIR"
    err "Usa: BACKEND_DIR=/ruta/al/backend ./fix_deploy.sh"
    exit 1
fi
if [ ! -f "$BACKEND_DIR/.env" ]; then
    warn "No encontré $BACKEND_DIR/.env (los pasos de BD se omitirán)."
fi
cd "$BACKEND_DIR"

# ------------------------------------------------------------------
info "1/6 Actualizando el código (git pull)..."
if [ -d ".git" ]; then
    git pull --ff-only && ok "Código actualizado." || warn "git pull falló; continúo con los demás pasos."
else
    warn "No es un repositorio git en esta ruta. ¿El git repo está en otro lado?"
    warn "  Verifica con: git -C <otra-ruta> status"
    warn "  y copia/actualiza los archivos en $BACKEND_DIR"
fi

# ------------------------------------------------------------------
info "2/6 Verificando bcrypt==4.0.1 (compatibilidad con passlib)..."
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

if [ -n "$PYTHON_BIN" ]; then
    CURRENT_BCRYPT=$("$PYTHON_BIN" -c "import bcrypt; print(getattr(bcrypt,'__version__','?'))" 2>/dev/null || echo "none")
    info "  bcrypt actual: $CURRENT_BCRYPT  ($PYTHON_BIN)"
    if [ "$CURRENT_BCRYPT" != "4.0.1" ]; then
        info "  Instalando bcrypt==4.0.1..."
        "$PYTHON_BIN" -m pip install "bcrypt==4.0.1" || warn "No pude instalarlo; hazlo manual: pip install bcrypt==4.0.1"
    else
        ok "  bcrypt correcto."
    fi
else
    warn "No encontré intérprete de Python; omite el paso de bcrypt."
fi

# ------------------------------------------------------------------
info "3/6 Reiniciando el servicio ($SERVICE_NAME)..."
restart_service() {
    case "$SERVICE_TYPE" in
        systemd) sudo systemctl restart "$SERVICE_NAME" ;;
        docker)  docker restart "$SERVICE_NAME" ;;
        none)    warn "Reinicia manualmente tu servicio." ;;
        auto)
            if [ -n "$SERVICE_NAME" ]; then
                if has systemctl && systemctl list-units --type=service --all 2>/dev/null | grep -q "$SERVICE_NAME"; then
                    sudo systemctl restart "$SERVICE_NAME"
                elif has docker; then
                    docker restart "$SERVICE_NAME"
                else
                    warn "No pude reiniciar; hazlo tú: sudo systemctl restart $SERVICE_NAME"
                fi
            else
                warn "Sin SERVICE_NAME; reinicia manualmente tu servicio."
            fi
            ;;
    esac
}
restart_service
sleep 4
if [ -n "$SERVICE_NAME" ] && has systemctl; then
    STATE=$(systemctl is-active "$SERVICE_NAME" 2>/dev/null || true)
    [ "$STATE" = "active" ] && ok "Servicio activo." || warn "Estado: ${STATE:-desconocido}."
fi

# ------------------------------------------------------------------
info "4/6 Verificando migración de pending_balance..."
get_db_creds() {
    if [ ! -f "$BACKEND_DIR/.env" ]; then return 1; fi
    DBURL=$(grep -E '^DATABASE_URL=' "$BACKEND_DIR/.env" | head -n1 | cut -d= -f2- | tr -d '"')
    [ -z "$DBURL" ] && return 1
    TMP="${DBURL#*://}"                              # quita mysql+pymysql://
    DB_USER="${TMP%%:*}"
    TMP="${TMP#*:}"
    DB_PASS="${TMP%%@*}"
    TMP="${TMP#*@}"
    DB_NAME="${TMP##*/}"
    return 0
}

MIGROK="no"
if get_db_creds && has mysql; then
    count=$(mysql -u"$DB_USER" -p"$DB_PASS" "$DB_NAME" -N -e \
        "SELECT COUNT(*) FROM information_schema.columns WHERE table_name IN ('students','users') AND column_name='pending_balance';" 2>/dev/null || echo "0")
    if [ "$count" = "2" ]; then
        ok "  Columnas pending_balance presentes en $DB_NAME."
        MIGROK="si"
    else
        info "  Ejecutando ALTER (respaldo del auto-migrador del backend)..."
        mysql -u"$DB_USER" -p"$DB_PASS" "$DB_NAME" -e \
            "ALTER TABLE students ADD COLUMN pending_balance FLOAT NOT NULL DEFAULT 0; ALTER TABLE users ADD COLUMN pending_balance FLOAT NOT NULL DEFAULT 0;" \
            && { ok "  Migración aplicada."; MIGROK="si"; } \
            || warn "  Falló el ALTER (revisa permisos del usuario de BD)."
    fi
else
    warn "  No pude leer DATABASE_URL o no hay cliente mysql."
fi

if [ "$MIGROK" != "si" ]; then
    warn "  IMPORTANTE: revisa los logs del backend, debe aparecer:"
    warn "    [MIGRACION] Ejecutando: ALTER TABLE ..."
    warn "  o ejecuta manual en la BD:"
    warn "    ALTER TABLE students ADD COLUMN pending_balance FLOAT NOT NULL DEFAULT 0;"
    warn "    ALTER TABLE users   ADD COLUMN pending_balance FLOAT NOT NULL DEFAULT 0;"
fi

# ------------------------------------------------------------------
info "5/6 Revisando logs del arranque..."
if [ -n "$SERVICE_NAME" ] && has journalctl; then
    journalctl -u "$SERVICE_NAME" --since "2 minutes ago" --no-pager 2>/dev/null | tail -n 30 || true
else
    warn "  Sin servicio/journalctl; revisa los logs a mano."
fi

# ------------------------------------------------------------------
info "6/6 Verificación del login..."
if [ -n "$DOMAIN" ] && [ -n "$LOGIN_EMAIL" ]; then
    RESP=$(curl -s -o /tmp/login_check.json -w "%{http_code}" \
        -X POST "$DOMAIN/api/v1/auth/login/access-token" \
        -H "Content-Type: application/x-www-form-urlencoded" \
        --data-urlencode "username=$LOGIN_EMAIL" \
        --data-urlencode "password=$LOGIN_PASS" 2>/dev/null || echo "000")
    if [ "$RESP" = "200" ]; then
        ok "El login responde OK (200)."
    else
        warn "Login devolvió HTTP $RESP. Revisa el JSON en /tmp/login_check.json."
    fi
else
    warn "Define DOMAIN y LOGIN_EMAIL para probar el login automáticamente."
fi

echo ""
ok "Proceso terminado. Revisa arriba si hubo [WARN]/[FAIL]."
echo "  Logs: journalctl -u ${SERVICE_NAME:-<servicio>} --since \"10 minutes ago\" | tail -100"