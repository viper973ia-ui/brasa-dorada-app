# 🔥 La Brasa Dorada — Sistema de gestión de restaurante

Aplicación completa en **Python + Streamlit + SQLite** que gestiona un restaurante:
mapa de mesas en vivo (con **unión y separación de mesas** según comensales), comandas y
pantalla de cocina, caja con tickets, dashboard analítico, gestión de la carta y reservas.
La base de datos se puebla automáticamente con **180 días de actividad simulada**
(≈10.800 pedidos y ≈109.000 líneas de pedido) para que todos los gráficos tengan vida.

## ▶️ Cómo ejecutarla

```bash
pip install -r requirements.txt
streamlit run app.py          # abre http://localhost:8501
```

Opcional:

```bash
uvicorn api:app --reload      # API REST → http://localhost:8000/docs
pytest -q                     # tests unitarios
python seed_data.py           # (re)crear la base de datos con datos de ejemplo
```

> La primera ejecución crea `restaurante.db` y `carta.json` automáticamente.
> Para empezar de cero, borra `restaurante.db` y vuelve a lanzar la app.

## 🧭 Módulos

| Página | Qué hace |
|---|---|
| 🏠 Inicio (`app.py`) | KPIs en tiempo real, indicador de ocupación, estado de mesas, ingresos 30 días |
| 🗺️ Mapa de Mesas | Plano por zonas, asistente que sugiere qué mesas unir, unir / separar / abrir mesas |
| 🍽️ Pedidos | Toma de comandas por mesa con buscador de carta y pantalla de cocina (KDS) |
| 💳 Caja | Cobro, propina, dividir cuenta, cambio, ticket descargable y cierre de caja |
| 📊 Dashboard | Filtros por fechas/zona/servicio, KPIs con variación, tendencias, mapa de calor, ingeniería de menú, gráficos matplotlib/seaborn, exportación CSV |
| 📖 Carta | Ver, editar (tabla editable), añadir platos, importar/exportar CSV y JSON |
| 📅 Reservas | Agenda diaria, alta con validación y asignación automática de mesa (uniendo mesas si hace falta) |

## 📚 Temario del curso cubierto

| Tema | Dónde se aplica |
|---|---|
| Fundamentos (variables, tipos, operadores, condicionales, bucles) | En todos los archivos; `seed_data.py` (simulación) |
| Listas, tuplas, diccionarios, conjuntos, comprensiones | `gestor_mesas.py` (grupos), `seed_data.py` (carta), `5_Carta.py` |
| Funciones, lambdas, `map` / `filter` / `sorted` | `models.py` (`Pedido.subtotal`, `agregar_linea`), `6_Reservas.py`, `4_Dashboard.py` |
| `itertools.combinations` (algoritmo de unión de mesas) | `gestor_mesas.py → sugerir()`, `6_Reservas.py` |
| Cadenas y f-strings | Ticket de caja (`3_Caja.py`), validación de email/teléfono (`6_Reservas.py`), `styles.euros()` |
| Fechas con `datetime` / `timedelta` | `seed_data.py`, `analytics.py`, `6_Reservas.py`, cierre de caja |
| Ficheros CSV / JSON y excepciones | `carta.json`, import/export en `5_Carta.py`, ticket .txt, excepciones propias en `models.py` |
| POO: clases, herencia, `@property`, `@classmethod`, Singleton | `database.py` (Singleton), `models.py` (`EntidadBase` → `Mesa`, `Producto`, `Pedido`) |
| NumPy | Generación aleatoria (`seed_data.py`), `polyfit`, percentiles, `np.select` |
| pandas | `analytics.py`: `resample`, `rolling`, `pivot_table`, `groupby` |
| Polars | `analytics.py`: ranking de productos (API lazy) e ingeniería de menú |
| matplotlib / seaborn | Pestaña «Matplotlib / Seaborn» del Dashboard |
| Plotly | Todas las páginas (gauge, donut, heatmap, sunburst, treemap, violín…) |
| Streamlit | Interfaz multipágina, `session_state`, `cache_data`, formularios, `data_editor` |
| Bases de datos (SQL) | `database.py` con SQLite (7 tablas relacionadas); intercambiable por MySQL |
| Buenas prácticas y testing | Módulos separados, docstrings, `tests/test_modelos.py` con pytest |
| FastAPI | `api.py` (GET `/mesas`, `/carta`, `/ventas/resumen`, POST `/mesas/sugerir`) |

## 🗂️ Estructura

```
restaurante_app/
├── app.py               # Inicio
├── pages/               # 6 páginas de Streamlit
├── database.py          # Conexión SQLite (Singleton) y creación de tablas
├── models.py            # Clases del dominio y excepciones
├── gestor_mesas.py      # Unir / separar / sugerir mesas
├── analytics.py         # Cálculos con pandas, NumPy y Polars
├── seed_data.py         # Datos de ejemplo
├── styles.py            # Tema visual y componentes HTML
├── api.py               # API REST con FastAPI
├── tests/               # Tests con pytest
└── .streamlit/config.toml
```
