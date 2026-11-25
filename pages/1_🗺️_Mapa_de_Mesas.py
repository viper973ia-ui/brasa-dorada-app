"""
Mapa de mesas — plano visual del restaurante con unión/separación de mesas.
Temas: POO (Mesa, GestorMesas), diccionarios/conjuntos, excepciones, Streamlit, Plotly.
"""
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="Mapa de mesas", page_icon="🗺️", layout="wide")

from seed_data import inicializar
inicializar()
from gestor_mesas import GestorMesas
from models import Mesa, MesaError, Pedido, PedidoError
from styles import aplicar_estilos, mesa_html, kpi, PLOTLY_TEMPLATE

aplicar_estilos("Mapa de mesas", "Plano en vivo · une mesas para grupos grandes y sepáralas al terminar", "🗺️")

gestor = GestorMesas()
mesas = gestor.mesas()
grupos = gestor.grupos()
por_id = {m.id: m for m in mesas}

# ── Leyenda y KPIs ───────────────────────────────────────────────────────────
c = st.columns(5)
for col, (est, ic) in zip(c, Mesa.ICONOS.items()):
    kpi(col, ic, est.capitalize(), str(sum(1 for m in mesas if m.estado == est)))
kpi(c[4], "🔗", "Grupos unidos", str(len(grupos)))

zonas = sorted({m.zona for m in mesas}, key=["Salón", "Terraza", "Reservado", "Barra"].index)
vista = st.radio("Vista", ["🎨 Plano visual", "🛰️ Plano Plotly"], horizontal=True, label_visibility="collapsed")

# ── Plano ────────────────────────────────────────────────────────────────────
if vista == "🎨 Plano visual":
    for zona in zonas:
        st.markdown(f'<div class="zona-title">📍 {zona}</div>', unsafe_allow_html=True)
        mz = sorted([m for m in mesas if m.zona == zona], key=lambda m: (m.pos_y, m.pos_x))
        cols = st.columns(4)
        for m in mz:
            cap_g = gestor.capacidad_grupo(m.grupo_id) if (m.grupo_id == m.id) else None
            etiqueta = f"↪ unida a {por_id[m.grupo_id].numero}" if m.estado == "unida" else ""
            cols[m.pos_x % 4].markdown(
                mesa_html(m.numero, m.estado, m.capacidad, cap_g, etiqueta, bool(m.grupo_id)),
                unsafe_allow_html=True)
            cols[m.pos_x % 4].write("")
else:
    fig = go.Figure()
    offset_x = {"Salón": 0, "Terraza": 5.5, "Reservado": 0, "Barra": 5.5}
    offset_y = {"Salón": 0, "Terraza": 0, "Reservado": 4.2, "Barra": 4.2}
    for zona in zonas:
        ox, oy = offset_x[zona], offset_y[zona]
        fig.add_shape(type="rect", x0=ox - .6, y0=-(oy - .6), x1=ox + 3.6, y1=-(oy + 2.9),
                      line=dict(color="#F5A623", dash="dot"), fillcolor="rgba(255,255,255,0.02)")
        fig.add_annotation(x=ox + 1.5, y=-(oy - .9), text=f"<b>{zona}</b>", showarrow=False,
                           font=dict(color="#F5A623", size=15))
    # líneas de unión entre mesas del mismo grupo
    for gid, ms in grupos.items():
        ms = sorted(ms, key=lambda m: m.numero)
        for a, b in zip(ms, ms[1:]):
            fig.add_scatter(x=[offset_x[a.zona] + a.pos_x, offset_x[b.zona] + b.pos_x],
                            y=[-(offset_y[a.zona] + a.pos_y), -(offset_y[b.zona] + b.pos_y)],
                            mode="lines", line=dict(color="#F5A623", width=8), showlegend=False, hoverinfo="skip")
    for est, color in Mesa.COLORES.items():
        sub = [m for m in mesas if m.estado == est]
        if not sub:
            continue
        fig.add_scatter(
            x=[offset_x[m.zona] + m.pos_x for m in sub], y=[-(offset_y[m.zona] + m.pos_y) for m in sub],
            mode="markers+text", name=est.capitalize(), text=[str(m.numero) for m in sub],
            textfont=dict(color="white", size=14), marker_symbol=["square" if m.capacidad >= 4 else "circle" for m in sub],
            marker=dict(size=[24 + m.capacidad * 6 for m in sub], color=color, line=dict(color="white", width=2)),
            customdata=[[m.capacidad, gestor.capacidad_efectiva(m)] for m in sub],
            hovertemplate="Mesa %{text}<br>Plazas: %{customdata[0]}<br>Capacidad efectiva: %{customdata[1]}<extra></extra>")
    fig.update_layout(template=PLOTLY_TEMPLATE, height=620, paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="rgba(0,0,0,0)", xaxis=dict(visible=False), yaxis=dict(visible=False),
                      legend=dict(orientation="h", y=1.05), margin=dict(l=10, r=10, t=30, b=10))
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# ── Operaciones ──────────────────────────────────────────────────────────────
t1, t2, t3, t4 = st.tabs(["🤖 Asistente de asignación", "🔗 Unir mesas", "✂️ Separar mesas", "🚪 Abrir mesa"])

