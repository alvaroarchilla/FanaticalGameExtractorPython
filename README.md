# Fanatical & Humble Bundle Game Extractor (Playwright)

Extrae los juegos de bundles de [Fanatical](https://www.fanatical.com) (pick-and-mix) y de [Humble Bundle](https://www.humblebundle.com/games), consulta sus datos en Steam (precio, reviews, categorías, tags, etc.) y genera reportes **HTML interactivos** (DataTables).

Incluye un modo `--pretty` con portada del juego, estilo oscuro y resaltado dorado para títulos con **pantalla compartida / multijugador local**.

> Uso personal / educativo. Respeta los términos de Fanatical, Humble Bundle y Steam; no abuses de la frecuencia de las peticiones.

## Características

- Flujo en dos fases: recolecta ítems en Fanatical/Humble y luego visita Steam
- Un bundle concreto, todos los del listado (un HTML por bundle) o **un HTML combinado**
- **Humble**: tiers con precio de desbloqueo (“Pay at least …”) y lista de juegos por tier
- Reportes en `reports/` con ordenación y búsqueda
- `--pretty`: imágenes de cabecera Steam, marco dorado en local/shared screen, enlaces cortos
- Columna **Links**: Steam + enlace al bundle de origen (Fanatical o Humble)

## Requisitos

- Python 3.10+ (probado con 3.13)
- Windows, macOS o Linux

## Instalación

```bash
git clone <URL_DEL_REPO>
cd FanaticalGameExtractorPlaywright

python -m venv venv

# Windows (PowerShell)
.\venv\Scripts\Activate.ps1

# macOS / Linux
source venv/bin/activate

pip install -r requirements.txt
playwright install chromium
```

## Uso

Los comandos se ejecutan desde la raíz del proyecto con el entorno virtual activado.

### Opciones globales

| Opción | Descripción |
|--------|-------------|
| `--url` | URL del bundle (tests parametrizados) |
| `--pretty` | HTML enriquecido (imagen, local MP dorado) |
| `--html-output` | Nombre base del archivo HTML (sin `.html`) |
| `--headed` | Abre el navegador visible (pytest-playwright) |

---

## Fanatical

### Un solo pick-and-mix

```bash
pytest tests/test_fanatical_to_html_parametrized.py -s --url "https://www.fanatical.com/en/pick-and-mix/TU-BUNDLE"
pytest tests/test_fanatical_to_html_parametrized.py -s --pretty --url "https://www.fanatical.com/en/pick-and-mix/TU-BUNDLE"
```

### Todos los pick-and-mix (un HTML por bundle)

Listado: `https://www.fanatical.com/en/bundle/games`

```bash
pytest tests/test_fanatical_all_bundles.py -s
pytest tests/test_fanatical_all_bundles.py -s --pretty
```

### Todos los pick-and-mix en un solo HTML

```bash
pytest tests/test_fanatical_all_bundles_combined.py -s --pretty
pytest tests/test_fanatical_all_bundles_combined.py -s --pretty --html-output mi_combinado
```

Salida típica: `reports/all_fanatical_pick_and_mix_combined_pretty.html`

---

## Humble Bundle

Los bundles de juegos se leen desde [humblebundle.com/games](https://www.humblebundle.com/games). En el HTML verás:

- Bloque superior con **cada tier**, su **precio** y los **juegos** que desbloquea
- Columna **Tier** por fila (precio mínimo para obtener ese juego)
- Soundtrack / cupones / etc. se omiten del scrape de Steam (sí se mencionan en el resumen del tier)

### Un solo bundle

```bash
pytest tests/test_humble_to_html_parametrized.py -s --url "https://www.humblebundle.com/games/awesome-indie-adventures"
pytest tests/test_humble_to_html_parametrized.py -s --pretty --url "https://www.humblebundle.com/games/awesome-indie-adventures"
```

Si no pasas `--url`, usa un bundle de ejemplo por defecto.

### Todos los bundles de /games (un HTML por bundle)

```bash
pytest tests/test_humble_all_bundles.py -s
pytest tests/test_humble_all_bundles.py -s --pretty
```

### Todos en un solo HTML

```bash
pytest tests/test_humble_all_bundles_combined.py -s --pretty
pytest tests/test_humble_all_bundles_combined.py -s --pretty --html-output mi_humble_combinado
```

Salida típica: `reports/all_humble_game_bundles_combined_pretty.html`

---

## Estructura del proyecto

```
├── config/
├── pages/
│   ├── fanatical_home_page.py
│   ├── humble_bundle_page.py
│   └── steam_game_page.py
├── tests/
│   ├── conftest.py
│   ├── utils_html_report.py          # Fanatical
│   ├── utils_humble_html_report.py   # Humble (+ tiers)
│   ├── test_fanatical_*.py
│   └── test_humble_*.py
├── reports/
├── requirements.txt
└── pytest.ini
```

## Datos que se extraen (Steam)

- Nombre, URL, precio
- Reviews (global y 30 días)
- Categorías y tags (game labels)
- Fecha de lanzamiento, editor y desarrollador
- En modo `--pretty`: portada y detección de local / shared screen
- **Humble**: precio de tier de desbloqueo

## Notas

- El viewport del navegador está fijado a 1400×900.
- Si Steam oculta resultados por preferencias, el scraper intenta emparejar por **nombre** entre los títulos excluidos.
- La generación puede tardar bastante (muchas fichas de Steam). Prueba primero con un solo bundle.

## Licencia

Uso personal. Añade la licencia que prefieras (MIT, etc.) si publicas el repositorio.
