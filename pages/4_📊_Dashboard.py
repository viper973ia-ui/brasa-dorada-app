"""
Dashboard analítico — el "cuadro de mando" del restaurante.
Temas: pandas (filtros, groupby, pivot, resample), NumPy (polyfit, percentiles),
Polars (ranking y menu engineering), Plotly y matplotlib/seaborn, datetime.
"""
from datetime import timedelta

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import seaborn as sns
import streamlit as st

st.set_page_config(page_title="Dashboard", page_icon="📊", layout="wide")

from seed_data import inicializar
inicializar()
import analytics as an
from styles import aplicar_estilos, euros, kpi, PALETA, PLOTLY_TEMPLATE

aplicar_estilos("Dashboard analítico", "Ventas, ocupación, carta y clientes de un vistazo", "📊")

df_all = an.ventas()
lin_all = an.lineas()
if df_all.empty:
    st.warning("No hay datos de ventas todavía.")
    st.stop()

# ── Filtros en la barra lateral ──────────────────────────────────────────────
fmin, fmax = df_all["fecha_apertura"].min().date(), df_all["fecha_apertura"].max().date()
with st.sidebar:
    st.markdown("### 🎛️ Filtros")
    preset = st.radio("Periodo rápido", ["7 días", "30 días", "90 días", "Todo", "Personalizado"], index=1)
    dias = {"7 días": 7, "30 días": 30, "90 días": 90}.get(preset)
    if preset == "Todo":
        desde, hasta = fmin, fmax
    elif preset == "Personalizado":
        rango = st.date_input("Rango", (fmax - timedelta(days=29), fmax), min_value=fmin, max_value=fmax)
        desde, hasta = (rango if isinstance(rango, (list, tuple)) and len(rango) == 2 else (fmin, fmax))
    else:
        desde, hasta = fmax - timedelta(days=dias - 1), fmax
    zonas = st.multiselect("Zonas", sorted(df_all["zona"].dropna().unique()),
                           default=sorted(df_all["zona"].dropna().unique()))
    servicios = st.multiselect("Servicio", ["Comida", "Cena"], default=["Comida", "Cena"])

# Periodo actual y periodo anterior de la misma duración (para los deltas)
dur = (hasta - desde).days + 1
df = an.filtrar(df_all, desde, hasta)
df_prev = an.filtrar(df_all, desde - timedelta(days=dur), desde - timedelta(days=1))
cond = lambda d: d["zona"].isin(zonas) & d["servicio"].isin(servicios)
df, df_prev = df[cond(df)], df_prev[cond(df_prev)]
lin = an.filtrar(lin_all, desde, hasta)
lin = lin[lin["pedido_id"].isin(df["id"])]

if df.empty:
    st.info("No hay datos para los filtros seleccionados.")
    st.stop()

st.caption(f"📆 {desde:%d/%m/%Y} → {hasta:%d/%m/%Y} · {dur} días · comparado con los {dur} días anteriores")

# ── KPIs ─────────────────────────────────────────────────────────────────────
k = an.kpis(df, df_prev)
a, d = k["actual"], k["delta"]
c = st.columns(6)
kpi(c[0], "💶", "Ingresos", euros(a["ingresos"]), d["ingresos"])
kpi(c[1], "🧾", "Pedidos", f"{a['pedidos']:,}".replace(",", "."), d["pedidos"])
kpi(c[2], "👥", "Comensales", f"{int(a['comensales']):,}".replace(",", "."), d["comensales"])
kpi(c[3], "🎯", "Ticket medio", euros(a["ticket"]), d["ticket"])
kpi(c[4], "🍴", "Gasto / persona", euros(a["ticket_persona"]), d["ticket_persona"])
kpi(c[5], "💝", "Propinas", euros(a["propinas"]), d["propinas"])
st.write("")

tab1, tab2, tab3, tab4, tab5 = st.tabs(["📈 Ventas", "🔥 Ocupación", "🍽️ Carta", "👥 Clientes", "🧪 Matplotlib / Seaborn"])