with t1:
    st.markdown("Indica cuántos comensales llegan y el sistema busca la **combinación óptima** "
                "de mesas libres (mínimo de sillas vacías y de mesas a mover).")
    a, b, c_ = st.columns([1, 1, 1])
    n = a.number_input("Comensales", 1, 30, 6)
    zona = b.selectbox("Zona preferida", ["Cualquiera"] + zonas)
    if c_.button("🔍 Buscar mesas", use_container_width=True, type="primary"):
        st.session_state["sugerencia"] = gestor.sugerir(n, None if zona == "Cualquiera" else zona)
        st.session_state["sug_n"] = n
    sug = st.session_state.get("sugerencia")
    if "sugerencia" in st.session_state:
        if not sug:
            st.error("😕 No hay combinación de mesas libres que acomode a ese grupo.")
        else:
            cap = sum(m.capacidad for m in sug)
            st.success(f"✅ Propuesta: mesas **{', '.join(str(m.numero) for m in sug)}** "
                       f"({sug[0].zona}) → {cap} plazas para {st.session_state['sug_n']} comensales "
                       f"({cap - st.session_state['sug_n']} sillas libres).")
            cols = st.columns(max(len(sug), 4))
            for col, m in zip(cols, sug):
                col.markdown(mesa_html(m.numero, "libre", m.capacidad), unsafe_allow_html=True)
            if st.button("🔗 Aplicar propuesta y abrir mesa", type="primary"):
                try:
                    principal_id = sug[0].id if len(sug) == 1 else gestor.unir([m.id for m in sug])
                    Pedido.crear(Mesa.por_id(principal_id), st.session_state["sug_n"])
                    del st.session_state["sugerencia"]
                    st.toast("Mesa abierta 🎉")
                    st.rerun()
                except (MesaError, PedidoError) as e:
                    st.error(str(e))

with t2:
    libres = [m for m in mesas if m.estado == "libre" and not m.grupo_id]
    sel = st.multiselect("Mesas libres a unir (misma zona)", libres,
                         format_func=lambda m: f"Mesa {m.numero} · {m.zona} · {m.capacidad} plazas")
    if sel:
        st.info(f"Capacidad resultante: **{sum(m.capacidad for m in sel)} plazas** 🪑")
    if st.button("🔗 Unir mesas seleccionadas", type="primary"):
        try:
            pid = gestor.unir([m.id for m in sel])
            st.toast(f"Mesas unidas. Principal: mesa {por_id[pid].numero}")
            st.rerun()
        except MesaError as e:
            st.error(str(e))

with t3:
    if not grupos:
        st.info("No hay mesas unidas ahora mismo.")
    for gid, ms in grupos.items():
        a, b = st.columns([4, 1])
        a.markdown(f"**Grupo de la mesa {por_id[gid].numero}** → mesas "
                   f"{', '.join(str(m.numero) for m in sorted(ms, key=lambda x: x.numero))} · "
                   f"{sum(m.capacidad for m in ms)} plazas · estado: {por_id[gid].estado}")
        if b.button("✂️ Separar", key=f"sep{gid}"):
            try:
                gestor.separar(gid)
                st.toast("Mesas separadas")
                st.rerun()
            except MesaError as e:
                st.error(str(e))

with t4:
    abribles = [m for m in mesas if m.estado in ("libre", "reservada")]
    a, b, c_ = st.columns([2, 1, 1])
    m = a.selectbox("Mesa", abribles, format_func=lambda m: f"Mesa {m.numero} · {m.zona} · "
                    f"{gestor.capacidad_efectiva(m)} plazas{' (grupo)' if m.grupo_id else ''} · {m.estado}")
    n = b.number_input("Comensales ", 1, 30, 2)
    if c_.button("🚪 Abrir", type="primary", use_container_width=True) and m:
        if n > gestor.capacidad_efectiva(m):
            st.warning(f"⚠️ La mesa {m.numero} solo tiene {gestor.capacidad_efectiva(m)} plazas. "
                       "Usa el asistente o une mesas.")
        else:
            try:
                Pedido.crear(m, n)
                st.toast(f"Mesa {m.numero} abierta")
                st.rerun()
            except PedidoError as e:
                st.error(str(e))
