# Grand Luxe Hotel — CLAUDE.md

## Idioma

**El idioma principal y único de este proyecto es el español.**

- Nombres de variables, funciones y clases: inglés (convención Python/JS)
- Mensajes de error de la API, labels del frontend, comentarios de código, commits, nombres de tests, documentación: **español**
- Valores de datos del dominio (`status`, `type`): español (`disponible`, `ocupada`, `mantenimiento`, `suite`, `doble`, `individual`)

---

## Descripción

Sistema de gestión de habitaciones para un hotel de lujo. Permite crear, reservar, liberar y eliminar habitaciones, con estadísticas en tiempo real. Un único servidor FastAPI sirve tanto la API REST como el frontend estático.

---

## Arquitectura

```
NAVEGADOR
    │
    │  GET /              → index.html (frontend SPA)
    │  GET /api/...       → JSON (datos)
    │  POST/PATCH/DELETE  → acciones
    ▼
UVICORN (puerto 8000)
    │
    ▼
FASTAPI (main.py)
    ├── Schemas Pydantic   → validación de entrada/salida
    ├── Endpoints API      → lógica de negocio
    ├── StaticFiles        → sirve /static/*
    └── FileResponse       → sirve / → index.html
            │
            ▼
        SQLAlchemy ORM (database.py)
            │
            ▼
        SQLite (hotel.db)
        tabla: rooms
```

**Sin separación frontend/backend**: el mismo servidor en `:8000` sirve todo. El frontend hace `fetch('/api/...')` con rutas relativas — no hay CORS ni configuración de proxy.

---

## Estructura de archivos

```
demo-3/
├── main.py              # Aplicación FastAPI: schemas, endpoints, montaje de estáticos
├── database.py          # Engine SQLite, modelo Room, get_db(), init_db()
├── requirements.txt     # Dependencias Python (fastapi, uvicorn, sqlalchemy, pydantic)
├── hotel.db             # Base de datos SQLite (generada automáticamente, ignorar en git)
├── static/
│   └── index.html       # Frontend completo (HTML + CSS + JS en un solo archivo)
├── tests/
│   ├── __init__.py
│   ├── test_api.py      # 45 tests de endpoints HTTP con TestClient
│   └── test_database.py # 14 tests de lógica de BD con SQLite en memoria
└── venv/                # Entorno virtual Python (ignorar en git)
```

---

## Comandos

### Instalar dependencias
```bash
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
```

### Arrancar el servidor
```bash
./venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```
El frontend queda disponible en **http://localhost:8000**
La documentación automática de la API en **http://localhost:8000/docs**

### Ejecutar todos los tests
```bash
./venv/bin/pytest tests/ -v
```

### Ejecutar solo tests de API
```bash
./venv/bin/pytest tests/test_api.py -v
```

### Ejecutar solo tests de base de datos
```bash
./venv/bin/pytest tests/test_database.py -v
```

### Ejecutar un test específico
```bash
./venv/bin/pytest tests/test_api.py::TestCreateRoom::test_create_room_success -v
```

---

## Endpoints de la API

Todos los endpoints devuelven y aceptan JSON. Base URL: `http://localhost:8000`

### Habitaciones

| Método | Ruta | Descripción | Body | Respuesta |
|--------|------|-------------|------|-----------|
| `GET` | `/api/rooms` | Lista todas las habitaciones. Acepta `?status=disponible\|ocupada\|mantenimiento` | — | `200` array de `RoomResponse` |
| `POST` | `/api/rooms` | Crea una habitación nueva | `RoomCreate` | `201` `RoomResponse` |
| `PATCH` | `/api/rooms/{id}/reserve` | Reserva una habitación disponible | `RoomReserve` | `200` `RoomResponse` |
| `PATCH` | `/api/rooms/{id}/release` | Libera una habitación ocupada | — | `200` `RoomResponse` |
| `PATCH` | `/api/rooms/{id}/maintenance` | Pone una habitación en mantenimiento | — | `200` `RoomResponse` |
| `DELETE` | `/api/rooms/{id}` | Elimina una habitación | — | `204` sin body |

### Estadísticas

