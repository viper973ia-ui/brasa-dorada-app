"""
Caja — cobro de mesas, división de cuenta, propinas y ticket descargable.
Temas: POO (Pedido.cerrar), cadenas y f-strings, ficheros (descarga de ticket), excepciones.
"""
from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Caja", page_icon="💳", layout="wide")

from seed_data import inicializar
inicializar()
from database import Database
from models import Mesa, Pedido, PedidoError
from styles import aplicar_estilos, euros, kpi, NOMBRE, PLOTLY_TEMPLATE, PALETA

aplicar_estilos("Caja", "Cobra mesas, divide la cuenta y genera el ticket", "💳")
db = Database()


def generar_ticket(pedido: Pedido, propina: float, metodo: str, personas: int) -> str:
    """Construye el ticket como texto plano (manejo de cadenas)."""
    ancho = 40
    lineas = [NOMBRE.center(ancho), "C/ Mayor 12 · Madrid".center(ancho), "CIF B-12345678".center(ancho),
              "-" * ancho, f"Mesa: {pedido.mesa_numero:<6} Comensales: {pedido.num_comensales}",
              f"Fecha: {datetime.now():%d/%m/%Y %H:%M}", f"Pedido: #{pedido.id}", "-" * ancho]
    for l in pedido.lineas:
        nombre = l.producto_nombre[:24]
        lineas.append(f"{l.cantidad:>2} {nombre:<24}{l.subtotal:>10.2f}€")
    lineas += ["-" * ancho,
               f"{'Base imponible':<28}{pedido.subtotal:>10.2f}€",
               f"{'IVA 10%':<28}{pedido.iva:>10.2f}€",
               f"{'TOTAL':<28}{pedido.total:>10.2f}€"]
    if propina:
        lineas.append(f"{'Propina':<28}{propina:>10.2f}€")
    if personas > 1:
        lineas.append(f"{f'Por persona ({personas})':<28}{(pedido.total + propina) / personas:>10.2f}€")
    lineas += [f"Pago: {metodo.upper()}", "-" * ancho, "¡Gracias por su visita!".center(ancho)]
    return "\n".join(lineas)


ocupadas = [m for m in Mesa.todas() if m.estado == "ocupada"]
izq, der = st.columns([1.2, 1])

with izq:
    st.markdown("### 🧾 Mesas pendientes de cobro")
    if not ocupadas:
        st.success("🎉 Todas las mesas están cobradas.")
    else:
        pedidos = [p for p in (Pedido.de_mesa(m.id) for m in ocupadas) if p]
        df = pd.DataFrame([{"Mesa": p.mesa_numero, "Comensales": p.num_comensales,
                            "Platos": sum(l.cantidad for l in p.lineas), "Total (€)": p.total}
                           for p in pedidos])
        st.dataframe(df, hide_index=True, use_container_width=True,
                     column_config={"Total (€)": st.column_config.ProgressColumn(
                         format="%.2f €", min_value=0, max_value=float(df["Total (€)"].max() or 1))})
        pedido = st.selectbox("Mesa a cobrar", pedidos,
                              format_func=lambda p: f"Mesa {p.mesa_numero} · {euros(p.total)}")
        if pedido:
            c = st.columns(3)
            metodo = c[0].radio("Método de pago", ["tarjeta", "efectivo", "bizum"],
                                format_func=lambda x: {"tarjeta": "💳 Tarjeta", "efectivo": "💶 Efectivo",
                                                       "bizum": "📱 Bizum"}[x])
            pct = c[1].select_slider("Propina", [0, 3, 5, 8, 10, 15], value=5, format_func=lambda x: f"{x}%")
            personas = c[2].number_input("Dividir entre", 1, 30, 1)
            propina = round(pedido.total * pct / 100, 2)
            entregado = None
            if metodo == "efectivo":
                entregado = st.number_input("Importe entregado (€)", 0.0, 5000.0,
                                            float(round(pedido.total + propina + 4.99, -1)), step=5.0)
            k = st.columns(3)
            kpi(k[0], "💶", "Total + propina", euros(pedido.total + propina))
            kpi(k[1], "👤", "Por persona", euros((pedido.total + propina) / personas))
            if entregado is not None:
                kpi(k[2], "🔁", "Cambio", euros(max(0, entregado - pedido.total - propina)))
            st.write("")
            if st.button("✅ Cobrar y liberar mesa", type="primary", use_container_width=True):
                try:
                    texto = generar_ticket(pedido, propina, metodo, personas)
                    pedido.cerrar(metodo, propina)
                    st.session_state["ultimo_ticket"] = texto
                    st.cache_data.clear()
                    st.balloons()
                    st.rerun()
                except PedidoError as e:
                    st.error(str(e))
            st.session_state["preview"] = generar_ticket(pedido, propina, metodo, personas)

with der:
    texto = st.session_state.get("ultimo_ticket") or st.session_state.get("preview")
    if texto:
        titulo = "✅ Último ticket cobrado" if st.session_state.get("ultimo_ticket") else "👁️ Vista previa"
        st.markdown(f"### {titulo}")
        st.markdown(f"<div class='ticket'><pre style='margin:0;color:#222;background:none'>{texto}</pre></div>",
                    unsafe_allow_html=True)
        st.download_button("⬇️ Descargar ticket (.txt)", texto, file_name="ticket.txt", use_container_width=True)
        if st.session_state.get("ultimo_ticket") and st.button("Cerrar ticket", use_container_width=True):
            del st.session_state["ultimo_ticket"]
            st.rerun()

# ── Cierre de caja del día ───────────────────────────────────────────────────
st.divider()
st.markdown("### 📊 Cierre de caja · hoy")
hoy = datetime.now().strftime("%Y-%m-%d")
t = pd.DataFrame(db.fetchall("SELECT * FROM transacciones WHERE date(fecha)=?", (hoy,)))
if t.empty:
    ultimo = db.fetchone("SELECT date(MAX(fecha)) d FROM transacciones")["d"]
    st.caption(f"Aún no hay cobros hoy. Mostrando el último día con actividad: {ultimo}")
    t = pd.DataFrame(db.fetchall("SELECT * FROM transacciones WHERE date(fecha)=?", (ultimo,)))
k = st.columns(4)
kpi(k[0], "💰", "Recaudado", euros(t["total"].sum()))
kpi(k[1], "🧾", "Tickets", str(len(t)))
kpi(k[2], "🏛️", "IVA repercutido", euros(t["iva"].sum()))
kpi(k[3], "🙏", "Propinas", euros(t["propina"].sum()))
g = t.groupby("metodo_pago", as_index=False)["total"].sum()
fig = px.pie(g, names="metodo_pago", values="total", hole=.55, color_discrete_sequence=PALETA,
             title="Recaudación por método de pago")
fig.update_layout(template=PLOTLY_TEMPLATE, paper_bgcolor="rgba(0,0,0,0)", height=330)
st.plotly_chart(fig, use_container_width=True)