# ═════════════════════════════ 1. VENTAS ═════════════════════════════════════
with tab1:
    s = an.serie_diaria(df)
    fig = go.Figure()
    fig.add_bar(x=s["fecha"], y=s["ingresos"], name="Ingresos diarios", marker_color=PALETA[0], opacity=0.55)
    fig.add_scatter(x=s["fecha"], y=s["media_7d"], name="Media móvil 7d", line=dict(color=PALETA[1], width=3))
    fig.add_scatter(x=s["fecha"], y=s["tendencia"], name="Tendencia (np.polyfit)",
                    line=dict(color=PALETA[2], dash="dash"))
    fig.update_layout(template=PLOTLY_TEMPLATE, height=420, title="Evolución de ingresos",
                      legend=dict(orientation="h", y=1.1), hovermode="x unified", yaxis_title="€")
    st.plotly_chart(fig, use_container_width=True)

    c1, c2, c3 = st.columns(3)
    with c1:
        z = df.groupby("zona", as_index=False)["total"].sum()
        f = px.pie(z, names="zona", values="total", hole=0.55, title="Ingresos por zona",
                   color_discrete_sequence=PALETA, template=PLOTLY_TEMPLATE)
        f.update_layout(height=360)
        st.plotly_chart(f, use_container_width=True)
    with c2:
        sv = df.groupby(["dia_semana", "servicio"], as_index=False)["total"].sum()
        f = px.bar(sv, x="dia_semana", y="total", color="servicio", barmode="group",
                   category_orders={"dia_semana": an.DIAS_ES}, title="Ingresos por día y servicio",
                   color_discrete_sequence=[PALETA[1], PALETA[3]], template=PLOTLY_TEMPLATE)
        f.update_layout(height=360, xaxis_title="", yaxis_title="€")
        st.plotly_chart(f, use_container_width=True)
    with c3:
        mp = df.groupby("metodo_pago", as_index=False)["total"].sum()
        f = px.pie(mp, names="metodo_pago", values="total", hole=0.55, title="Métodos de pago",
                   color_discrete_sequence=PALETA[2:], template=PLOTLY_TEMPLATE)
        f.update_layout(height=360)
        st.plotly_chart(f, use_container_width=True)

    # Comparativa mensual sobre todo el histórico
    mens = (df_all[cond(df_all)].set_index("fecha_apertura")["total"].resample("MS").sum().reset_index())
    mens["mes"] = mens["fecha_apertura"].dt.month.map(lambda m: an.MESES_ES[m - 1])
    mens["variación %"] = mens["total"].pct_change().mul(100).round(1)
    f = px.bar(mens, x="mes", y="total", text=mens["total"].map(lambda v: f"{v/1000:.1f}k €"),
               title="Ingresos mensuales (histórico completo)", color="total",
               color_continuous_scale="Sunsetdark", template=PLOTLY_TEMPLATE)
    f.update_layout(height=360, coloraxis_showscale=False, xaxis_title="", yaxis_title="€")
    st.plotly_chart(f, use_container_width=True)

# ═════════════════════════════ 2. OCUPACIÓN ══════════════════════════════════
with tab2:
    hm = an.heatmap_ocupacion(df)
    f = px.imshow(hm, text_auto=True, aspect="auto", color_continuous_scale="YlOrRd",
                  labels=dict(x="Hora", y="Día", color="Pedidos/día"),
                  title="🔥 Mapa de calor: pedidos medios por día y hora", template=PLOTLY_TEMPLATE)
    f.update_layout(height=420)
    st.plotly_chart(f, use_container_width=True)

    c1, c2 = st.columns(2)
    with c1:
        f = px.histogram(df, x="duracion_min", nbins=40, color="servicio",
                         color_discrete_sequence=[PALETA[1], PALETA[3]], marginal="box",
                         title="Duración de la mesa (minutos)", template=PLOTLY_TEMPLATE)
        f.update_layout(height=380, barmode="overlay")
        f.update_traces(opacity=0.75)
        st.plotly_chart(f, use_container_width=True)
    with c2:
        mz = df.groupby("mesa_numero").agg(pedidos=("id", "count"), ingresos=("total", "sum"),
                                           zona=("zona", "first")).reset_index()
        f = px.bar(mz.sort_values("ingresos", ascending=False), x="mesa_numero", y="ingresos", color="zona",
                   title="Ingresos por mesa", color_discrete_sequence=PALETA, template=PLOTLY_TEMPLATE)
        f.update_layout(height=380, xaxis_title="Mesa", xaxis_type="category")
        st.plotly_chart(f, use_container_width=True)

    tam = df["num_comensales"].value_counts().sort_index().reset_index()
    tam.columns = ["comensales", "pedidos"]
    f = px.funnel(tam.sort_values("pedidos", ascending=False), x="pedidos", y="comensales",
                  title="Tamaño de los grupos (nº de comensales por mesa)",
                  color_discrete_sequence=[PALETA[4]], template=PLOTLY_TEMPLATE)
    f.update_layout(height=380)
    st.plotly_chart(f, use_container_width=True)

