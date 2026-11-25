"""
Reservas — agenda, alta con validación y asignación inteligente de mesas.
Temas: datetime (fechas, horas, timedelta), cadenas (validación de email/teléfono),
diccionarios, excepciones, POO (GestorMesas.sugerir), pandas + Plotly.
"""
from datetime import date, datetime, time, timedelta

import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Reservas", page_icon="📅", layout="wide")

from seed_data import inicializar
inicializar()
from database import Database
from gestor_mesas import GestorMesas
from models import Mesa, MesaError
from styles import aplicar_estilos, kpi, PALETA, PLOTLY_TEMPLATE

aplicar_estilos("Reservas", "Agenda, nuevas reservas y asignación automática de mesas", "📅")
db, gestor = Database(), GestorMesas()

ESTADOS = {"confirmada": "🟢", "sentada": "🍽️", "completada": "✅", "cancelada": "❌", "no_show": "👻"}
HORAS = [time(h, m) for h in list(range(13, 16)) + list(range(20, 23)) for m in (0, 30)]


# ── Validaciones con métodos de cadena (sin regex, como en el capítulo 9) ─────
def email_valido(email: str) -> bool:
    email = email.strip()
    if not email:
        return True  # opcional
    if email.count("@") != 1 or " " in email:
        return False
    usuario, dominio = email.split("@")
    return bool(usuario) and "." in dominio and not dominio.startswith(".") and not dominio.endswith(".")


def telefono_valido(tel: str) -> bool:
    limpio = tel.replace(" ", "").replace("-", "").removeprefix("+34")
    return limpio.isdigit() and len(limpio) == 9 and limpio[0] in "6789"


def cargar_reservas() -> pd.DataFrame:
    df = pd.DataFrame(db.fetchall("""
        SELECT r.*, m.numero AS mesa_numero, m.zona FROM reservas r
        LEFT JOIN mesas m ON m.id = r.mesa_id ORDER BY r.fecha, r.hora"""))
    if not df.empty:
        df["fecha_dt"] = pd.to_datetime(df["fecha"])
    return df


df = cargar_reservas()
hoy = date.today()
hoy_s = hoy.isoformat()

# ── KPIs ─────────────────────────────────────────────────────────────────────
d_hoy = df[(df["fecha"] == hoy_s) & (df["estado"] == "confirmada")] if not df.empty else df
prox = df[(df["fecha_dt"].dt.date > hoy) & (df["estado"] == "confirmada")] if not df.empty else df
pasadas = df[df["fecha_dt"].dt.date < hoy] if not df.empty else df
tasa_ns = (pasadas["estado"].eq("no_show").mean() * 100) if len(pasadas) else 0
c = st.columns(5)
kpi(c[0], "📅", "Reservas hoy", str(len(d_hoy)))
kpi(c[1], "👥", "Personas hoy", str(int(d_hoy["num_personas"].sum()) if len(d_hoy) else 0))
kpi(c[2], "🔜", "Próximas", str(len(prox)))
kpi(c[3], "🧑‍🤝‍🧑", "Media personas", f"{df['num_personas'].mean():.1f}" if len(df) else "0")
kpi(c[4], "👻", "Tasa no-show", f"{tasa_ns:.1f} %")
st.write("")

tab_agenda, tab_nueva, tab_stats = st.tabs(["🗓️ Agenda", "➕ Nueva reserva", "📊 Estadísticas"])