| Método | Ruta | Descripción | Respuesta |
|--------|------|-------------|-----------|
| `GET` | `/api/stats` | Totales en tiempo real | `200` objeto stats |

### Schemas

**`RoomCreate`** (body de POST /api/rooms):
```json
{ "number": "502", "type": "suite", "price_per_night": 450.0 }
```

**`RoomReserve`** (body de PATCH .../reserve):
```json
{ "guest_name": "Ana García" }
```

**`RoomResponse`** (respuesta estándar):
```json
{
  "id": 1,
  "number": "101",
  "type": "individual",
  "price_per_night": 150.0,
  "status": "disponible",
  "guest_name": null
}
```

**`/api/stats` response**:
```json
{
  "total": 5,
  "occupied": 2,
  "available": 2,
  "maintenance": 1,
  "estimated_revenue": 1230.0
}
```

### Códigos de error

| Código | Cuándo |
|--------|--------|
| `400` | Lógica de negocio inválida (tipo inválido, precio ≤ 0, número duplicado, habitación no disponible para reservar) |
| `404` | Habitación no encontrada por `id` |
| `422` | Body malformado o campos requeridos faltantes (Pydantic) |

---

## Modelo de datos

**Tabla `rooms`** en `hotel.db`:

| Columna | Tipo | Restricciones | Descripción |
|---------|------|---------------|-------------|
| `id` | INTEGER | PK, autoincrement | Identificador interno |
| `number` | TEXT | UNIQUE, NOT NULL | Número visible de la habitación (ej. "401") |
| `type` | TEXT | NOT NULL | `suite` \| `doble` \| `individual` |
| `price_per_night` | REAL | NOT NULL | Precio en euros |
| `status` | TEXT | DEFAULT `disponible` | `disponible` \| `ocupada` \| `mantenimiento` |
| `created_at` | DATETIME | DEFAULT now | Fecha de creación |
| `guest_name` | TEXT | nullable | Nombre del huésped cuando está ocupada |

**Reglas de estado**:
- Solo se puede **reservar** una habitación en estado `disponible`
- Al **liberar** o poner en **mantenimiento**, `guest_name` se pone a `null`
- Se puede eliminar una habitación en cualquier estado

---

## Convenciones de código

### Python (`main.py`, `database.py`)
- Nombres de funciones y variables en `snake_case`
- Clases en `PascalCase`
- Schemas Pydantic en el mismo archivo `main.py` (proyecto pequeño, no justifica separar)
- Validaciones de negocio en los propios endpoints, no en el modelo
- `get_db()` siempre via `Depends()` — nunca instanciar `SessionLocal` directamente en endpoints
- Siempre hacer `db.refresh(room)` después de `db.commit()` antes de devolver el objeto

### JavaScript (`static/index.html`)
- `camelCase` para funciones y variables
- Toda comunicación con el API pasa por `apiFetch()` — nunca `fetch()` directo
- El frontend no tiene estado global salvo `currentFilter` y `pendingReserveId`
- El HTML de las tarjetas se genera en `renderRooms()` vía template literals — no manipular el DOM elemento a elemento

### CSS (`static/index.html`)
- Todas las constantes de color y espaciado como variables CSS en `:root`
- Modificar solo variables CSS para cambiar el tema visual, nunca valores hardcodeados dispersos

### Tests
- Cada test recibe una BD limpia (fixture `client` o `db_session`) — sin estado compartido entre tests
- Los tests nunca tocan `hotel.db` — siempre SQLite en memoria (`:memory:` con `StaticPool`)
- Nombres de test en formato: `test_<acción>_<condición>` en español cuando describe comportamiento de dominio

---

## Datos de ejemplo precargados

Al arrancar con BD vacía, `init_db()` inserta automáticamente:

| Número | Tipo | Precio/noche | Estado | Huésped |
|--------|------|-------------|--------|---------|
| 101 | individual | €150 | disponible | — |
| 201 | doble | €280 | ocupada | Carlos Méndez |
| 202 | doble | €260 | mantenimiento | — |
| 301 | suite | €580 | disponible | — |
| 401 | suite | €950 | ocupada | Elena Rojas |
