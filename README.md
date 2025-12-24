# 🥗 School POS System - Gestión de Cafetería Escolar Pro

**School POS** es una plataforma integral de gestión de ventas para cafeterías escolares de alto nivel.  
Diseñada para eliminar el uso de efectivo dentro del colegio, permite pagos rápidos mediante **tarjetas RFID/NFC**, **recargas en línea vía PayU / PSE**, y un **control administrativo total** sobre el inventario y las finanzas.

![version](https://img.shields.io/badge/version-1.0.0-blue)
![backend](https://img.shields.io/badge/Backend-FastAPI-green)
![frontend](https://img.shields.io/badge/Frontend-Vue%203-blue)
![pwa](https://img.shields.io/badge/PWA-Ready-orange)

---

## 🚀 Características Principales

- 💳 **Ecosistema Cashless**  
  Pagos con tarjetas inteligentes RFID/NFC vinculadas a estudiantes y empleados.

- 💰 **Pasarela de Pagos**  
  Integración nativa con **PayU Colombia (PSE)** para recargas de saldo seguras.

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

## 🛠️ Stack Tecnológico

### Backend
- Python 3.10+
- FastAPI
- SQLAlchemy (ORM)

### Frontend
- Vue.js 3
- Vite
- Tailwind CSS
- Pinia (Gestión de Estado)

### Infraestructura
- Base de Datos: **MySQL 8.0+**
- Servidor: **Ubuntu Linux**
- Web Server: **Nginx**
- ASGI: **Gunicorn / Uvicorn**
- Servicios: **Systemd**

### Seguridad
- Autenticación **JWT**
- Hashing de contraseñas con **Bcrypt**

---

## ⚙️ Instalación en Producción (Ubuntu Server)

### 1️⃣ Requisitos Previos

```bash
sudo apt update && sudo apt install python3-pip python3-venv nginx mysql-server -y
```

---

### 2️⃣ Base de Datos

```sql
CREATE DATABASE school_pos_db 
CHARACTER SET utf8mb4 
COLLATE utf8mb4_unicode_ci;

CREATE USER 'pos_user'@'localhost' IDENTIFIED BY 'TuClaveSegura';
GRANT ALL PRIVILEGES ON school_pos_db.* TO 'pos_user'@'localhost';
```

---

### 3️⃣ Backend (FastAPI)

```bash
git clone https://github.com/usuario/repo.git /var/www/school_pos
cd /var/www/school_pos
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

- Configurar el archivo `.env` con:
  - Credenciales de MySQL
  - Llaves secretas
  - Credenciales de PayU

- Configurar servicio **Systemd** en:
  ```
  /etc/systemd/system/school_pos_backend.service
  ```

---

### 4️⃣ Frontend (Vue.js)

- Configurar `.env.production` con la URL del servidor.
- Compilar el proyecto:

```bash
npm run build
```

- Subir la carpeta `dist/` al servidor:

```
/var/www/school_pos/frontend/dist
```

---

### 5️⃣ Nginx

Configurar un servidor virtual en:

```
/etc/nginx/sites-available/school_pos
```

Funciones:
- Proxy inverso hacia el backend (puerto 8000).
- Servir archivos estáticos desde la carpeta `dist`.

---

## 📖 Guía de Funcionamiento por Roles

### 🏛️ Administrador (Acceso Total)

- Configuración del sistema (logo, nombre de la App y SMTP).
- Gestión de usuarios (padres, empleados y vendedores).
- Carga masiva desde Excel.
- Auditoría financiera mediante confrontación de saldos.
- Acceso completo a reportes gerenciales en **PDF** y **Excel**.

---

### 📦 Supervisor de Inventario

- Gestión de categorías y productos.
- Registro de entradas de almacén (pedidos a proveedores).
- Reportes de inventario y valoración de bodega.

---

### 🛒 Vendedor (Cajero)

- Módulo POS con lectura de tarjetas RFID.
- Identificación del usuario, validación de saldo y cupo diario.
- Reversión de ventas recientes (según permisos).

---

### 👨‍👩‍👧‍👦 Padre de Familia

- Visualización del saldo en tiempo real de sus hijos.
- Recargas PSE mediante PayU.
- Control detallado de gastos por productos.
- Bloqueo de tarjetas en caso de pérdida.

---

### 💳 Empleado / Staff

- Consulta de saldo y movimientos personales.
- Recarga de tarjeta propia vía PSE.
- Cambio de contraseña.

---

## 📊 Módulos de Reporte Incluidos

- Ventas Totales (por fecha, usuario, categoría y producto).
- Ventas por Producto.
- Estado de Inventario y valoración.
- Historial de Recargas PayU (CUS).
- Recargas vs Consumo (extracto por estudiante).
- Entradas / Pedidos por proveedor.

---

## 🛡️ Seguridad y Mantenimiento

- 🔐 **Copias de Seguridad**  
  Dump periódico de la base de datos MySQL y respaldo de `/backend/uploads`.

- 🔑 **Privacidad**  
  Contraseñas almacenadas con hashing de una sola vía (**Bcrypt**).

- 📱 **PWA**  
  Instalación como App en iOS y Android, con modo consulta offline.

---

## 👨‍💻 Autor

**Desarrollado por:** Joán Fuentes / Joán'Soft Corp.
copyright © 2025
