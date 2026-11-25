"""
app.py — Página de inicio: panel en tiempo real del restaurante
================================================================
Ejecutar con:  streamlit run app.py

Temas del curso cubiertos en esta página:
  ✔ Streamlit: layout en columnas, métricas, gráficos Plotly (capítulo 17)
  ✔ pandas y fechas
"""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="La Brasa Dorada · Gestión", page_icon="🔥", layout="wide")

# ── Seed automático: si la BD no existe o está vacía, se puebla con datos de prueba
from seed_data import inicializar, necesita_seed  # noqa: E402
if necesita_seed():
    with st.spinner("Preparando la base de datos con datos de prueba (solo la primera vez)..."):
        inicializar()

import analytics as an               # noqa: E402
from styles import aplicar_estilos, kpi, euros, PLOTLY_TEMPLATE  # noqa: E402

aplicar_estilos("La Brasa Dorada", f"Panel de control en vivo · {pd.Timestamp.now():%d/%m/%Y %H:%M}", "🔥")

est = an.estado_actual()
df = an.ventas()

# ── KPIs en vivo ─────────────────────────────────────────────────────────────
c = st.columns(5)
kpi(c[0], "🪑", "Ocupación", f"{est['ocupacion_pct']:.0f}%")
kpi(c[1], "👥", "Comensales ahora", f"{est['comensales']}")
kpi(c[2], "🧾", "Cuentas abiertas", euros(est["importe_abierto"]))
kpi(c[3], "👨‍🍳", "Platos en cocina", f"{est['platos_cocina']}")
kpi(c[4], "📅", "Reservas hoy", f"{est['reservas_hoy']} ({est['personas_reserva']} pax)")

st.write("")
col1, col2, col3 = st.columns([1.1, 1.1, 1.6])

# Gauge de ocupación
with col1:
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=est["ocupacion_pct"], number={"suffix": "%"},
        title={"text": "Ocupación de sala"},
        gauge={"axis": {"range": [0, 100]}, "bar": {"color": "#E94560"},
               "steps": [{"range": [0, 50], "color": "#1e3a2b"},
                         {"range": [50, 80], "color": "#4a3b16"},
                         {"range": [80, 100], "color": "#4a1a22"}]}))
    fig.update_layout(template=PLOTLY_TEMPLATE, height=290, margin=dict(t=60, b=10, l=20, r=20),
                      paper_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig, use_container_width=True)

# Donut de estado de mesas
with col2:
    labels = ["Libres", "Ocupadas", "Reservadas", "Unidas"]
    vals = [est["libres"], est["ocupadas"], est["reservadas"], est["unidas"]]
    fig = go.Figure(go.Pie(labels=labels, values=vals, hole=.62,
                           marker_colors=["#2ecc71", "#e74c3c", "#f39c12", "#3498db"]))
    fig.update_layout(template=PLOTLY_TEMPLATE, height=290, title="Estado de las mesas",
                      margin=dict(t=60, b=10, l=10, r=10), paper_bgcolor="rgba(0,0,0,0)",
                      annotations=[dict(text=f"<b>{est['total_mesas']}</b><br>mesas", showarrow=False, font_size=18)])
    st.plotly_chart(fig, use_container_width=True)

# Ingresos últimos 30 días
with col3:
    s = an.serie_diaria(df[df["fecha_apertura"] >= pd.Timestamp.now() - pd.Timedelta(days=30)])
    fig = go.Figure()
    fig.add_bar(x=s["fecha"], y=s["ingresos"], name="Ingresos", marker_color="#E94560", opacity=.75)
    fig.add_scatter(x=s["fecha"], y=s["media_7d"], name="Media 7 días", line=dict(color="#F5A623", width=3))
    fig.update_layout(template=PLOTLY_TEMPLATE, height=290, title="Ingresos · últimos 30 días",
                      margin=dict(t=60, b=10, l=10, r=10), paper_bgcolor="rgba(0,0,0,0)",
                      legend=dict(orientation="h", y=1.12, x=1, xanchor="right"))
    st.plotly_chart(fig, use_container_width=True)

# ── Accesos rápidos ──────────────────────────────────────────────────────────
st.markdown("### 🚀 Módulos")
mods = [
    ("pages/1_🗺️_Mapa_de_Mesas.py", "🗺️ Mapa de mesas", "Plano interactivo, unir y separar mesas"),
    ("pages/2_🍽️_Pedidos.py", "🍽️ Pedidos", "Comandas por mesa y estado de cocina"),
    ("pages/3_💳_Caja.py", "💳 Caja", "Cobro, ticket y propinas"),
    ("pages/4_📊_Dashboard.py", "📊 Dashboard", "Analítica avanzada de ventas"),
    ("pages/5_📖_Carta.py", "📖 Carta", "Gestión de platos y precios"),
    ("pages/6_📅_Reservas.py", "📅 Reservas", "Agenda y asignación de mesas"),
]
cols = st.columns(3)
for i, (page, titulo, desc) in enumerate(mods):
    with cols[i % 3]:
        st.page_link(page, label=f"**{titulo}** — {desc}", use_container_width=True)

# ── Resumen histórico ────────────────────────────────────────────────────────
st.markdown("### 📈 Histórico acumulado")
h = st.columns(4)
kpi(h[0], "💰", "Facturación total", euros(df["total"].sum()))
kpi(h[1], "🧾", "Pedidos cerrados", f"{len(df):,}".replace(",", "."))
kpi(h[2], "🍽️", "Comensales servidos", f"{df['num_comensales'].sum():,}".replace(",", "."))
kpi(h[3], "🎫", "Ticket medio", euros(df["total"].mean()))
