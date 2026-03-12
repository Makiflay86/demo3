# Claude Code Plugin — Grand Luxe Hotel

Plugin reutilizable con la configuración de Claude Code usada en el proyecto **Grand Luxe Hotel**. Incluye convenciones de idioma, plantilla de `CLAUDE.md` y un hook de formateo automático con `black`.

---

## Contenido

```
plugin/
├── README.md                   # Esta guía
├── CLAUDE.md                   # Plantilla de instrucciones para Claude Code
└── .claude/
    ├── settings.json           # Hooks de Claude Code
    └── hooks/
        └── black_format.sh     # Formateador automático de Python
```

### `CLAUDE.md`
Plantilla de instrucciones para Claude Code con:
- Convención de idioma (español para todo excepto nombres de código)
- Estructura de archivos recomendada
- Convenciones de Python, JavaScript y tests
- Secciones para documentar arquitectura, endpoints y modelo de datos

### `black_format.sh`
Hook `PostToolUse` que ejecuta [`black`](https://black.readthedocs.io/) automáticamente sobre cualquier archivo `.py` editado o creado por Claude Code.

Detecta `black` en este orden:
1. `venv/bin/black` (entorno virtual en la raíz del proyecto)
2. `.venv/bin/black`
3. `black` global en el `PATH`

### `settings.json`
Activa el hook de formateo para los eventos `Edit` y `Write` de Claude Code.

---

## Instalación

### Opción A — Copiar manualmente

1. Copia `CLAUDE.md` a la raíz de tu proyecto y edítalo:
   ```bash
   cp plugin/CLAUDE.md /ruta/a/tu-proyecto/CLAUDE.md
   ```

2. Copia la carpeta `.claude/` a la raíz de tu proyecto:
   ```bash
   cp -r plugin/.claude /ruta/a/tu-proyecto/.claude
   ```

3. Dale permisos de ejecución al hook:
   ```bash
   chmod +x /ruta/a/tu-proyecto/.claude/hooks/black_format.sh
   ```

4. Asegúrate de tener `black` instalado:
   ```bash
   ./venv/bin/pip install black
   # o globalmente:
   pip install black
   ```

### Opción B — Script de instalación

Ejecuta desde la carpeta `plugin/`:
```bash
bash install.sh /ruta/a/tu-proyecto
```

> El script copia los archivos, ajusta permisos y verifica que `black` esté disponible.

---

## Uso

Una vez instalado, Claude Code formateará automáticamente con `black` cualquier archivo `.py` que edite. No requiere ninguna acción manual.

Para verificar que el hook está activo, edita cualquier archivo Python desde Claude Code y comprueba que el formato se aplica al guardar.

---

## Personalización

### Cambiar el formateador

Edita `.claude/hooks/black_format.sh` y sustituye la llamada a `black` por tu herramienta preferida (ej. `ruff format`, `autopep8`).

### Añadir más hooks

Edita `.claude/settings.json` siguiendo la estructura:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          { "type": "command", "command": ".claude/hooks/mi_hook.sh" }
        ]
      }
    ]
  }
}
```

Los eventos disponibles son: `PreToolUse`, `PostToolUse`, `Notification`, `Stop`.

### Adaptar el `CLAUDE.md`

Rellena las secciones con `[corchetes]` con la información específica de tu proyecto:
- Nombre y descripción
- Arquitectura y estructura de archivos
- Comandos de arranque y test
- Endpoints de la API
- Modelo de datos

---

## Requisitos

| Herramienta | Versión mínima |
|-------------|----------------|
| Python | 3.8+ |
| black | 23.0+ |
| Claude Code | cualquiera |

---

## Origen

Extraído del proyecto **Grand Luxe Hotel** — sistema de gestión de habitaciones construido con FastAPI + SQLite + frontend SPA.