# ═════════════════════════════ AGENDA ════════════════════════════════════════
with tab_agenda:
    c1, c2 = st.columns([1, 3])
    dia = c1.date_input("Día", hoy, format="DD/MM/YYYY")
    nombres_dias = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
    c2.markdown(f"### {nombres_dias[dia.weekday()].capitalize()}, {dia:%d/%m/%Y}"
                + ("  ·  🔒 Cerrado por descanso" if dia.weekday() == 0 else ""))
    del_dia = df[df["fecha"] == dia.isoformat()] if not df.empty else df
    if del_dia.empty:
        st.info("No hay reservas para este día.")
    else:
        for servicio, rango in {"☀️ Comida": ("13:00", "16:59"), "🌙 Cena": ("20:00", "23:59")}.items():
            bloque = del_dia[(del_dia["hora"] >= rango[0]) & (del_dia["hora"] <= rango[1])]
            if bloque.empty:
                continue
            st.markdown(f'<div class="zona-title">{servicio} · {int(bloque["num_personas"].sum())} personas</div>',
                        unsafe_allow_html=True)
            for r in bloque.to_dict("records"):
                col = st.columns([1, 3, 1.3, 1.3, 2, 1.4])
                col[0].markdown(f"**{r['hora']}**")
                col[1].markdown(f"{ESTADOS.get(r['estado'], '•')} **{r['nombre']}**  \n"
                                f"<span style='color:#888;font-size:.8rem'>📞 {r['telefono'] or '—'} · "
                                f"{r['notas'] or ''}</span>", unsafe_allow_html=True)
                col[2].markdown(f"👥 {r['num_personas']} pax")
                mesa_txt = f"Mesa {int(r['mesa_numero'])} · {r['zona']}" if pd.notna(r["mesa_numero"]) else "Sin mesa"
                col[3].markdown(f"🪑 {mesa_txt}")
                nuevo = col[4].selectbox("Estado", list(ESTADOS), index=list(ESTADOS).index(r["estado"])
                                         if r["estado"] in ESTADOS else 0, key=f"est_{r['id']}",
                                         label_visibility="collapsed",
                                         format_func=lambda e: f"{ESTADOS[e]} {e.replace('_', ' ')}")
                if nuevo != r["estado"]:
                    db.execute("UPDATE reservas SET estado=? WHERE id=?", (nuevo, r["id"]))
                    # Si la reserva es de hoy, sincronizamos el estado de la mesa
                    if r["fecha"] == hoy_s and pd.notna(r["mesa_id"]):
                        mesa = Mesa.por_id(int(r["mesa_id"]))
                        try:
                            if nuevo == "confirmada" and mesa.esta_libre:
                                mesa.estado = "reservada"; mesa.guardar()
                            elif nuevo in ("cancelada", "no_show") and mesa.estado == "reservada":
                                mesa.estado = "libre"; mesa.guardar()
                        except (MesaError, ValueError) as e:
                            st.warning(str(e))
                    st.rerun()
                if r["estado"] == "confirmada" and r["fecha"] == hoy_s and pd.notna(r["mesa_id"]):
                    if col[5].button("🔒 Bloquear mesa", key=f"blq_{r['id']}", use_container_width=True):
                        mesa = Mesa.por_id(int(r["mesa_id"]))
                        if mesa and mesa.esta_libre:
                            mesa.estado = "reservada"; mesa.guardar()
                            st.toast(f"Mesa {mesa.numero} marcada como reservada")
                            st.rerun()
                        else:
                            st.toast("La mesa no está libre ahora mismo")

