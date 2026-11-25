"""
API REST de La Brasa Dorada con FastAPI (capítulo 21).
Ejecutar:  uvicorn api:app --reload   →  documentación en http://localhost:8000/docs
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from database import Database
from gestor_mesas import GestorMesas
from models import Mesa, Producto
from seed_data import inicializar

inicializar()
app = FastAPI(title="La Brasa Dorada API", version="1.0",
              description="Consulta de mesas, carta, ventas y sugerencia de mesas.")
db = Database()


class Sugerencia(BaseModel):
    comensales: int = Field(..., ge=1, le=40)
    zona: str | None = None


@app.get("/")
def raiz():
    return {"restaurante": "La Brasa Dorada", "endpoints": ["/mesas", "/carta", "/ventas/resumen", "/mesas/sugerir"]}


@app.get("/mesas")
def mesas(estado: str | None = None):
    lista = [{"id": m.id, "numero": m.numero, "capacidad": m.capacidad, "zona": m.zona,
              "estado": m.estado, "grupo_id": m.grupo_id} for m in Mesa.todas()]
    return [m for m in lista if estado is None or m["estado"] == estado]


@app.get("/mesas/{numero}")
def mesa(numero: int):
    fila = db.fetchone("SELECT * FROM mesas WHERE numero=?", (numero,))
    if not fila:
        raise HTTPException(404, f"La mesa {numero} no existe")
    return fila


@app.post("/mesas/sugerir")
def sugerir(datos: Sugerencia):
    sug = GestorMesas().sugerir(datos.comensales, datos.zona)
    if not sug:
        raise HTTPException(409, "No hay mesas libres suficientes")
    return {"mesas": [m.numero for m in sug], "plazas": sum(m.capacidad for m in sug)}


@app.get("/carta")
def carta():
    return [{"nombre": p.nombre, "categoria": p.categoria, "precio": p.precio,
             "precio_iva": p.precio_iva, "disponible": p.disponible} for p in Producto.todos()]


@app.get("/ventas/resumen")
def resumen(dias: int = 30):
    return db.fetchone("""SELECT COUNT(*) AS pedidos, ROUND(SUM(t.total),2) AS ingresos,
                                 ROUND(AVG(t.total),2) AS ticket_medio
                          FROM transacciones t WHERE date(t.fecha) >= date('now', ?)""", (f"-{dias} days",))
