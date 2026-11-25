"""
seed_data.py — Población de la base de datos con datos realistas
================================================================
Genera 6 meses de histórico de ventas con estacionalidad (fines de semana,
horas punta de comida y cena, verano) usando NumPy.

Temas del curso cubiertos:
  ✔ NumPy: generadores aleatorios, distribuciones (capítulo 13)
  ✔ datetime y timedelta (capítulo 10)
  ✔ Listas, tuplas, diccionarios (capítulos 6-7)
  ✔ Bucles for / while, if-elif-else (capítulos 4-5)
  ✔ Ficheros JSON (capítulo 11) → exporta la carta a carta.json
  ✔ if __name__ == "__main__"
"""
import json
import os
from datetime import datetime, timedelta

import numpy as np

from database import Database, BASE_DIR

RNG = np.random.default_rng(42)   # semilla → datos reproducibles

# ── Mesas: (numero, capacidad, zona, pos_x, pos_y) ──────────────────────────
MESAS = [
    # Salón interior (4 filas × 4 columnas aprox.)
    (1, 2, "Salón", 0, 0), (2, 2, "Salón", 1, 0), (3, 4, "Salón", 2, 0), (4, 4, "Salón", 3, 0),
    (5, 4, "Salón", 0, 1), (6, 4, "Salón", 1, 1), (7, 6, "Salón", 2, 1), (8, 2, "Salón", 3, 1),
    (9, 4, "Salón", 0, 2), (10, 4, "Salón", 1, 2), (11, 2, "Salón", 2, 2), (12, 2, "Salón", 3, 2),
    # Terraza
    (13, 2, "Terraza", 0, 0), (14, 2, "Terraza", 1, 0), (15, 4, "Terraza", 2, 0), (16, 4, "Terraza", 3, 0),
    (17, 4, "Terraza", 0, 1), (18, 4, "Terraza", 1, 1), (19, 6, "Terraza", 2, 1), (20, 2, "Terraza", 3, 1),
    # Reservado privado
    (21, 8, "Reservado", 0, 0), (22, 6, "Reservado", 1, 0), (23, 4, "Reservado", 2, 0),
    # Barra
    (24, 2, "Barra", 0, 0), (25, 2, "Barra", 1, 0), (26, 2, "Barra", 2, 0), (27, 2, "Barra", 3, 0),
]

# ── Carta: categoría → (icono, orden, [(nombre, precio, desc, tiempo, popularidad)]) ──
CARTA = {
    "Entrantes": ("🥗", 1, [
        ("Croquetas de jamón ibérico", 9.50, "8 unidades caseras, cremosas", 8, 9),
        ("Patatas bravas", 6.50, "Con salsa brava y alioli de la casa", 7, 10),
        ("Ensalada de burrata", 12.90, "Tomate rosa, pesto y piñones", 6, 6),
        ("Pulpo a la gallega", 18.50, "Con cachelos y pimentón de la Vera", 12, 7),
        ("Tabla de ibéricos", 19.90, "Jamón, lomo, chorizo y salchichón", 5, 6),
        ("Gazpacho andaluz", 6.90, "Con picatostes y guarnición", 4, 5),
        ("Calamares a la andaluza", 11.50, "Con limón y mayonesa de lima", 9, 7),
    ]),
    "Principales": ("🥩", 2, [
        ("Paella de marisco (2 pax)", 34.00, "Arroz bomba, gamba roja y mejillón", 30, 8),
        ("Arroz negro", 16.50, "Con sepia y alioli", 25, 5),
        ("Entrecot de vaca madurada", 26.90, "300 g con patatas y pimientos", 18, 7),
        ("Secreto ibérico", 19.50, "A la brasa con chimichurri", 15, 6),
        ("Lubina a la sal", 22.50, "Con verduras de temporada", 22, 5),
        ("Bacalao al pil-pil", 21.00, "Receta tradicional vasca", 20, 4),
        ("Hamburguesa gourmet", 15.90, "Wagyu, cheddar curado y cebolla caramelizada", 14, 8),
        ("Risotto de setas", 17.50, "Con trufa negra y parmesano", 20, 5),
    ]),
    "Postres": ("🍰", 3, [
        ("Tarta de queso", 6.90, "Al horno, estilo La Viña", 3, 9),
        ("Coulant de chocolate", 7.50, "Con helado de vainilla", 10, 7),
        ("Torrija caramelizada", 6.50, "Con helado de canela", 6, 5),
        ("Crema catalana", 5.90, "Quemada al momento", 4, 5),
        ("Fruta de temporada", 4.90, "Selección del día", 3, 3),
    ]),
    "Bebidas": ("🍷", 4, [
        ("Agua mineral", 2.50, "50 cl", 1, 10),
        ("Refresco", 3.00, "Cola, naranja o limón", 1, 8),
        ("Caña de cerveza", 2.80, "Cerveza de barril", 1, 10),
        ("Copa de vino tinto", 4.50, "D.O. Rioja crianza", 1, 7),
        ("Copa de vino blanco", 4.20, "D.O. Rueda verdejo", 1, 6),
        ("Botella de vino Ribera", 24.00, "D.O. Ribera del Duero", 1, 3),
        ("Sangría (jarra)", 14.00, "1 litro", 2, 4),
        ("Café", 1.80, "Solo, cortado o con leche", 2, 9),
    ]),
}