# ═════════════════════════════ NUEVA RESERVA ═════════════════════════════════
with tab_nueva:
    c1, c2 = st.columns([3, 2])
    with c1:
        with st.form("form_reserva"):
            a, b = st.columns(2)
            nombre = a.text_input("Nombre del cliente *")
            telefono = b.text_input("Teléfono *", placeholder="600 123 456")
            email = a.text_input("Email", placeholder="cliente@correo.com")
            personas = b.number_input("Nº de personas *", 1, 30, 4)
            a, b, z = st.columns(3)
            fecha = a.date_input("Fecha *", hoy + timedelta(days=1), min_value=hoy, format="DD/MM/YYYY")
            hora = b.selectbox("Hora *", HORAS, format_func=lambda t: t.strftime("%H:%M"), index=7)
            zona = z.selectbox("Zona preferida", ["Cualquiera", "Salón", "Terraza", "Reservado"])
            notas = st.text_input("Notas (alergias, celebración, trona…)")
            auto = st.toggle("🤖 Asignar mesa automáticamente (une mesas si hace falta)", value=True)
            enviar = st.form_submit_button("📅 Confirmar reserva", type="primary")

        if enviar:
            errores = []
            if len(nombre.strip()) < 2:
                errores.append("Indica el nombre del cliente.")
            if not telefono_valido(telefono):
                errores.append("Teléfono no válido (9 dígitos, empieza por 6, 7, 8 o 9).")
            if not email_valido(email):
                errores.append("Email no válido.")
            if fecha.weekday() == 0:
                errores.append("Los lunes el restaurante está cerrado.")
            if errores:
                for e in errores:
                    st.error(e)
            else:
                mesa_id, info = None, "sin mesa asignada"
                if auto:
                    # Mesas ya comprometidas en esa fecha y franja (±2h)
                    hh = hora.hour
                    ocupadas = {r["mesa_id"] for r in db.fetchall(
                        "SELECT mesa_id, hora FROM reservas WHERE fecha=? AND estado='confirmada' AND mesa_id IS NOT NULL",
                        (fecha.isoformat(),)) if abs(int(r["hora"][:2]) - hh) < 2}
                    candidatas = [m for m in gestor.mesas() if m.zona != "Barra" and m.id not in ocupadas
                                  and (zona == "Cualquiera" or m.zona == zona)]
                    # Elegimos la mesa individual que mejor encaje; si no, una combinación
                    simples = sorted([m for m in candidatas if m.capacidad >= personas], key=lambda m: m.capacidad)
                    if simples:
                        mesa_id, info = simples[0].id, f"mesa {simples[0].numero} ({simples[0].zona}, {simples[0].capacidad} plazas)"
                    else:
                        from itertools import combinations
                        mejor = None
                        for zn in {m.zona for m in candidatas}:
                            zm = [m for m in candidatas if m.zona == zn]
                            for k in range(2, 5):
                                for combo in combinations(zm, k):
                                    cap = sum(m.capacidad for m in combo)
                                    if cap >= personas and (mejor is None or (cap - personas, k) <
                                                            (sum(x.capacidad for x in mejor) - personas, len(mejor))):
                                        mejor = combo
                        if mejor:
                            principal = min(mejor, key=lambda m: m.numero)
                            mesa_id = principal.id
                            info = ("mesas " + " + ".join(str(m.numero) for m in sorted(mejor, key=lambda m: m.numero))
                                    + f" unidas ({sum(m.capacidad for m in mejor)} plazas) — se unirán al llegar")
                db.execute("""INSERT INTO reservas (nombre, email, telefono, fecha, hora, num_personas, mesa_id, estado, notas)
                              VALUES (?,?,?,?,?,?,?,'confirmada',?)""",
                           (nombre.strip().title(), email.strip().lower(), telefono.strip(), fecha.isoformat(),
                            hora.strftime("%H:%M"), int(personas), mesa_id,
                            (notas.strip() + (" · " if notas.strip() else "") + info) if "unidas" in info else notas.strip()))
                st.success(f"✅ Reserva confirmada para **{nombre.strip().title()}** el {fecha:%d/%m/%Y} a las "
                           f"{hora:%H:%M} · {personas} personas · {info}.")
                st.balloons()
    with c2:
        st.markdown("#### 🤖 Simulador de asignación")
        st.caption("¿Cabe ahora mismo un grupo? Prueba el algoritmo de unión de mesas con las mesas libres actuales.")
        n = st.slider("Comensales", 1, 24, 10)
        zn = st.selectbox("Zona", ["Cualquiera", "Salón", "Terraza", "Reservado", "Barra"], key="zona_sim")
        sug = gestor.sugerir(n, None if zn == "Cualquiera" else zn)
        if sug:
            cap = sum(m.capacidad for m in sug)
            st.success(f"**{len(sug)} mesa(s):** " + " + ".join(f"#{m.numero}" for m in sug)
                       + f" · {sug[0].zona} · {cap} plazas ({cap - n} libres)")
            st.markdown("".join(f'<span class="badge">🪑 Mesa {m.numero} · {m.capacidad} pax</span> ' for m in sug),
                        unsafe_allow_html=True)
        else:
            st.error("No hay combinación de mesas libres que acomode al grupo ahora mismo.")

# ═════════════════════════════ ESTADÍSTICAS ══════════════════════════════════
with tab_stats:
    if df.empty:
        st.info("Sin datos.")
    else:
        por_dia = df.groupby(["fecha_dt", "estado"], as_index=False)["num_personas"].sum()
        f = px.bar(por_dia, x="fecha_dt", y="num_personas", color="estado",
                   color_discrete_map={"confirmada": "#2ECC71", "completada": "#3498DB", "cancelada": "#E94560",
                                       "no_show": "#9B59B6", "sentada": "#F5A623"},
                   title="Personas reservadas por día", template=PLOTLY_TEMPLATE)
        f.add_vline(x=pd.Timestamp(hoy).timestamp() * 1000, line_dash="dash", line_color="#F5A623",
                    annotation_text="Hoy")
        f.update_layout(height=400, xaxis_title="", yaxis_title="Personas")
        st.plotly_chart(f, use_container_width=True)
        c1, c2 = st.columns(2)
        with c1:
            h = df.groupby("hora", as_index=False).size()
            f = px.bar(h, x="hora", y="size", title="Horas más solicitadas", color="size",
                       color_continuous_scale="Sunsetdark", template=PLOTLY_TEMPLATE)
            f.update_layout(height=360, coloraxis_showscale=False, yaxis_title="Reservas")
            st.plotly_chart(f, use_container_width=True)
        with c2:
            e = df["estado"].value_counts().reset_index()
            e.columns = ["estado", "n"]
            f = px.pie(e, names="estado", values="n", hole=0.55, title="Estado de las reservas",
                       color_discrete_sequence=PALETA, template=PLOTLY_TEMPLATE)
            f.update_layout(height=360)
            st.plotly_chart(f, use_container_width=True)
        st.dataframe(df[["fecha", "hora", "nombre", "telefono", "num_personas", "mesa_numero", "zona", "estado"]]
                     .sort_values(["fecha", "hora"], ascending=False), hide_index=True, use_container_width=True)
