"""
Carta — gestión de productos (CRUD), importación/exportación CSV y JSON.
Temas: POO (Producto, @property), ficheros CSV/JSON, excepciones, NumPy (estadísticas),
comprensiones de listas, diccionarios y cadenas.
"""
import io
import json
import os

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Carta", page_icon="📖", layout="wide")

from seed_data import inicializar
inicializar()
from database import Database, BASE_DIR
from models import Producto
from styles import aplicar_estilos, euros, kpi, PALETA, PLOTLY_TEMPLATE

aplicar_estilos("Carta", "Gestiona platos, precios y disponibilidad", "📖")
db = Database()

productos = Producto.todos()
categorias = db.fetchall("SELECT id, nombre, icono FROM categorias ORDER BY orden")
cat_id = {c["nombre"]: c["id"] for c in categorias}
iconos = {c["nombre"]: c["icono"] for c in categorias}

# ── KPIs con NumPy ───────────────────────────────────────────────────────────
precios = np.array([p.precio for p in productos])
c = st.columns(5)
kpi(c[0], "📋", "Productos", str(len(productos)))
kpi(c[1], "✅", "Disponibles", str(sum(p.disponible for p in productos)))
kpi(c[2], "💶", "Precio medio", euros(precios.mean() if precios.size else 0))
kpi(c[3], "⚖️", "Mediana", euros(np.median(precios) if precios.size else 0))
kpi(c[4], "📏", "Desv. típica", euros(precios.std() if precios.size else 0))
st.write("")

tab_menu, tab_edit, tab_nuevo, tab_io = st.tabs(["🍽️ Ver carta", "✏️ Editar", "➕ Nuevo plato", "📁 Importar / Exportar"])