CLIENTES = ["García", "Martínez", "López", "Sánchez", "Pérez", "Gómez", "Fernández",
            "Ruiz", "Díaz", "Moreno", "Álvarez", "Romero", "Navarro", "Torres",
            "Domínguez", "Vázquez", "Ramos", "Gil", "Serrano", "Molina"]
NOMBRES = ["Ana", "Luis", "María", "Carlos", "Lucía", "Javier", "Elena", "Pablo",
           "Sara", "David", "Laura", "Miguel", "Carmen", "Jorge", "Paula", "Raúl"]


def insertar_mesas(db: Database) -> None:
    db.executemany(
        "INSERT INTO mesas (numero, capacidad, zona, pos_x, pos_y) VALUES (?,?,?,?,?)",
        MESAS)


def insertar_carta(db: Database) -> list[dict]:
    for nombre, (icono, orden, _) in CARTA.items():
        db.execute("INSERT INTO categorias (nombre, icono, orden) VALUES (?,?,?)",
                   (nombre, icono, orden))
    cats = {c["nombre"]: c["id"] for c in db.fetchall("SELECT id, nombre FROM categorias")}
    filas = [(n, cats[cat], p, d, t)
             for cat, (_, _, platos) in CARTA.items()
             for (n, p, d, t, _) in platos]
    db.executemany(
        "INSERT INTO productos (nombre, categoria_id, precio, descripcion, tiempo_prep) "
        "VALUES (?,?,?,?,?)", filas)

    # Exportar carta a JSON (manejo de ficheros)
    carta_json = {cat: [{"nombre": n, "precio": p, "descripcion": d}
                        for (n, p, d, _, _) in platos]
                  for cat, (_, _, platos) in CARTA.items()}
    with open(BASE_DIR / "carta.json", "w", encoding="utf-8") as f:
        json.dump(carta_json, f, ensure_ascii=False, indent=2)

    return db.fetchall("""SELECT p.id, p.nombre, p.precio, c.nombre AS categoria
                          FROM productos p JOIN categorias c ON p.categoria_id=c.id""")


def _pesos(productos: list[dict], categoria: str) -> tuple[list[dict], np.ndarray]:
    """Devuelve los productos de una categoría y su probabilidad (por popularidad)."""
    popularidad = {n: pop for _, (_, _, pl) in CARTA.items() for (n, _, _, _, pop) in pl}
    prods = [p for p in productos if p["categoria"] == categoria]
    w = np.array([popularidad[p["nombre"]] for p in prods], dtype=float)
    return prods, w / w.sum()


