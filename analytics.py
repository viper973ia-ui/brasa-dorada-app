"""
analytics.py — Capa de análisis de datos
=========================================
Convierte los datos de SQLite en DataFrames y calcula KPIs.

Temas del curso cubiertos:
  ✔ pandas: read_sql, groupby, pivot_table, resample, merge (capítulo 14)
  ✔ Polars: lazy API, group_by, agg, with_columns (capítulo 15)
  ✔ NumPy: medias móviles, percentiles, polyfit (capítulo 13)
  ✔ Decoradores (@st.cache_data)
"""
import sqlite3

import numpy as np
import pandas as pd
import polars as pl
import streamlit as st

from database import DB_PATH

DIAS_ES = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
MESES_ES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]


def _sql(query: str, params: tuple = ()) -> pd.DataFrame:
    with sqlite3.connect(DB_PATH) as conn:
        return pd.read_sql_query(query, conn, params=params)


# ── Datos base (cacheados 60 s) ──────────────────────────────────────────────
@st.cache_data(ttl=60)
def ventas() -> pd.DataFrame:
    """Un registro por pedido cerrado, con columnas de fecha derivadas."""
    df = _sql("""
        SELECT p.id, p.mesa_numero, p.num_comensales, p.fecha_apertura, p.fecha_cierre,
               m.zona, t.subtotal, t.iva, t.total, t.propina, t.metodo_pago
        FROM pedidos p
        JOIN transacciones t ON t.pedido_id = p.id
        LEFT JOIN mesas m ON m.id = p.mesa_id
        WHERE p.estado = 'cerrado'""")
    df["fecha_apertura"] = pd.to_datetime(df["fecha_apertura"])
    df["fecha_cierre"] = pd.to_datetime(df["fecha_cierre"])
    df["fecha"] = df["fecha_apertura"].dt.normalize()
    df["hora"] = df["fecha_apertura"].dt.hour
    df["dia_semana"] = df["fecha_apertura"].dt.dayofweek.map(lambda d: DIAS_ES[d])
    df["mes"] = df["fecha_apertura"].dt.to_period("M").astype(str)
    df["servicio"] = np.where(df["hora"] < 18, "Comida", "Cena")
    df["duracion_min"] = (df["fecha_cierre"] - df["fecha_apertura"]).dt.total_seconds() / 60
    df["ticket_persona"] = df["total"] / df["num_comensales"]
    return df


@st.cache_data(ttl=60)
def lineas() -> pd.DataFrame:
    df = _sql("""
        SELECT l.pedido_id, l.producto_nombre, l.cantidad, l.subtotal,
               c.nombre AS categoria, p.fecha_apertura
        FROM lineas_pedido l
        JOIN pedidos p ON p.id = l.pedido_id
        LEFT JOIN productos pr ON pr.id = l.producto_id
        LEFT JOIN categorias c ON c.id = pr.categoria_id
        WHERE p.estado = 'cerrado'""")
    df["fecha_apertura"] = pd.to_datetime(df["fecha_apertura"])
    return df


def filtrar(df: pd.DataFrame, desde, hasta, col: str = "fecha_apertura") -> pd.DataFrame:
    mask = (df[col].dt.date >= desde) & (df[col].dt.date <= hasta)
    return df.loc[mask]


# ── KPIs ─────────────────────────────────────────────────────────────────────
def kpis(df: pd.DataFrame, df_prev: pd.DataFrame) -> dict:
    """KPIs del periodo actual y variación % frente al periodo anterior."""
    def calc(d: pd.DataFrame) -> dict:
        return {
            "ingresos": d["total"].sum(),
            "pedidos": len(d),
            "comensales": d["num_comensales"].sum(),
            "ticket": d["total"].mean() if len(d) else 0,
            "ticket_persona": d["ticket_persona"].mean() if len(d) else 0,
            "propinas": d["propina"].sum(),
        }
    act, prev = calc(df), calc(df_prev)
    delta = {k: ((act[k] - prev[k]) / prev[k] * 100 if prev[k] else 0) for k in act}
    return {"actual": act, "delta": delta}


# ── Series temporales (pandas resample + NumPy) ──────────────────────────────
def serie_diaria(df: pd.DataFrame) -> pd.DataFrame:
    s = df.set_index("fecha_apertura")["total"].resample("D").sum().to_frame("ingresos")
    s["media_7d"] = s["ingresos"].rolling(7, min_periods=1).mean()
    # Tendencia lineal con np.polyfit
    x = np.arange(len(s))
    if len(s) > 1:
        a, b = np.polyfit(x, s["ingresos"].to_numpy(), 1)
        s["tendencia"] = a * x + b
    else:
        s["tendencia"] = s["ingresos"]
    return s.reset_index().rename(columns={"fecha_apertura": "fecha"})


