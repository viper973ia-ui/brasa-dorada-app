"""
database.py — Gestión de la base de datos SQLite
=================================================
Patrón Singleton con POO para garantizar una única instancia
de la conexión a lo largo de toda la aplicación.

Temas del curso cubiertos:
  ✔ Clases y objetos (capítulo 12)
  ✔ Atributos de clase vs. de instancia
  ✔ Métodos especiales (__new__, __init__)
  ✔ Captura de excepciones (capítulo 11)
  ✔ Type hints
"""
import sqlite3
import os
from pathlib import Path

# ── Rutas relativas al directorio de este script (portable a la nube) ──
BASE_DIR = Path(__file__).resolve().parent
DB_PATH  = BASE_DIR / "restaurante.db"


class Database:
    """
    Acceso a la base de datos SQLite usando el patrón Singleton.

    Al usar __new__ garantizamos que sólo exista un objeto Database
    durante toda la ejecución de la aplicación (atributo de clase _instance).
    """

    _instance = None           # Atributo de clase compartido por todos los objetos

    def __new__(cls):
        """Patrón Singleton: crea la instancia solo si no existe."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        self.db_path = str(DB_PATH)

    def __repr__(self) -> str:
        return f"Database(path='{self.db_path}')"

    # ── Conexión ─────────────────────────────────────────────────────────
    def get_connection(self) -> sqlite3.Connection:
        """Abre y devuelve una conexión con row_factory activado."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row          # acceso por nombre de columna
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    # ── Operaciones genéricas ─────────────────────────────────────────────
    def execute(self, query: str, params: tuple = ()) -> int:
        """Ejecuta INSERT/UPDATE/DELETE y devuelve el id del último registro."""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute(query, params)
                conn.commit()
                return cursor.lastrowid
        except sqlite3.Error as e:
            raise RuntimeError(f"Error en DB: {e}") from e

    def executemany(self, query: str, params_list: list) -> None:
        """Ejecuta una sentencia con múltiples conjuntos de parámetros (bulk insert)."""
        try:
            with self.get_connection() as conn:
                conn.executemany(query, params_list)
                conn.commit()
        except sqlite3.Error as e:
            raise RuntimeError(f"Error en DB (bulk): {e}") from e

    def fetchall(self, query: str, params: tuple = ()) -> list[dict]:
        """SELECT que devuelve todos los resultados como lista de diccionarios."""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute(query, params)
                return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            raise RuntimeError(f"Error en SELECT: {e}") from e

    def fetchone(self, query: str, params: tuple = ()) -> dict | None:
        """SELECT que devuelve el primer resultado o None."""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute(query, params)
                row = cursor.fetchone()
                return dict(row) if row else None
        except sqlite3.Error as e:
            raise RuntimeError(f"Error en SELECT: {e}") from e

    # ── Creación de esquema ───────────────────────────────────────────────
    def create_tables(self) -> None:
        """Crea todas las tablas si no existen (idempotente)."""
        esquemas = [
            # ── Mesas ────────────────────────────────────────────────────
            """CREATE TABLE IF NOT EXISTS mesas (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                numero    INTEGER UNIQUE NOT NULL,
                capacidad INTEGER NOT NULL,
                estado    TEXT    DEFAULT 'libre',
                grupo_id  INTEGER DEFAULT NULL,
                zona      TEXT    DEFAULT 'interior',
                pos_x     INTEGER DEFAULT 0,
                pos_y     INTEGER DEFAULT 0
            )""",
            # ── Categorías ───────────────────────────────────────────────
            """CREATE TABLE IF NOT EXISTS categorias (
                id     INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT UNIQUE NOT NULL,
                icono  TEXT    DEFAULT '🍽️',
                orden  INTEGER DEFAULT 0
            )""",
            # ── Productos ────────────────────────────────────────────────
            """CREATE TABLE IF NOT EXISTS productos (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre       TEXT NOT NULL,
                categoria_id INTEGER,
                precio       REAL NOT NULL,
                descripcion  TEXT,
                disponible   INTEGER DEFAULT 1,
                tiempo_prep  INTEGER DEFAULT 10,
                FOREIGN KEY (categoria_id) REFERENCES categorias(id)
            )""",
            # ── Pedidos ──────────────────────────────────────────────────
            """CREATE TABLE IF NOT EXISTS pedidos (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                mesa_id        INTEGER,
                mesa_numero    INTEGER,
                fecha_apertura TEXT DEFAULT (datetime('now','localtime')),
                fecha_cierre   TEXT,
                estado         TEXT DEFAULT 'abierto',
                total          REAL DEFAULT 0,
                num_comensales INTEGER DEFAULT 1,
                notas          TEXT,
                FOREIGN KEY (mesa_id) REFERENCES mesas(id)
            )""",
            # ── Líneas de pedido ─────────────────────────────────────────
            """CREATE TABLE IF NOT EXISTS lineas_pedido (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                pedido_id       INTEGER,
                producto_id     INTEGER,
                producto_nombre TEXT,
                cantidad        INTEGER DEFAULT 1,
                precio_unitario REAL,
                subtotal        REAL,
                estado          TEXT DEFAULT 'pendiente',
                notas           TEXT,
                FOREIGN KEY (pedido_id) REFERENCES pedidos(id),
                FOREIGN KEY (producto_id) REFERENCES productos(id)
            )""",
            # ── Reservas ─────────────────────────────────────────────────
            """CREATE TABLE IF NOT EXISTS reservas (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre       TEXT NOT NULL,
                email        TEXT,
                telefono     TEXT,
                fecha        TEXT NOT NULL,
                hora         TEXT NOT NULL,
                num_personas INTEGER NOT NULL,
                mesa_id      INTEGER,
                estado       TEXT DEFAULT 'confirmada',
                notas        TEXT,
                FOREIGN KEY (mesa_id) REFERENCES mesas(id)
            )""",
            # ── Transacciones ────────────────────────────────────────────
            """CREATE TABLE IF NOT EXISTS transacciones (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                pedido_id   INTEGER,
                fecha       TEXT DEFAULT (datetime('now','localtime')),
                subtotal    REAL,
                iva         REAL,
                total       REAL,
                propina     REAL DEFAULT 0,
                metodo_pago TEXT DEFAULT 'efectivo',
                FOREIGN KEY (pedido_id) REFERENCES pedidos(id)
            )"""
        ]
        with self.get_connection() as conn:
            for q in esquemas:
                conn.execute(q)
            conn.commit()

    def is_initialized(self) -> bool:
        """Devuelve True si la base de datos ya tiene mesas cargadas."""
        result = self.fetchone("SELECT COUNT(*) AS n FROM mesas")
        return (result["n"] > 0) if result else False