# ═════════════════════════════ 3. CARTA ══════════════════════════════════════
with tab3:
    c1, c2 = st.columns([3, 2])
    with c1:
        rk = an.ranking_productos(lin, top=12)
        f = px.bar(rk.sort_values("ingresos"), x="ingresos", y="producto_nombre", color="categoria",
                   orientation="h", text="unidades", title="🏆 Top 12 platos por ingresos (calculado con Polars)",
                   color_discrete_sequence=PALETA, template=PLOTLY_TEMPLATE)
        f.update_layout(height=480, yaxis_title="", xaxis_title="€")
        st.plotly_chart(f, use_container_width=True)
    with c2:
        tm = lin.groupby(["categoria", "producto_nombre"], as_index=False)["subtotal"].sum()
        f = px.sunburst(tm, path=["categoria", "producto_nombre"], values="subtotal",
                        color_discrete_sequence=PALETA, title="Peso de cada categoría y plato",
                        template=PLOTLY_TEMPLATE)
        f.update_layout(height=480)
        st.plotly_chart(f, use_container_width=True)

    mm = an.matriz_menu(lin)
    if not mm.empty:
        colores = {"⭐ Estrella": "#F5A623", "🐄 Vaca lechera": "#2ECC71", "🧩 Puzzle": "#3498DB", "🐶 Perro": "#E94560"}
        f = px.scatter(mm, x="unidades", y="precio_medio", size="ingresos", color="clase",
                       text="producto_nombre", color_discrete_map=colores, size_max=55,
                       title="🧭 Ingeniería de menú: popularidad vs. precio", template=PLOTLY_TEMPLATE)
        f.add_vline(x=np.median(mm["unidades"]), line_dash="dot", line_color="#888")
        f.add_hline(y=np.median(mm["precio_medio"]), line_dash="dot", line_color="#888")
        f.update_traces(textposition="top center", textfont_size=10)
        f.update_layout(height=560, xaxis_title="Unidades vendidas", yaxis_title="Precio medio (€)")
        st.plotly_chart(f, use_container_width=True)
        st.caption("⭐ Estrella: popular y rentable · 🐄 Vaca: popular pero barato · "
                   "🧩 Puzzle: rentable pero poco pedido · 🐶 Perro: candidato a salir de la carta")

# ═════════════════════════════ 4. CLIENTES ═══════════════════════════════════
with tab4:
    tp = df["ticket_persona"].to_numpy()
    p25, p50, p75, p90 = np.percentile(tp, [25, 50, 75, 90])
    c = st.columns(4)
    kpi(c[0], "📉", "Percentil 25", euros(p25))
    kpi(c[1], "⚖️", "Mediana", euros(p50))
    kpi(c[2], "📈", "Percentil 75", euros(p75))
    kpi(c[3], "💎", "Percentil 90", euros(p90))
    st.write("")
    c1, c2 = st.columns(2)
    with c1:
        f = px.violin(df, y="ticket_persona", x="zona", color="zona", box=True, points=False,
                      title="Gasto por persona según zona", color_discrete_sequence=PALETA,
                      template=PLOTLY_TEMPLATE)
        f.update_layout(height=420, showlegend=False, yaxis_title="€ / persona")
        st.plotly_chart(f, use_container_width=True)
    with c2:
        muestra = df.sample(min(len(df), 1500), random_state=1)
        f = px.scatter(muestra, x="num_comensales", y="total", color="servicio", opacity=0.55, title="Comensales vs. importe del ticket",
                       color_discrete_sequence=[PALETA[1], PALETA[3]], template=PLOTLY_TEMPLATE)
        f.update_layout(height=420, xaxis_title="Comensales", yaxis_title="Total (€)")
        st.plotly_chart(f, use_container_width=True)

    pr = df.assign(pct_propina=lambda d: np.where(d["total"] > 0, d["propina"] / d["total"] * 100, 0))
    pz = pr.groupby("metodo_pago", as_index=False)["pct_propina"].mean().round(2)
    f = px.bar(pz, x="metodo_pago", y="pct_propina", text="pct_propina", color="metodo_pago",
               title="Propina media (% sobre la cuenta) por método de pago",
               color_discrete_sequence=PALETA[3:], template=PLOTLY_TEMPLATE)
    f.update_layout(height=340, showlegend=False, yaxis_title="%")
    st.plotly_chart(f, use_container_width=True)