def heatmap_ocupacion(df: pd.DataFrame) -> pd.DataFrame:
    """Pivot día de la semana × hora con nº de pedidos medio por día."""
    n_semanas = max(1, df["fecha"].nunique() / 6)
    pv = df.pivot_table(index="dia_semana", columns="hora", values="id",
                        aggfunc="count", fill_value=0) / n_semanas
    return pv.reindex([d for d in DIAS_ES if d in pv.index]).round(1)


# ── Polars: ranking de productos (API lazy) ───────────────────────────────────
def ranking_productos(df_lineas: pd.DataFrame, top: int = 10) -> pd.DataFrame:
    """Usa Polars para agregar ventas por producto — más rápido en grandes volúmenes."""
    if df_lineas.empty:
        return pd.DataFrame(columns=["producto_nombre", "categoria", "unidades", "ingresos"])
    res = (
        pl.from_pandas(df_lineas[["producto_nombre", "categoria", "cantidad", "subtotal"]])
        .lazy()
        .group_by(["producto_nombre", "categoria"])
        .agg([pl.col("cantidad").sum().alias("unidades"),
              pl.col("subtotal").sum().round(2).alias("ingresos")])
        .sort("ingresos", descending=True)
        .head(top)
        .collect()
    )
    return res.to_pandas()


def matriz_menu(df_lineas: pd.DataFrame) -> pd.DataFrame:
    """
    Menu Engineering (matriz BCG de la carta):
    popularidad (unidades) vs. rentabilidad (precio medio).
    Clasifica cada plato en Estrella, Vaca, Puzzle o Perro.
    """
    if df_lineas.empty:
        return pd.DataFrame()
    g = (pl.from_pandas(df_lineas[["producto_nombre", "categoria", "cantidad", "subtotal"]])
         .group_by(["producto_nombre", "categoria"])
         .agg([pl.col("cantidad").sum().alias("unidades"),
               pl.col("subtotal").sum().alias("ingresos")])
         .with_columns((pl.col("ingresos") / pl.col("unidades")).alias("precio_medio"))
         .to_pandas())
    med_u, med_p = np.median(g["unidades"]), np.median(g["precio_medio"])
    g["clase"] = np.select(
        [(g["unidades"] >= med_u) & (g["precio_medio"] >= med_p),
         (g["unidades"] >= med_u) & (g["precio_medio"] < med_p),
         (g["unidades"] < med_u) & (g["precio_medio"] >= med_p)],
        ["⭐ Estrella", "🐄 Vaca lechera", "🧩 Puzzle"], default="🐶 Perro")
    return g


def estado_actual() -> dict:
    """Situación en tiempo real del servicio."""
    mesas = _sql("SELECT estado, capacidad FROM mesas")
    abiertos = _sql("""SELECT COUNT(*) n, COALESCE(SUM(total),0) t, COALESCE(SUM(num_comensales),0) c
                       FROM pedidos WHERE estado='abierto'""").iloc[0]
    cocina = _sql("""SELECT COUNT(*) n FROM lineas_pedido l JOIN pedidos p ON p.id=l.pedido_id
                     WHERE p.estado='abierto' AND l.estado IN ('pendiente','en_cocina')""").iloc[0]["n"]
    hoy = pd.Timestamp.now().strftime("%Y-%m-%d")
    reservas = _sql("SELECT COUNT(*) n, COALESCE(SUM(num_personas),0) p FROM reservas WHERE fecha=? AND estado='confirmada'",
                    (hoy,)).iloc[0]
    activas = mesas[mesas["estado"].isin(["ocupada", "unida"])]
    return {
        "total_mesas": len(mesas),
        "ocupadas": int((mesas["estado"] == "ocupada").sum()),
        "libres": int((mesas["estado"] == "libre").sum()),
        "reservadas": int((mesas["estado"] == "reservada").sum()),
        "unidas": int((mesas["estado"] == "unida").sum()),
        "ocupacion_pct": len(activas) / len(mesas) * 100 if len(mesas) else 0,
        "comensales": int(abiertos["c"]),
        "pedidos_abiertos": int(abiertos["n"]),
        "importe_abierto": float(abiertos["t"]),
        "platos_cocina": int(cocina),
        "reservas_hoy": int(reservas["n"]),
        "personas_reserva": int(reservas["p"]),
        "aforo": int(mesas["capacidad"].sum()),
    }
