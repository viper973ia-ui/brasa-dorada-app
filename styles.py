"""
styles.py — Estilos CSS y componentes visuales reutilizables
=============================================================
Temas del curso: funciones, cadenas f-string, Streamlit (st.markdown con HTML).
"""
import streamlit as st

NOMBRE = "La Brasa Dorada"
PALETA = ["#E94560", "#F5A623", "#2ECC71", "#3498DB", "#9B59B6", "#1ABC9C", "#E67E22", "#ECF0F1"]
PLOTLY_TEMPLATE = "plotly_dark"

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;800&display=swap');
html, body, [class*="css"] { font-family: 'Poppins', sans-serif; }
.block-container { padding-top: 1.5rem; max-width: 1400px; }

.hero {
  background: linear-gradient(135deg, #1a1f2e 0%, #2d1b3d 50%, #E94560 160%);
  border-radius: 22px; padding: 28px 36px; margin-bottom: 22px;
  border: 1px solid rgba(233,69,96,.35); box-shadow: 0 10px 40px rgba(233,69,96,.15);
}
.hero h1 { margin: 0; font-size: 2.3rem; font-weight: 800;
  background: linear-gradient(90deg,#fff,#F5A623); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
.hero p { margin: 6px 0 0; color: #c9cbd6; font-size: 1.02rem; }

.kpi {
  background: linear-gradient(160deg, #1d2333, #161a26);
  border-radius: 18px; padding: 18px 20px; border: 1px solid #2a3145;
  box-shadow: 0 6px 20px rgba(0,0,0,.35); transition: transform .2s, border-color .2s; height: 100%;
}
.kpi:hover { transform: translateY(-4px); border-color: #E94560; }
.kpi .ic { font-size: 1.6rem; }
.kpi .lb { color: #9aa0b4; font-size: .82rem; text-transform: uppercase; letter-spacing: 1px; margin-top: 4px; }
.kpi .vl { font-size: clamp(1.1rem, 1.6vw, 1.85rem); white-space: nowrap; font-weight: 800; color: #fff; line-height: 1.2; }
.kpi .dl { font-size: .85rem; font-weight: 600; }
.up { color: #2ECC71; } .down { color: #E94560; }

.mesa {
  border-radius: 18px; padding: 14px 8px; text-align: center; color: #fff;
  font-weight: 600; border: 2px solid rgba(255,255,255,.08); min-height: 118px;
  box-shadow: 0 6px 18px rgba(0,0,0,.4); position: relative; transition: transform .15s;
}
.mesa:hover { transform: scale(1.04); }
.mesa .num { font-size: 1.6rem; font-weight: 800; }
.mesa .cap { font-size: .8rem; opacity: .9; }
.mesa .sillas { letter-spacing: 2px; font-size: .75rem; }
.mesa .tag { font-size: .7rem; background: rgba(0,0,0,.28); border-radius: 10px; padding: 2px 8px; display:inline-block; margin-top:4px;}
.libre    { background: linear-gradient(145deg,#1e8449,#27ae60); }
.ocupada  { background: linear-gradient(145deg,#922b21,#e74c3c); animation: pulso 2.2s infinite; }
.reservada{ background: linear-gradient(145deg,#b9770e,#f39c12); }
.unida    { background: linear-gradient(145deg,#1f618d,#3498db); }
.grupo    { outline: 3px dashed #F5A623; outline-offset: 3px; }
@keyframes pulso { 0%{box-shadow:0 0 0 0 rgba(231,76,60,.55);} 70%{box-shadow:0 0 0 12px rgba(231,76,60,0);} 100%{box-shadow:0 0 0 0 rgba(231,76,60,0);} }

.zona-title { font-size: 1.15rem; font-weight: 700; margin: 14px 0 8px; color: #F5A623; }
.card { background:#161a26; border:1px solid #2a3145; border-radius:16px; padding:16px 18px; margin-bottom:12px; }
.ticket { background:#fdfaf3; color:#222; font-family:'Courier New',monospace; border-radius:6px;
  padding:22px; box-shadow:0 10px 30px rgba(0,0,0,.5); max-width:420px; margin:auto; }
.ticket h3 { text-align:center; margin:0; color:#222; }
.ticket hr { border:none; border-top:1px dashed #999; }
.badge { display:inline-block; padding:2px 10px; border-radius:12px; font-size:.75rem; font-weight:600; }
section[data-testid="stSidebar"] { background: linear-gradient(180deg,#141824,#1d1428); }
</style>
"""


def aplicar_estilos(titulo: str, subtitulo: str, icono: str = "🔥") -> None:
    """Inyecta el CSS y pinta la cabecera de la página."""
    st.markdown(CSS, unsafe_allow_html=True)
    st.markdown(f'<div class="hero"><h1>{icono} {titulo}</h1><p>{subtitulo}</p></div>',
                unsafe_allow_html=True)
    with st.sidebar:
        st.markdown(f"## 🔥 {NOMBRE}")
        st.caption("Sistema de gestión integral · Python + Streamlit + SQLite")


def kpi(col, icono: str, etiqueta: str, valor: str, delta: float | None = None,
        sufijo_delta: str = "vs periodo anterior") -> None:
    """Tarjeta KPI con variación coloreada."""
    dl = ""
    if delta is not None:
        clase, flecha = ("up", "▲") if delta >= 0 else ("down", "▼")
        dl = f'<div class="dl {clase}">{flecha} {abs(delta):.1f}% <span style="color:#777;font-weight:400">{sufijo_delta}</span></div>'
    col.markdown(f'<div class="kpi"><div class="ic">{icono}</div><div class="lb">{etiqueta}</div>'
                 f'<div class="vl">{valor}</div>{dl}</div>', unsafe_allow_html=True)


def mesa_html(numero: int, estado: str, capacidad: int, cap_grupo: int | None = None,
              etiqueta: str = "", en_grupo: bool = False) -> str:
    """Devuelve el HTML de una mesa con sus sillas dibujadas."""
    sillas = "🪑" * min(capacidad, 8)
    grupo = " grupo" if en_grupo else ""
    extra = f'<div class="tag">🔗 grupo {cap_grupo} pax</div>' if cap_grupo else ""
    tag = f'<div class="tag">{etiqueta}</div>' if etiqueta else ""
    return (f'<div class="mesa {estado}{grupo}"><div class="num">{numero}</div>'
            f'<div class="sillas">{sillas}</div><div class="cap">{capacidad} plazas · {estado}</div>'
            f'{extra}{tag}</div>')


def euros(x: float) -> str:
    """Formatea un número como moneda española: 1.234,56 €"""
    return f"{x:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")