def generar_historico(db: Database, productos: list[dict], dias: int = 180) -> None:
    """Genera pedidos cerrados con estacionalidad realista."""
    hoy = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    mesas = db.fetchall("SELECT id, numero, capacidad, zona FROM mesas")
    cats = {c: _pesos(productos, c) for c in CARTA}
    metodos = ["tarjeta", "efectivo", "bizum"]
    p_metodos = [0.62, 0.23, 0.15]

    pedidos_rows, lineas_rows, trans_rows = [], [], []
    pedido_id = 0

    for d in range(dias, 0, -1):
        fecha = hoy - timedelta(days=d)
        dow = fecha.weekday()                         # 0 = lunes
        if dow == 0:                                  # lunes: cerrado por descanso
            continue
        factor = {4: 1.35, 5: 1.6, 6: 1.3}.get(dow, 1.0)          # vie/sáb/dom
        factor *= 1.25 if fecha.month in (6, 7, 8) else 1.0          # verano
        factor *= 1 + 0.15 * (dias - d) / dias                        # tendencia creciente

        for servicio, (h_ini, h_fin, base) in {"comida": (13, 16, 22), "cena": (20, 23, 26)}.items():
            n_pedidos = int(RNG.poisson(base * factor))
            for _ in range(n_pedidos):
                pedido_id += 1
                comensales = int(np.clip(RNG.choice([1, 2, 2, 2, 3, 4, 4, 5, 6, 8]), 1, 8))
                candidatas = [m for m in mesas if m["capacidad"] >= comensales] or mesas
                mesa = candidatas[RNG.integers(len(candidatas))]
                if fecha.month not in (5, 6, 7, 8, 9) and mesa["zona"] == "Terraza":
                    mesa = candidatas[RNG.integers(len(candidatas))]
                apertura = fecha + timedelta(hours=int(RNG.integers(h_ini, h_fin)),
                                             minutes=int(RNG.integers(0, 60)))
                duracion = int(np.clip(RNG.normal(75 if servicio == "comida" else 95, 20), 25, 180))
                cierre = apertura + timedelta(minutes=duracion)

                # Líneas: bebidas por comensal, entrantes a compartir, principales y postres
                subtotal = 0.0
                plan = {
                    "Bebidas": comensales + int(RNG.integers(0, comensales + 1)),
                    "Entrantes": max(1, int(RNG.poisson(comensales * 0.6))),
                    "Principales": comensales if RNG.random() > 0.15 else max(1, comensales - 1),
                    "Postres": int(RNG.binomial(comensales, 0.55)),
                }
                for cat, unidades in plan.items():
                    prods, w = cats[cat]
                    elegidos = RNG.choice(len(prods), size=unidades, p=w)
                    ids, cuentas = np.unique(elegidos, return_counts=True)
                    for idx, cant in zip(ids, cuentas):
                        pr = prods[int(idx)]
                        st = round(pr["precio"] * int(cant), 2)
                        subtotal += st
                        lineas_rows.append((pedido_id, pr["id"], pr["nombre"], int(cant),
                                            pr["precio"], st, "servido"))
                subtotal = round(subtotal, 2)
                iva = round(subtotal * 0.10, 2)
                total = round(subtotal + iva, 2)
                propina = round(float(total * RNG.choice([0, 0, 0.03, 0.05, 0.08, 0.10])), 2)
                pedidos_rows.append((pedido_id, mesa["id"], mesa["numero"],
                                     apertura.strftime("%Y-%m-%d %H:%M:%S"),
                                     cierre.strftime("%Y-%m-%d %H:%M:%S"),
                                     "cerrado", total, comensales))
                trans_rows.append((pedido_id, cierre.strftime("%Y-%m-%d %H:%M:%S"),
                                   subtotal, iva, round(total + propina, 2), propina,
                                   str(RNG.choice(metodos, p=p_metodos))))

    db.executemany("""INSERT INTO pedidos (id, mesa_id, mesa_numero, fecha_apertura, fecha_cierre,
                      estado, total, num_comensales) VALUES (?,?,?,?,?,?,?,?)""", pedidos_rows)
    db.executemany("""INSERT INTO lineas_pedido (pedido_id, producto_id, producto_nombre, cantidad,
                      precio_unitario, subtotal, estado) VALUES (?,?,?,?,?,?,?)""", lineas_rows)
    db.executemany("""INSERT INTO transacciones (pedido_id, fecha, subtotal, iva, total, propina,
                      metodo_pago) VALUES (?,?,?,?,?,?,?)""", trans_rows)