# ═════════════════════════════ 5. MATPLOTLIB ═════════════════════════════════
with tab5:
    st.markdown("Gráficos estáticos generados con **matplotlib** y **seaborn** (capítulo 16), "
                "con estilo oscuro a juego con la app.")
    plt.style.use("dark_background")
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.patch.set_facecolor("#0E1117")

    # a) Ventas por categoría y día (barras apiladas)
    lc = lin.merge(df[["id", "dia_semana"]], left_on="pedido_id", right_on="id")
    pv = lc.pivot_table(index="dia_semana", columns="categoria", values="subtotal", aggfunc="sum").fillna(0)
    pv = pv.reindex([x for x in an.DIAS_ES if x in pv.index])
    pv.plot(kind="bar", stacked=True, ax=axes[0], color=PALETA[:pv.shape[1]], width=0.75)
    axes[0].set_title("Ventas por categoría y día", fontsize=13, weight="bold")
    axes[0].set_xlabel("")
    axes[0].set_ylabel("€")
    axes[0].tick_params(axis="x", rotation=0)
    axes[0].legend(frameon=False, fontsize=9)

    # b) Distribución del ticket (seaborn KDE por servicio)
    sns.kdeplot(data=df, x="ticket_persona", hue="servicio", fill=True, ax=axes[1],
                palette=[PALETA[1], PALETA[3]], alpha=0.45, linewidth=2)
    axes[1].axvline(p50, color=PALETA[0], ls="--", lw=1.5, label=f"Mediana {p50:.1f} €")
    axes[1].set_title("Densidad del gasto por persona", fontsize=13, weight="bold")
    axes[1].set_xlabel("€ por persona")
    for ax in axes:
        ax.set_facecolor("#0E1117")
        ax.spines[["top", "right"]].set_visible(False)
    plt.tight_layout()
    st.pyplot(fig)
    plt.close(fig)

    # c) Heatmap de seaborn: correlaciones entre variables numéricas
    fig2, ax2 = plt.subplots(figsize=(8, 5))
    fig2.patch.set_facecolor("#0E1117")
    corr = df[["num_comensales", "total", "propina", "duracion_min", "ticket_persona", "hora"]].corr()
    sns.heatmap(corr, annot=True, fmt=".2f", cmap="rocket", ax=ax2, linewidths=0.5, cbar_kws={"shrink": 0.8})
    ax2.set_title("Matriz de correlación (seaborn)", fontsize=13, weight="bold")
    c1, c2 = st.columns([3, 2])
    c1.pyplot(fig2)
    plt.close(fig2)
    with c2:
        st.markdown("#### 📋 Resumen estadístico")
        st.dataframe(df[["total", "ticket_persona", "duracion_min", "propina"]].describe().round(2),
                     use_container_width=True)

# ── Exportación ──────────────────────────────────────────────────────────────
st.divider()
c1, c2 = st.columns([1, 3])
c1.download_button("⬇️ Exportar ventas filtradas (CSV)",
                   df.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig"),
                   file_name=f"ventas_{desde}_{hasta}.csv", mime="text/csv", use_container_width=True)
c2.caption(f"{len(df):,} pedidos en el periodo · los datos se leen de SQLite y se cachean 60 s".replace(",", "."))
