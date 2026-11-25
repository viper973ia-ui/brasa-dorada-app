"""
Pedidos — toma de comandas por mesa y pantalla de cocina (KDS).
Temas: POO (Pedido, Producto, LineaPedido), listas, lambdas, datetime, Streamlit.
"""
from datetime import datetime

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Pedidos", page_icon="🍽️", layout="wide")

from seed_data import inicializar
inicializar()
from database import Database
from models import Mesa, Pedido, Producto
from styles import aplicar_estilos, euros, kpi

aplicar_estilos("Pedidos y cocina", "Toma comandas, sigue el estado de cada plato y controla la cocina", "🍽️")
db = Database()

ESTADOS = {"pendiente": ("🕒", "#f39c12"), "en_cocina": ("🔥", "#E94560"), "servido": ("✅", "#2ecc71")}
SIGUIENTE = {"pendiente": "en_cocina", "en_cocina": "servido"}

tab_comanda, tab_cocina = st.tabs(["📝 Comandas por mesa", "👨‍🍳 Pantalla de cocina"])

# ═════════════════════════════════════════════════════════════════════════════
def _comandas():
    ocupadas = [m for m in Mesa.todas() if m.estado == "ocupada"]
    if not ocupadas:
        st.info("No hay mesas ocupadas. Abre una mesa desde el **Mapa de mesas**.")
        return

    pedidos = {m.id: Pedido.de_mesa(m.id) for m in ocupadas}
    elegida = st.session_state.get("mesa_pedido", ocupadas[0].id)
    st.markdown("#### Selecciona mesa")
    cols = st.columns(min(len(ocupadas), 8))
    for i, m in enumerate(ocupadas):
        p = pedidos[m.id]
        etiqueta = f"🍽️ Mesa {m.numero}\n{euros(p.total) if p else '—'}"
        if cols[i % len(cols)].button(etiqueta, key=f"m{m.id}", use_container_width=True,
                                      type="primary" if m.id == elegida else "secondary"):
            st.session_state["mesa_pedido"] = m.id
            st.rerun()

    mesa = Mesa.por_id(elegida) if elegida in pedidos else ocupadas[0]
    pedido = pedidos.get(mesa.id)
    if pedido is None:
        st.warning("Esta mesa no tiene pedido abierto.")
        return

    izq, der = st.columns([1.5, 1])

    # ── Carta para añadir ─────────────────────────────────────────────────
    with izq:
        st.markdown(f"### 📖 Carta · Mesa {mesa.numero}")
        productos = [p for p in Producto.todos() if p.disponible]
        cats = list(dict.fromkeys(p.categoria for p in productos))
        busqueda = st.text_input("🔎 Buscar plato", placeholder="p. ej. croquetas")
        tabs = st.tabs(cats)
        for tab, cat in zip(tabs, cats):
            with tab:
                lista = [p for p in productos if p.categoria == cat
                         and busqueda.lower() in p.nombre.lower()]
                grid = st.columns(3)
                for i, p in enumerate(lista):
                    with grid[i % 3]:
                        with st.container(border=True):
                            st.markdown(f"**{p.nombre}**  \n<span style='color:#9aa0b4;font-size:.8rem'>"
                                        f"{p.descripcion}</span>", unsafe_allow_html=True)
                            st.markdown(f"<span style='color:#F5A623;font-weight:700'>{euros(p.precio)}</span>"
                                        f" · ⏱️ {p.tiempo_prep} min", unsafe_allow_html=True)
                            if st.button("➕ Añadir", key=f"add{p.id}", use_container_width=True):
                                pedido.agregar_linea(p, 1)
                                st.toast(f"{p.nombre} añadido a la mesa {mesa.numero}")
                                st.rerun()

    # ── Comanda actual ────────────────────────────────────────────────────
    with der:
        apertura = datetime.strptime(pedido.fecha_apertura[:16], "%Y-%m-%d %H:%M")
        minutos = int((datetime.now() - apertura).total_seconds() // 60)
        st.markdown(f"### 🧾 Comanda #{pedido.id}")
        st.caption(f"👥 {pedido.num_comensales} comensales · ⏱️ abierta hace {minutos} min")
        if not pedido.lineas:
            st.info("Comanda vacía. Añade platos desde la carta.")
        for l in pedido.lineas:
            ic, color = ESTADOS.get(l.estado, ("•", "#999"))
            a, b, c = st.columns([5, 1, 1])
            a.markdown(f"<div class='card' style='padding:8px 12px;margin:0;border-left:4px solid {color}'>"
                       f"{ic} <b>{l.cantidad}×</b> {l.producto_nombre}"
                       f"<span style='float:right'>{euros(l.subtotal)}</span></div>", unsafe_allow_html=True)
            if l.estado in SIGUIENTE and b.button("⏩", key=f"nx{l.id}", help=f"Pasar a {SIGUIENTE[l.estado]}"):
                db.execute("UPDATE lineas_pedido SET estado=? WHERE id=?", (SIGUIENTE[l.estado], l.id))
                st.rerun()
            if c.button("🗑️", key=f"del{l.id}", help="Eliminar"):
                pedido.quitar_linea(l.id)
                st.rerun()
        st.divider()
        k = st.columns(3)
        kpi(k[0], "🧮", "Base", euros(pedido.subtotal))
        kpi(k[1], "🏛️", "IVA 10%", euros(pedido.iva))
        kpi(k[2], "💶", "Total", euros(pedido.total))
        st.write("")
        if st.button("📤 Enviar todo a cocina", use_container_width=True):
            db.execute("UPDATE lineas_pedido SET estado='en_cocina' WHERE pedido_id=? AND estado='pendiente'",
                       (pedido.id,))
            st.toast("Comanda enviada a cocina 🔥")
            st.rerun()
        st.page_link("pages/3_💳_Caja.py", label="💳 Ir a caja para cobrar", use_container_width=True)

with tab_comanda:
    _comandas()

# ═════════════════════════════════════════════════════════════════════════════
with tab_cocina:
    df = pd.DataFrame(db.fetchall("""
        SELECT l.id, l.producto_nombre, l.cantidad, l.estado, p.mesa_numero, p.fecha_apertura,
               pr.tiempo_prep
        FROM lineas_pedido l JOIN pedidos p ON p.id = l.pedido_id
        LEFT JOIN productos pr ON pr.id = l.producto_id
        WHERE p.estado = 'abierto' ORDER BY p.fecha_apertura"""))
    if df.empty:
        st.info("Sin comandas activas.")
    else:
        k = st.columns(3)
        for col, est in zip(k, ESTADOS):
            kpi(col, ESTADOS[est][0], est.replace("_", " ").capitalize(),
                str(int(df.loc[df["estado"] == est, "cantidad"].sum())))
        st.write("")
        cols = st.columns(3)
        for col, est in zip(cols, ESTADOS):
            with col:
                ic, color = ESTADOS[est]
                st.markdown(f"<h4 style='color:{color}'>{ic} {est.replace('_', ' ').upper()}</h4>",
                            unsafe_allow_html=True)
                for _, r in df[df["estado"] == est].iterrows():
                    with st.container(border=True):
                        st.markdown(f"**Mesa {r.mesa_numero}** · {r.cantidad}× {r.producto_nombre}  \n"
                                    f"<span style='color:#9aa0b4'>⏱️ {r.tiempo_prep} min de preparación</span>",
                                    unsafe_allow_html=True)
                        if est in SIGUIENTE and st.button(f"Marcar {SIGUIENTE[est].replace('_', ' ')}",
                                                          key=f"k{r.id}", use_container_width=True):
                            db.execute("UPDATE lineas_pedido SET estado=? WHERE id=?", (SIGUIENTE[est], int(r.id)))
                            st.rerun()