def generar_reservas(db: Database) -> None:
    """Reservas para los próximos 14 días y algunas pasadas."""
    hoy = datetime.now().date()
    mesas = db.fetchall("SELECT id, capacidad FROM mesas WHERE zona != 'Barra'")
    filas = []
    for d in range(-7, 15):
        fecha = hoy + timedelta(days=d)
        if fecha.weekday() == 0:
            continue
        for _ in range(int(RNG.integers(3, 10))):
            personas = int(RNG.choice([2, 2, 3, 4, 4, 5, 6, 8, 10, 12]))
            cand = [m for m in mesas if m["capacidad"] >= personas]
            mesa_id = cand[RNG.integers(len(cand))]["id"] if cand else None  # grupos grandes: sin asignar
            hora = str(RNG.choice(["13:30", "14:00", "14:30", "15:00", "20:30", "21:00", "21:30", "22:00"]))
            nombre = f"{RNG.choice(NOMBRES)} {RNG.choice(CLIENTES)}"
            estado = ("completada" if RNG.random() > 0.1 else "no_show") if d < 0 else "confirmada"
            filas.append((nombre, f"{nombre.split()[0].lower()}@mail.com",
                          f"6{RNG.integers(10_000_000, 99_999_999)}",
                          fecha.isoformat(), hora, personas, mesa_id, estado,
                          str(RNG.choice(["", "", "Cumpleaños 🎂", "Silla de bebé", "Alergia al marisco", "Junto a la ventana"]))))
    db.executemany("""INSERT INTO reservas (nombre, email, telefono, fecha, hora, num_personas,
                      mesa_id, estado, notas) VALUES (?,?,?,?,?,?,?,?,?)""", filas)


def generar_servicio_actual(db: Database, productos: list[dict]) -> None:
    """Deja algunas mesas ocupadas con pedidos abiertos y una pareja de mesas unidas."""
    ahora = datetime.now()
    # Unir mesas 9 y 10 (grupo de 8)
    m9 = db.fetchone("SELECT id FROM mesas WHERE numero=9")["id"]
    db.execute("UPDATE mesas SET grupo_id=?, estado='ocupada' WHERE numero=9", (m9,))
    db.execute("UPDATE mesas SET grupo_id=?, estado='unida' WHERE numero=10", (m9,))
    ocupadas = [(3, 4), (7, 5), (9, 8), (15, 3), (19, 6), (24, 2), (21, 7)]
    for num, comensales in ocupadas:
        mesa = db.fetchone("SELECT id FROM mesas WHERE numero=?", (num,))
        apertura = (ahora - timedelta(minutes=int(RNG.integers(10, 80)))).strftime("%Y-%m-%d %H:%M:%S")
        pid = db.execute("""INSERT INTO pedidos (mesa_id, mesa_numero, fecha_apertura, estado, num_comensales)
                            VALUES (?,?,?,'abierto',?)""", (mesa["id"], num, apertura, comensales))
        db.execute("UPDATE mesas SET estado='ocupada' WHERE id=?", (mesa["id"],))
        subtotal = 0.0
        for idx in RNG.choice(len(productos), size=int(RNG.integers(3, 8)), replace=False):
            pr = productos[int(idx)]
            cant = int(RNG.integers(1, 3))
            estado = str(RNG.choice(["pendiente", "en_cocina", "servido"]))
            db.execute("""INSERT INTO lineas_pedido (pedido_id, producto_id, producto_nombre, cantidad,
                          precio_unitario, subtotal, estado) VALUES (?,?,?,?,?,?,?)""",
                       (pid, pr["id"], pr["nombre"], cant, pr["precio"], pr["precio"] * cant, estado))
            subtotal += pr["precio"] * cant
        db.execute("UPDATE pedidos SET total=? WHERE id=?", (round(subtotal * 1.10, 2), pid))
    # Reservadas para hoy
    for num in (5, 22):
        db.execute("UPDATE mesas SET estado='reservada' WHERE numero=?", (num,))


def necesita_seed() -> bool:
    """True si la BD no existe o está vacía (p. ej. primer arranque en la nube)."""
    db = Database()
    if not os.path.exists(db.db_path):
        return True
    try:
        db.create_tables()
        return not db.is_initialized()
    except Exception:
        return True


def inicializar(forzar: bool = False) -> None:
    """Crea la base de datos y la puebla si está vacía."""
    db = Database()
    if forzar and os.path.exists(db.db_path):
        os.remove(db.db_path)
    db.create_tables()
    if db.is_initialized():
        return
    insertar_mesas(db)
    productos = insertar_carta(db)
    generar_historico(db, productos)
    generar_reservas(db)
    generar_servicio_actual(db, productos)


if __name__ == "__main__":
    inicializar(forzar=True)
    db = Database()
    for tabla in ("mesas", "productos", "pedidos", "lineas_pedido", "reservas", "transacciones"):
        print(f"{tabla:15s}: {db.fetchone(f'SELECT COUNT(*) AS n FROM {tabla}')['n']:>6} registros")
