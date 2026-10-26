# 🥗 School POS System - Gestión de Cafetería Escolar Pro

**School POS** es una plataforma integral de gestión de ventas para cafeterías escolares.
Diseñada para eliminar el uso de efectivo dentro del colegio, permite pagos rápidos mediante **tarjetas RFID/NFC**, **recargas en línea con PayU PSE** y un **control administrativo total** sobre el inventario y las finanzas.

![version](https://img.shields.io/badge/version-2.0.0-blue)
![backend](https://img.shields.io/badge/Backend-FastAPI-green)
![frontend](https://img.shields.io/badge/Frontend-Vue%203-blue)
![payments](https://img.shields.io/badge/Pagos-PayU%20PSE-purple)
![pwa](https://img.shields.io/badge/PWA-Ready-orange)

---

## 🚀 Características Principales

- 💳 **Ecosistema Cashless**
  Pagos con tarjetas inteligentes NFC (Mifare / ISO 14443A) y lectores NFC ACR122U vinculadas a estudiantes y empleados.

- 💰 **Recargas con PayU PSE**
  Pasarela única registrada en el sistema. Las recargas solo se acreditan cuando PayU envía una notificación **firmada**, del merchant correcto y por el monto exacto de la transacción.

- 🖥️ **Terminal de Ventas (POS)**
  Interfaz táctil de alto impacto optimizada para tablets y móviles, con fotos de productos y categorías dinámicas.

- 📦 **Control de Inventario**
  Auditoría mediante Órdenes de Compra (Entradas) y Ajustes de Stock manuales.

- 📥 **Carga Masiva Inteligente**
  Importación de cientos de estudiantes y empleados mediante Excel con lógica de actualización automática (*Upsert*).

- 🎨 **Branding Institucional**
  Nombre, logo y parámetros SMTP configurables desde el panel de administración.

- 📊 **Reportes Avanzados**
  6 módulos de reporte exportables a **Excel** y **PDF**.

---

## 🏗️ Arquitectura de Pagos

Solo existe un proveedor registrado. El contrato `PaymentProvider` se conserva para poder añadir pasarelas en el futuro:

```
payment_providers/
├── base.py          → PaymentProvider (ABC): get_methods / init_recharge / handle_notification
├── registry.py      → register() + get_provider() + get_active_provider()
├── payu_provider.py → PayU PSE (delegado a app/services/payment_service.py)
└── __init__.py      → registra únicamente PayU
```

La tabla `payment_gateway_settings` se siembra solo con PayU. `get_provider("wompi")` y `get_provider("mercadopago")` devuelven `None` y sus endpoints responden `404`.

La lógica sensible vive en [`backend/app/services/payment_service.py`](backend/app/services/payment_service.py):

- La **referencia se genera en el servidor** (`RECH-<128 bits>`); nunca se acepta del cliente.
- La transacción se crea en estado `pending` y se confirma **antes** de llamar a PayU (nunca hay HTTP externo dentro de una transacción de BD).
- El webhook valida `merchant_id`, firma MD5 (comparación en tiempo constante), `currency`, monto y referencia; bloquea **tarjeta → transacción**, abona `tx.amount` exactamente una vez y guarda la notificación cruda en `payment_notifications`.
- Los duplicados responden `200` sin segundo abono.

### 🧭 Endpoints de pago (`/api/v1/payments/*`)

| Método | Endpoint | Descripción |
|---|---|---|
| GET | `/payments/providers` | Lista pasarelas (admin) |
| POST | `/payments/providers/activate` | Activa PayU (única soportada) |
| GET | `/payments/methods` | Métodos de la pasarela activa |
| POST | `/payments/init` | Inicia la recarga; valida propiedad de la tarjeta y límites |
| POST | `/payments/notify/payu` | **Webhook canónico** de PayU |
| GET | `/payments/status/{reference}` | Estado de la recarga (autenticado y con permisos) |

Los endpoints legacy `/recharges/init-payu-pse`, `/recharges/banks` y `/recharges/payu-confirmation` delegan en el mismo servicio. `POST /recharges/simulate-pse` fue **eliminado** (`404`).

> Configure en el dashboard de PayU la URL de confirmación `https://<dominio>/api/v1/payments/notify/payu` y la de respuesta `https://<dominio>/payment-result?reference=<referencia>`. Actualice PayU **antes** de retirar el alias legacy en una release posterior.

---

## 🛠️ Stack Tecnológico

### Backend
- Python 3.10+
- FastAPI
- SQLAlchemy 2.0 (ORM) + MySQL
- Pydantic Settings, Requests, Passlib/Bcrypt, OpenPyXL, ReportLab

### Frontend
- Vue.js 3
- Vite
- Tailwind CSS
- Pinia (Gestión de Estado)
- Vue Router, Axios, PWA (`vite-plugin-pwa`)

### Infraestructura
- Base de Datos: **MySQL 8.0+**
- Servidor: **Ubuntu Linux**
- Web Server: **Nginx**
- ASGI: **Gunicorn / Uvicorn**
- Servicios: **Systemd**

### Seguridad
- Autenticación **JWT**
- Hashing de contraseñas con **Bcrypt 4.0.1**
- Webhooks de pasarelas con validación de firma e **idempotencia** (no se abona 2 veces)

---

## ⚙️ Instalación en Producción (Ubuntu Server)

### 1️⃣ Requisitos Previos

```bash
sudo apt update && sudo apt install python3-pip python3-venv nginx mysql-server git -y
```

### 2️⃣ Base de Datos

```sql
CREATE DATABASE school_pos_db
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;

CREATE USER 'pos_user'@'localhost' IDENTIFIED BY 'TuClaveSegura';
GRANT ALL PRIVILEGES ON school_pos_db.* TO 'pos_user'@'localhost';
```

### 3️⃣ Backend (FastAPI)

```bash
git clone https://github.com/usuario/repo.git /var/www/school_pos
cd /var/www/school_pos
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Configurar `.env` (usa `backend/.env.example` como plantilla):

```bash
# App
ENVIRONMENT="production"
DATABASE_URL="mysql+pymysql://pos_user:TuClaveSegura@localhost/school_pos_db"
SECRET_KEY="una-clave-aleatoria-de-32-caracteres-o-mas"
ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES=30
ALLOWED_ORIGINS="https://TU_DOMINIO"          # nunca "*" en producción
PUBLIC_BASE_URL="https://TU_DOMINIO"
FRONTEND_URL="https://TU_DOMINIO"
APP_TIMEZONE="America/Bogota"

# Sesiones y contraseñas
SETTINGS_ENCRYPTION_KEY="otra-clave-aleatoria-de-32-caracteres-o-mas"
MAX_FAILED_LOGIN_ATTEMPTS=5
LOGIN_LOCKOUT_MINUTES=15
PASSWORD_RESET_EXPIRE_MINUTES=30

# Admin inicial (solo seed; no sobrescribe un admin existente)
ADMIN_EMAIL="admin@tudominio.com"
ADMIN_INITIAL_PASSWORD="ClaveInicial2026"
ADMIN_FORCE_CHANGE=true

# PayU PSE (única pasarela)
PAYU_MERCHANT_ID="..."
PAYU_API_KEY="..."
PAYU_API_LOGIN="..."
PAYU_ACCOUNT_ID="..."
PAYU_IS_TEST=false
PAYU_URL="https://api.payulatam.com/payments-api/4.0/service.cgi"

# Límites
PAYMENT_CURRENCY="COP"
MIN_RECHARGE_AMOUNT=1000
MAX_RECHARGE_AMOUNT=500000
MAX_IMPORT_BYTES=10485760
MAX_UPLOAD_BYTES=2097152
```

> En `ENVIRONMENT=production` la aplicación **no publica** `/docs`, `/redoc` ni OpenAPI, exige `ALLOWED_ORIGINS` explícito, `SECRET_KEY` y `SETTINGS_ENCRYPTION_KEY` de 32+ caracteres, y `PUBLIC_BASE_URL` con HTTPS.

> La sesión web viaja en una cookie `HttpOnly` (`school_pos_session`) con protección CSRF de doble envío (`school_pos_csrf` + cabecera `X-CSRF-Token`). Los clientes de API pueden seguir usando `Authorization: Bearer <token>`; el token incluye `iss`, `aud`, `jti`, `iat` y `ver`, y se revoca al cambiar la contraseña o desactivar el usuario.

### 4️⃣ Esquema de base de datos (Alembic)

La aplicación **no crea ni altera tablas al arrancar**. El esquema se aplica explícitamente:

```bash
cd /var/www/school_pos/backend
source venv/bin/activate
alembic upgrade head
python -m app.db.init_db          # seed idempotente: PayU + admin inicial
python -m app.db.init_db --check  # verifica tablas, PayU activo y admin
```

Use un usuario de BD con permisos DDL solo para las migraciones; el usuario de la aplicación puede quedarse sin permisos DDL.

> ⚠️ **Recreación de esquema:** si viene de una instalación anterior sin movimientos (`transactions = 0`), revise `backend/scripts/reset_db.py`. Es destructivo, exige `ALLOW_DB_RESET=true` y `--yes-i-have-a-backup`, y debe ejecutarse solo después de un backup verificado y con confirmación explícita.

### 5️⃣ Despliegue repetible (recomendado)

```bash
cd /var/www/school_pos
./fix_deploy.sh      # git pull → bcrypt → alembic upgrade head → reinicia systemd → health/login
```

El script autodetecta el servicio systemd y la ruta del backend (`BACKEND_DIR` / `SERVICE_NAME` si quieres forzarlos). Aplica `alembic upgrade head` **antes** de reiniciar; si la migración falla, no toca el servicio.

Después de desplegar, verifique `GET /health` y ejecute el smoke test de la sección de pruebas.

### 6️⃣ Frontend (Vue.js)

```bash
cd frontend
npm install
npm run build        # genera frontend/dist (PWA)
```

### 6.1 Publicar el ejecutable del lector NFC

El botón de descarga usa `GET /api/v1/downloads/nfc-reader` y solo está disponible para usuarios `admin`, `supervisor` y `vendedor`.

1. En Windows, ejecuta `compilar_lector_exe.bat` y verifica que exista `backend/dist/ACR122U_NFC.exe`.
2. Publica ese archivo en el servidor o en el almacenamiento definido para la instalación.
3. En el `.env` del backend, configura `NFC_EXECUTABLE_PATH` si el archivo no está en `backend/dist` y actualiza `NFC_EXECUTABLE_VERSION` para cada release.
4. El endpoint entrega un nombre versionado y el hash SHA-256 en la cabecera `X-Content-SHA256`.

### 7️⃣ Nginx

Configurar el virtual host en `/etc/nginx/sites-available/school_pos`:
- Proxy inverso al backend (puerto 8000).
- Servir estáticos desde `frontend/dist` (SPA → prueba de vuelta a `index.html` para rutas tipo `/admin/payments`).

---

## 🧪 Pruebas

La suite usa `pytest` con SQLite en memoria para pruebas funcionales y MySQL real para concurrencia.

```bash
cd backend
source venv/bin/activate          # o venv\Scripts\activate en Windows
python -m pytest -q
```

Cubre, entre otros:

- **Autorización:** creación de usuarios solo por admin, settings privados, `cards/check` y `sales/recent` solo para staff, límites diarios solo admin/supervisor.
- **Autenticación:** claims y tipo de token, revocación por `token_version`, cookie `HttpOnly` + CSRF, logout, bloqueo por intentos fallidos, cambio forzado de contraseña, recuperación con token de un solo uso y cifrado de `smtp_pass` en reposo.
- **PayU:** firma válida/ inválida/ausente, merchant, monto y moneda; abono exacto una sola vez; replay y notificaciones rechazadas.
- **Dinero:** ventas atómicas, saldo/stock insuficiente, cupo diario, reversos únicos, compras y ajustes de stock.
- **Importación:** no puede modificar admins ni crear cuentas con contraseñas débiles.
- **Esquema:** cantidades/costos positivos, política de contraseñas y validaciones de producción.

Concurrencia real (requiere MySQL descartable):

```bash
TEST_DATABASE_URL="mysql+pymysql://user:pass@localhost/school_pos_test" python -m pytest tests/test_concurrency_mysql.py -q
```

**Smoke test manual antes de reanudar pagos:** login admin (cookie + CSRF) → cambio de contraseña forzado en el primer ingreso → crear padre/estudiante/tarjeta → venta POS → reverso → recarga PayU sandbox con webhook válido y falso → consulta de estado autenticada → intento anónimo de crear admin/consultar tarjeta/leer settings → reimportar empleados y confirmar que no cambia la clave de un admin.

---

## 📖 Guía de Funcionamiento por Roles

### 🏛️ Administrador (Acceso Total)

- Configuración del sistema (logo, nombre de la App y SMTP).
- Gestión de usuarios (padres, empleados y vendedores).
- Carga masiva desde Excel.
- **Estado de la pasarela de pago** (`/admin/payments`, solo PayU PSE).
- Auditoría financiera mediante confrontación de saldos.
- Acceso completo a reportes gerenciales en **PDF** y **Excel**.

### 📦 Supervisor de Inventario

- Gestión de categorías y productos.
- Registro de entradas de almacén (pedidos a proveedores).
- Reportes de inventario y valoración de bodega.

### 🛒 Vendedor (Cajero)

- Módulo POS con lectura de tarjetas NFC mediante lector ACR122U.
- Identificación del usuario, validación de saldo y cupo diario.
- Las reversiones requieren un administrador.

### 👨‍👩‍👧‍👦 Padre de Familia

- Visualización del saldo en tiempo real de sus hijos.
- **Recargas en línea con PayU PSE**.
- Control detallado de gastos por productos.
- Puede **bloquear** la tarjeta en caso de pérdida; el desbloqueo y el cambio de cupo los gestiona el colegio.

### 💳 Empleado / Staff

- Consulta de saldo y movimientos personales.
- Recarga de su propia tarjeta con PayU PSE.
- Puede bloquear su tarjeta; el desbloqueo lo realiza un administrador.
- Cambio de contraseña.

---

## 📊 Módulos de Reporte Incluidos

- Ventas Totales (por fecha, usuario, categoría y producto).
- Ventas por Producto.
- Estado de Inventario y valoración.
- Historial de Recargas (PayU CUS / referencia de pasarela).
- Recargas vs Consumo (extracto por estudiante).
- Entradas / Pedidos por proveedor.

---

## 🛡️ Seguridad y Mantenimiento

- 🔐 **Webhooks endurecidos**
  Solo se abona una recarga si la notificación de PayU tiene `merchant_id` correcto, firma válida, moneda y monto exactos. El procesamiento bloquea tarjeta y transacción, es idempotente y archiva cada notificación en `payment_notifications` (IP, firma válida, motivo y cuerpo crudo) para auditoría y replay.

- 💰 **Integridad del dinero**
  Saldos, precios y cupos usan `DECIMAL(12,2)`; ventas, reversos, compras y ajustes usan bloqueos `SELECT ... FOR UPDATE` en orden determinista y un único `commit`. Cantidades y costos deben ser positivos.

- 🔐 **Sesiones endurecidas**
  La web usa cookie `HttpOnly` + `SameSite` y protección CSRF de doble envío; los clientes de API pueden autenticarse con Bearer. El JWT valida `iss`/`aud`/`typ` y se revoca con `token_version` al cambiar la contraseña, desactivar la cuenta o cerrar todas las sesiones. El login bloquea la cuenta tras 5 intentos fallidos durante 15 minutos y responde con un mensaje uniforme (incluye verificación bcrypt ficticia para emails inexistentes).

- 🔑 **Contraseñas y secretos**
  Contraseñas con **Bcrypt** y política mínima (10 caracteres, letras y números, lista de claves comunes). La recuperación usa tokens aleatorios de un solo uso almacenados como hash SHA-256, con expiración y consumo atómico. `must_change_password` se aplica en el backend tras un reset administrativo o una importación. `smtp_pass` se guarda cifrado (Fernet, prefijo `enc:v1:`) y nunca se devuelve en las respuestas.

- 🗄️ **Migraciones explícitas**
  El esquema se gestiona con **Alembic** (`alembic upgrade head`). La aplicación no ejecuta DDL al arrancar.

- 🔒 **Importación y privacidad**
  La importación masiva no puede cambiar el rol ni la contraseña de usuarios existentes que no sean empleados/padres, ni reutilizar claves por defecto. `GET /settings/` nunca devuelve `smtp_pass`; el frontend público solo consume `/settings/public`.

- ⏳ **Pendiente para Fase 3**
  TOTP para administradores, CSP estricta, rate limiting en Nginx (login, recuperación, webhooks) y cabeceras de seguridad adicionales.

- 🌐 **Superficie mínima**
  `POST /users/` exige admin, los endpoints de tarjetas y ventas recientes exigen personal autenticado, y en producción se deshabilitan `/docs`, `/redoc` y OpenAPI. CORS solo acepta orígenes explícitos.

- 📱 **PWA**
  Instalación como App en iOS y Android, con modo consulta offline. Tras cada despliegue, fuerza recarga con **Ctrl+F5** para actualizar el service worker.

- 🧪 **Entornos de prueba**
  Use `PAYU_IS_TEST=true` y el endpoint sandbox de PayU hasta validar el flujo completo. Las pruebas automatizadas no contactan servicios externos.

---

## 👨‍💻 Autor

**Desarrollado por:** Joán Fuentes / Joán'Soft Corp.
copyright © 2025