# 🎮 Fanatical Game Extractor (Python)

Extractor automatizado de información de juegos desde la tienda **Fanatical** y páginas relacionadas (como Steam).  
El objetivo del proyecto es facilitar la recopilación de datos de bundles, publishers, fechas de lanzamiento y otros metadatos de juegos de forma rápida y reutilizable.

---

## 🚀 Características

- Automatización con **Selenium** para navegar y extraer datos.
- Limpieza de la interfaz inicial (cookies, popups, alertas, live streams).
- Extracción de:
  - Nombre del juego
  - Publisher / Developer
  - Fecha de lanzamiento
  - Enlaces a Steam
  - Reseñas de usuarios
  - Precio
  - Categorías
  - Etiquetas del juego
- Estructura modular con carpetas:
  - `config/` → configuración del proyecto
  - `pages/` → Page Objects para Selenium
  - `tests/` → pruebas automatizadas
  - `utils/` → utilidades y helpers

---

## 📦 Requisitos

- Python 3.9+
- Google Chrome / Chromium

Instala las dependencias con:

```bash
pip install webdriver-manager  
