#!/usr/bin/env bash
#
# fix_deploy.sh - Corrige el despliegue en producción.
#
# 1. Actualiza el código del backend (git pull).
# 2. Garantiza bcrypt==4.0.1 (compatible con passlib 1.7.4).
# 3. Reinicia el servicio (systemd o docker).
# 4. Verifica/ejecuta la migración automática de pending_balance.
# 5. (Opcional) Prueba el login vía API.
#
# USO:
#   ./fix_deploy.sh                    # usa las variables de abajo
#   BACKEND_DIR=/opt/app ./fix_deploy.sh
#
# Los datos de BD se leen automáticamente de backend/.env (DATABASE_URL).
#
set -euo pipefail

# ============================ CONFIGURACIÓN ============================
BACKEND_DIR="${BACKEND_DIR:-/opt/school_pos/backend}"   # Ruta del backend en el servidor
SERVICE_NAME="${SERVICE_NAME:-}"                        # Ej: school-pos (systemd) o nombre del contenedor
SERVICE_TYPE="${SERVICE_TYPE:-auto}"                     # auto | systemd | docker | none
DOMAIN="${DOMAIN:-}"                                     # Ej: https://pos.colegiobilingue.edu.co (opcional)
LOGIN_EMAIL="${LOGIN_EMAIL:-}"                           # Correo para probar login (opcional)
LOGIN_PASS="${LOGIN_PASS:-}"                             # Contraseña para probar login (opcional)
# ========================================================================

GREEN="\033[1;32m"; CYAN="\033[1;36m"; YELLOW="\033[1;33m"; RED="\033[1;31m"; NC="\033[0m"
info() { echo -e "${CYAN}[INFO ]${NC} $*"; }
ok()   { echo -e "${GREEN}[ OK  ]${NC} $*"; }
warn() { echo -e "${YELLOW}[WARN ]${NC} $*"; }
err()  { echo -e "${RED}[FAIL ]${NC} $*"; }

cd "$BACKEND_DIR" || { err "No existe $BACKEND_DIR"; exit 1; }

# ------------------------------------------------------------------
info "1/5 Actualizando el código del backend..."
if [ -d .git ]; then
    git pull --ff-only || warn "git pull falló; continúo con los demás pasos."
else
    warn "No es un repositorio git: asegúrate de copiar manualmente backend/main.py y el código nuevo."
fi

# ------------------------------------------------------------------
info "2/5 Verificando bcrypt==4.0.1 (compatibilidad con passlib)..."
PYTHON_BIN=""
for cand in ".venv/bin/python" "venv/bin/python" "python3"; do
    if [ -x "$BACKEND_DIR/$cand" ]; then
        PYTHON_BIN="$BACKEND_DIR/$cand"
        break
    fi
    if [ "$cand" = "python3" ] && command -v python3 >/dev/null; then
        PYTHON_BIN="python3"
        break
    fi
done

if [ -n "$PYTHON_BIN" ]; then
    CURRENT_BCRYPT=$("$PYTHON_BIN" -c "import bcrypt; print(getattr(bcrypt,'__version__','?'))" 2>/dev/null || echo "none")
    info "  bcrypt actual: $CURRENT_BCRYPT"
    if [ "$CURRENT_BCRYPT" != "4.0.1" ]; then
        info "  Instalando bcrypt==4.0.1..."
        "$PYTHON_BIN" -m pip install "bcrypt==4.0.1" || warn "No pude instalar bcrypt; verifícalo manualmente: pip install bcrypt==4.0.1"
    else
        ok "  bcrypt ya está en 4.0.1."
    fi
else
    warn "No encontré intérprete de Python; omite el paso de bcrypt."
fi

# ------------------------------------------------------------------
info "3/5 Reiniciando el servicio..."
restart_service() {
    case "$SERVICE_TYPE" in
        systemd) sudo systemctl restart "$SERVICE_NAME" ;;
        docker)  docker restart "$SERVICE_NAME" ;;
        none)    warn "Reinicia manualmente tu servicio." ;;
        auto)
            if [ -n "$SERVICE_NAME" ] && systemctl list-units --type=service --all 2>/dev/null | grep -q "$SERVICE_NAME"; then
                sudo systemctl restart "$SERVICE_NAME"
            elif [ -n "$SERVICE_NAME" ] && command -v docker >/dev/null; then
                docker restart "$SERVICE_NAME"
            else
                warn "No detecté el servicio. Define SERVICE_NAME / SERVICE_TYPE o reinicia manualmente."
            fi
            ;;
    esac
}
restart_service

# ------------------------------------------------------------------
info "4/5 Esperando arranque y verificando migración..."
sleep 5

# Leer credenciales de BD desde backend/.env
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

if get_db_creds && command -v mysql >/dev/null; then
    count=$(mysql -u"$DB_USER" -p"$DB_PASS" "$DB_NAME" -N -e \
        "SELECT COUNT(*) FROM information_schema.columns WHERE table_name IN ('students','users') AND column_name='pending_balance';" 2>/dev/null || echo "0")
    if [ "$count" = "2" ]; then
        ok "Columnas pending_balance presentes."
    else
        info "  Ejecutando migración manual (respaldo si el auto-migrador no actuó)..."
        mysql -u"$DB_USER" -p"$DB_PASS" "$DB_NAME" -e \
            "ALTER TABLE students ADD COLUMN pending_balance FLOAT NOT NULL DEFAULT 0; ALTER TABLE users ADD COLUMN pending_balance FLOAT NOT NULL DEFAULT 0;" \
            && ok "Migración aplicada." \
            || warn "Revisa manualmente con: mysql -u<usuario> -p <basedatos>"
    fi
else
    warn "No pude leer DATABASE_URL o no hay cliente mysql. Verifica en logs si apareció [MIGRACION][MANUAL]."
fi

# ------------------------------------------------------------------
info "5/5 Verificación final..."
if [ -n "$DOMAIN" ] && [ -n "$LOGIN_EMAIL" ]; then
    RESP=$(curl -s -o /tmp/login_check.json -w "%{http_code}" \
        -X POST "$DOMAIN/api/v1/auth/login/access-token" \
        -H "Content-Type: application/x-www-form-urlencoded" \
        --data-urlencode "username=$LOGIN_EMAIL" \
        --data-urlencode "password=$LOGIN_PASS" 2>/dev/null || echo "000")
    if [ "$RESP" = "200" ]; then
        ok "El login responde OK (200)."
    else
        warn "Login devolvió HTTP $RESP. Revisa los logs del backend."
    fi
else
    warn "Define DOMAIN y LOGIN_EMAIL en el script para probar el login automáticamente."
fi

echo ""
ok "Proceso terminado. Si todo salió bien, ya puedes entrar. Si algo falla, revisa los logs con:"
echo "  journalctl -u ${SERVICE_NAME:-<servicio>} --since \"10 minutes ago\" | tail -100   (systemd)"
echo "  docker logs --tail 100 ${SERVICE_NAME:-<contenedor>}                                  (docker)"