# ── Vista de la carta en tarjetas ────────────────────────────────────────────
with tab_menu:
    buscar = st.text_input("🔎 Buscar plato", placeholder="Ej.: chuletón, tarta…").strip().lower()
    for cat in cat_id:
        lista = [p for p in productos if p.categoria == cat
                 and (buscar in p.nombre.lower() or buscar in (p.descripcion or "").lower())]
        if not lista:
            continue
        st.markdown(f'<div class="zona-title">{iconos.get(cat, "🍽️")} {cat}</div>', unsafe_allow_html=True)
        cols = st.columns(4)
        for i, p in enumerate(lista):
            opacidad = "1" if p.disponible else "0.4"
            cols[i % 4].markdown(
                f'<div class="card" style="opacity:{opacidad}">'
                f'<div style="display:flex;justify-content:space-between;align-items:baseline">'
                f'<b>{p.nombre}</b><span style="color:#F5A623;font-weight:800">{euros(p.precio)}</span></div>'
                f'<div style="color:#999;font-size:.85rem;margin:.3rem 0">{p.descripcion or ""}</div>'
                f'<div style="font-size:.75rem;color:#777">IVA incl.: {euros(p.precio_iva)} · ⏱️ {p.tiempo_prep} min'
                f'{"" if p.disponible else " · ❌ agotado"}</div></div>', unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    dfp = pd.DataFrame([{"Producto": p.nombre, "Categoría": p.categoria, "Precio": p.precio} for p in productos])
    with c1:
        f = px.box(dfp, x="Categoría", y="Precio", color="Categoría", points="all",
                   title="Distribución de precios por categoría", color_discrete_sequence=PALETA,
                   template=PLOTLY_TEMPLATE)
        f.update_layout(height=380, showlegend=False)
        st.plotly_chart(f, use_container_width=True)
    with c2:
        f = px.treemap(dfp, path=["Categoría", "Producto"], values="Precio", color="Precio",
                       color_continuous_scale="Sunsetdark", title="Mapa de la carta (tamaño = precio)",
                       template=PLOTLY_TEMPLATE)
        f.update_layout(height=380)
        st.plotly_chart(f, use_container_width=True)

# ── Edición en tabla ─────────────────────────────────────────────────────────
with tab_edit:
    st.caption("Edita precios, descripción y disponibilidad directamente en la tabla y pulsa **Guardar cambios**.")
    df_edit = pd.DataFrame([{"id": p.id, "nombre": p.nombre, "categoria": p.categoria, "precio": p.precio,
                             "descripcion": p.descripcion, "tiempo_prep": p.tiempo_prep,
                             "disponible": p.disponible} for p in productos])
    editado = st.data_editor(
        df_edit, hide_index=True, use_container_width=True, disabled=["id"], key="editor_carta",
        column_config={
            "precio": st.column_config.NumberColumn("Precio (€)", min_value=0.0, step=0.5, format="%.2f €"),
            "categoria": st.column_config.SelectboxColumn("Categoría", options=list(cat_id)),
            "disponible": st.column_config.CheckboxColumn("Disponible"),
            "tiempo_prep": st.column_config.NumberColumn("Prep. (min)", min_value=1, max_value=120),
        })
    c1, c2 = st.columns([1, 3])
    subida = c2.slider("📈 Subida/bajada global de precios (%)", -20, 20, 0)
    if c1.button("💾 Guardar cambios", type="primary", use_container_width=True):
        errores, cambios = [], 0
        for fila in editado.to_dict("records"):
            try:
                p = Producto.desde_dict({**fila, "categoria_id": cat_id.get(fila["categoria"], 0)})
                p.precio = float(fila["precio"]) * (1 + subida / 100)   # el setter valida y redondea
                db.execute("""UPDATE productos SET nombre=?, categoria_id=?, precio=?, descripcion=?,
                              tiempo_prep=?, disponible=? WHERE id=?""",
                           (p.nombre.strip(), p.categoria_id, p.precio, p.descripcion,
                            int(p.tiempo_prep), int(bool(fila["disponible"])), p.id))
                cambios += 1
            except (ValueError, TypeError) as e:
                errores.append(f"{fila.get('nombre')}: {e}")
        if errores:
            st.error("No se pudieron guardar:\n\n" + "\n".join(errores))
        st.success(f"✅ {cambios} productos actualizados.")
        st.cache_data.clear()
        st.rerun()

# ── Nuevo producto ───────────────────────────────────────────────────────────
with tab_nuevo:
    with st.form("nuevo_plato", clear_on_submit=True):
        c1, c2, c3 = st.columns([2, 1, 1])
        nombre = c1.text_input("Nombre del plato *")
        categoria = c2.selectbox("Categoría", list(cat_id))
        precio = c3.number_input("Precio (€) *", min_value=0.0, step=0.5, value=10.0)
        descripcion = st.text_area("Descripción", max_chars=200)
        c1, c2 = st.columns(2)
        tiempo = c1.slider("Tiempo de preparación (min)", 1, 60, 12)
        disponible = c2.toggle("Disponible desde hoy", value=True)
        if st.form_submit_button("➕ Añadir a la carta", type="primary"):
            nombre = nombre.strip().title()
            if not nombre:
                st.error("El nombre es obligatorio.")
            elif nombre.lower() in {p.nombre.lower() for p in productos}:
                st.error(f"Ya existe un plato llamado «{nombre}».")
            else:
                db.execute("""INSERT INTO productos (nombre, categoria_id, precio, descripcion, disponible, tiempo_prep)
                              VALUES (?,?,?,?,?,?)""",
                           (nombre, cat_id[categoria], round(precio, 2), descripcion.strip(), int(disponible), tiempo))
                st.success(f"✅ «{nombre}» añadido a {categoria} por {euros(precio)}.")
                st.cache_data.clear()
                st.rerun()

# ── Importar / exportar ─────────────────────────────────────────────────────
with tab_io:
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### ⬇️ Exportar")
        carta = {cat: [{"nombre": p.nombre, "precio": p.precio, "descripcion": p.descripcion,
                        "disponible": p.disponible} for p in productos if p.categoria == cat]
                 for cat in cat_id}
        texto_json = json.dumps(carta, ensure_ascii=False, indent=2)
        st.download_button("📄 Carta en JSON", texto_json.encode("utf-8"), "carta.json",
                           "application/json", use_container_width=True)
        csv = pd.DataFrame([{"nombre": p.nombre, "categoria": p.categoria, "precio": p.precio,
                             "descripcion": p.descripcion, "disponible": int(p.disponible)} for p in productos])
        st.download_button("📊 Carta en CSV", csv.to_csv(index=False, sep=";").encode("utf-8-sig"),
                           "carta.csv", "text/csv", use_container_width=True)
        if st.button("💾 Guardar carta.json en el servidor", use_container_width=True):
            ruta = BASE_DIR / "carta.json"
            with open(ruta, "w", encoding="utf-8") as fh:
                fh.write(texto_json)
            st.success(f"Guardado en `{os.path.basename(ruta)}`")
        with st.expander("👀 Vista previa del JSON"):
            st.json(carta, expanded=False)
    with c2:
        st.markdown("#### ⬆️ Importar CSV")
        st.caption("Columnas: `nombre;categoria;precio;descripcion;disponible`. Los nombres existentes se actualizan.")
        archivo = st.file_uploader("Sube un CSV", type=["csv"])
        if archivo is not None:
            try:
                nuevo = pd.read_csv(io.BytesIO(archivo.getvalue()), sep=None, engine="python")
                faltan = {"nombre", "categoria", "precio"} - set(nuevo.columns)
                if faltan:
                    raise ValueError(f"Faltan columnas: {', '.join(faltan)}")
                st.dataframe(nuevo, use_container_width=True, hide_index=True)
                if st.button("✅ Confirmar importación", type="primary"):
                    existentes = {p.nombre.lower(): p.id for p in productos}
                    ins = upd = 0
                    for r in nuevo.fillna("").to_dict("records"):
                        cid = cat_id.get(str(r["categoria"]).strip())
                        if cid is None:
                            continue
                        valores = (str(r["nombre"]).strip(), cid, float(r["precio"]),
                                   str(r.get("descripcion", "")), int(r.get("disponible", 1) or 1))
                        if valores[0].lower() in existentes:
                            db.execute("""UPDATE productos SET nombre=?, categoria_id=?, precio=?, descripcion=?,
                                          disponible=? WHERE id=?""", (*valores, existentes[valores[0].lower()]))
                            upd += 1
                        else:
                            db.execute("""INSERT INTO productos (nombre, categoria_id, precio, descripcion, disponible)
                                          VALUES (?,?,?,?,?)""", valores)
                            ins += 1
                    st.success(f"Importación completada: {ins} nuevos, {upd} actualizados.")
                    st.cache_data.clear()
            except Exception as e:  # noqa: BLE001 — mostramos cualquier error de formato al usuario
                st.error(f"❌ No se pudo leer el archivo: {e}")
