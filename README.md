# 🥗 School POS System - Gestión de Cafetería Escolar Pro

**School POS** es una plataforma integral de gestión de ventas para cafeterías escolares de alto nivel.
Diseñada para eliminar el uso de efectivo dentro del colegio, permite pagos rápidos mediante **tarjetas RFID/NFC**, **recargas en línea multi-pasarela (PayU PSE, Wompi, Mercado Pago)** y un **control administrativo total** sobre el inventario y las finanzas.

![version](https://img.shields.io/badge/version-1.1.0-blue)
![backend](https://img.shields.io/badge/Backend-FastAPI-green)
![frontend](https://img.shields.io/badge/Frontend-Vue%203-blue)
![payments](https://img.shields.io/badge/Pagos-Multi%20pasarela-purple)
![pwa](https://img.shields.io/badge/PWA-Ready-orange)

---

## 🚀 Características Principales

- 💳 **Ecosistema Cashless**
  Pagos con tarjetas inteligentes NFC (Mifare / ISO 14443A) y lectores NFC ACR122U vinculadas a estudiantes y empleados.

- 💰 **Pasarelas de Pago Intercambiables**
  - **PayU Colombia (PSE)** — pasarela activa por defecto.
  - **Wompi (Colombia)** — Nequi, PSE, QR, tarjetas.
  - **Mercado Pago** — Checkout Pro / PSE / Nequi.
  - El administrador **cambia la pasarela activa desde el panel web** (`💳 Pasarela de pago`, `/admin/payments`) **sin redeploy**, con una sola pasarela activa a la vez.

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

## 🏗️ Arquitectura de Pasarelas de Pago

Cada pasarela implementa el contrato `PaymentProvider` (`backend/app/payment_providers/`):

```
payment_providers/
├── base.py              → PaymentProvider (ABC): get_methods / init_recharge / handle_notification
├── registry.py          → register() + get_provider() + get_active_provider() (fallback seguro a PayU)
├── payu_provider.py     → PayU PSE (activa por defecto; mismo contrato de hoy)
├── wompi_provider.py    → Wompi (Nequi / PSE / QR / tarjeta)
├── mercadopago_provider.py → Mercado Pago (Checkout Pro / PSE / Nequi)
└── __init__.py          → registra los providers al importar el paquete
```

La tabla `payment_gateway_settings` guarda la pasarela activa, modo test y si tiene credenciales configuradas. Al arrancar, `main.py` siembra las 3 (PayU activa) y aplica migraciones idempotentes (columnas `gateway`, `currency`, `raw_notification`, `response_code` en `transactions`).

### 🧭 Endpoints neutros de pago (`/api/v1/payments/*`)

| Método | Endpoint | Descripción |
|---|---|---|
| GET | `/payments/providers` | Lista pasarelas (admin) |
| POST | `/payments/providers/activate` | Cambia la pasarela activa (admin) |
| GET | `/payments/methods` | Métodos de la pasarela activa para el modal de recarga |
| POST | `/payments/init` | Inicia la recarga → `redirect_url` |
| POST | `/payments/notify/{gateway}` | Webhook de confirmación (PayU/Wompi/MP) |
| GET | `/payments/status/{reference}` | Estado de una recarga |

Los endpoints legacy `/recharges/*` (incluido `payu-confirmation`, **endurecido**: validación de `merchant_id`, firma, idempotencia y auditoría `raw_notification`) se mantienen como compatibilidad.

> **Wompi / Mercado Pago**: requieren crear su cuenta de desarrollador (gratis, modo sandbox). Mientras no existan credenciales en el `.env`, el panel las muestra como "Faltan credenciales" y **PayU sigue operando sin cambios**.

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
DATABASE_URL="mysql+pymysql://pos_user:TuClaveSegura@localhost/school_pos_db"
SECRET_KEY="cambia-esta-clave"
ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES=30
ALLOWED_ORIGINS="*"
FRONTEND_URL="https://TU_DOMINIO"

# PayU (activa por defecto)
PAYU_MERCHANT_ID="..."
PAYU_API_KEY="..."
PAYU_API_LOGIN="..."
PAYU_ACCOUNT_ID="..."
PAYU_IS_TEST=True
PAYU_URL="https://sandbox.api.payulatam.com/payments-api/4.0/service.cgi"

# Wompi (activa cuando completes credenciales sandbox)
WOMPI_PUBLIC_KEY="pub_test_..."
WOMPI_PRIVATE_KEY="prv_test_..."
WOMPI_WEBHOOK_SECRET="..."
WOMPI_IS_TEST=True
WOMPI_URL="https://sandbox.wompi.co/v1"

# Mercado Pago
MP_ACCESS_TOKEN="TEST-..."
MP_WEBHOOK_SECRET="..."
MP_URL="https://api.mercadopago.com"
```

> **Las tablas y columnas nuevas se crean/actualizan solas al arrancar** (`Base.metadata.create_all` + migraciones idempotentes en `main.py`). No hace falta SQL manual para `pending_balance`, `gateway`, etc.

### 4️⃣ Despliegue repetible (recomendado)

```bash
cd /var/www/school_pos
./fix_deploy.sh      # git pull → verifica bcrypt → migraciones → reinicia systemd → revisa logs/login
```

El script autodetecta el servicio systemd y la ruta del backend (`BACKEND_DIR` / `SERVICE_NAME` si quieres forzarlos).

### 5️⃣ Frontend (Vue.js)

```bash
cd frontend
npm install
npm run build        # genera frontend/dist (PWA)
```

### 6️⃣ Nginx

Configurar el virtual host en `/etc/nginx/sites-available/school_pos`:
- Proxy inverso al backend (puerto 8000).
- Servir estáticos desde `frontend/dist` (SPA → prueba de vuelta a `index.html` para rutas tipo `/admin/payments`).

---

## 🧪 Pruebas del Contrato de Pasarelas

Sin red real ni base de datos (mocks de `requests` + sesión falsa). Validan métodos expuestos, resultado normalizado, abono de saldo e idempotencia:

```bash
cd backend
python -m unittest discover -s tests -v   # esperado: OK (16 tests)
```

Cubre PayU, Wompi, Mercado Pago y el registro/activación por registry.

---

## 📖 Guía de Funcionamiento por Roles

### 🏛️ Administrador (Acceso Total)

- Configuración del sistema (logo, nombre de la App y SMTP).
- Gestión de usuarios (padres, empleados y vendedores).
- Carga masiva desde Excel.
- **Selección de la pasarela de pago activa** (`/admin/payments`).
- Auditoría financiera mediante confrontación de saldos.
- Acceso completo a reportes gerenciales en **PDF** y **Excel**.

### 📦 Supervisor de Inventario

- Gestión de categorías y productos.
- Registro de entradas de almacén (pedidos a proveedores).
- Reportes de inventario y valoración de bodega.

### 🛒 Vendedor (Cajero)

- Módulo POS con lectura de tarjetas NFC mediante lector ACR122U.
- Identificación del usuario, validación de saldo y cupo diario.
- Reversión de ventas recientes (según permisos).

### 👨‍👩‍👧‍👦 Padre de Familia

- Visualización del saldo en tiempo real de sus hijos.
- **Recargas en línea con la pasarela activa** (PayU PSE / Wompi / Mercado Pago).
- Control detallado de gastos por productos.
- Bloqueo de tarjetas en caso de pérdida.

### 💳 Empleado / Staff

- Consulta de saldo y movimientos personales.
- Recarga de tarjeta propia vía la pasarela activa.
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
  El webhook de PayU valida `merchant_id` y firma, aplica **idempotencia** (una notificación duplicada jamás abona dos veces) y archiva la **notificación cruda** (`raw_notification`) en cada transacción para auditoría.

- 🗄️ **Migraciones automáticas**
  `main.py` ejecuta migraciones idempotentes al arrancar (`pending_balance`, columnas de pasarela y seed de `payment_gateway_settings`).

- 🔑 **Privacidad**
  Contraseñas almacenadas con hashing de una sola vía (**Bcrypt**).

- 📱 **PWA**
  Instalación como App en iOS y Android, con modo consulta offline. Tras cada despliegue, fuerza recarga con **Ctrl+F5** para actualizar el service worker.

- 🧪 **Entornos de prueba**
  Wompi y Mercado Pago se integran en modo **sandbox** (`*_IS_TEST=True`) usando sus llaves de prueba gratuitas; PayU opera con sus credenciales de prueba hasta pasar a producción.

---

## 👨‍💻 Autor

**Desarrollado por:** Joán Fuentes / Joán'Soft Corp.
copyright © 2025