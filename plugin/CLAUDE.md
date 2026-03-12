# [Nombre del Proyecto] — CLAUDE.md

## Idioma

**El idioma principal y único de este proyecto es el español.**

- Nombres de variables, funciones y clases: inglés (convención Python/JS)
- Mensajes de error de la API, labels del frontend, comentarios de código, commits, nombres de tests, documentación: **español**
- Valores de datos del dominio: español cuando proceda

---

## Descripción

[Breve descripción del proyecto: qué hace, para quién, qué problema resuelve.]

---

## Arquitectura

[Diagrama ASCII o descripción de la arquitectura del sistema.]

```
NAVEGADOR
    │
    ▼
SERVIDOR (puerto XXXX)
    │
    ▼
[FRAMEWORK] (main.py / app.py)
    │
    ▼
[BASE DE DATOS]
```

---

## Estructura de archivos

```
proyecto/
├── main.py              # Punto de entrada
├── database.py          # Capa de datos
├── requirements.txt     # Dependencias
├── static/              # Assets estáticos
├── tests/               # Tests
└── .claude/             # Configuración de Claude Code
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
[comando de arranque]
```

### Ejecutar todos los tests
```bash
./venv/bin/pytest tests/ -v
```

---

## Convenciones de código

### Python
- Nombres de funciones y variables en `snake_case`
- Clases en `PascalCase`
- Validaciones de negocio en los propios endpoints, no en el modelo
- Siempre hacer `db.refresh(obj)` después de `db.commit()` antes de devolver el objeto

### JavaScript
- `camelCase` para funciones y variables
- Toda comunicación con la API pasa por una función central (ej. `apiFetch()`)

### Tests
- Cada test recibe una BD limpia (fixture) — sin estado compartido entre tests
- Los tests nunca tocan la BD de producción — siempre SQLite en memoria o BD de test
- Nombres de test en formato: `test_<acción>_<condición>`

---

## Endpoints de la API

[Documentar aquí los endpoints principales.]

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/api/...` | ... |
| `POST` | `/api/...` | ... |

### Códigos de error

| Código | Cuándo |
|--------|--------|
| `400` | Lógica de negocio inválida |
| `404` | Recurso no encontrado |
| `422` | Body malformado (validación) |

---

## Modelo de datos

[Describir las tablas/colecciones principales.]

---

## Notas adicionales

[Cualquier decisión de diseño, deuda técnica conocida o contexto relevante.]
