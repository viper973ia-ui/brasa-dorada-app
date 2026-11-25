"""
models.py — Modelos de dominio con POO
=======================================
Clases que representan las entidades del restaurante.

Temas del curso cubiertos:
  ✔ Clases, objetos, self, __init__ (capítulo 12)
  ✔ Herencia simple y múltiple
  ✔ Sobrescritura de métodos (__str__, __repr__)
  ✔ @property y encapsulación
  ✔ Métodos de clase (@classmethod)
  ✔ Excepciones propias (hereda de Exception)
  ✔ Lambdas y funciones de orden superior (capítulo 8)
  ✔ Fechas y datetime (capítulo 10)
"""
from __future__ import annotations
from datetime import datetime
from database import Database


# ════════════════════════════════════════════════════════════════════════════
#  Excepciones propias (heredan de Exception)
# ════════════════════════════════════════════════════════════════════════════

class RestauranteError(Exception):
    """Clase base para errores del restaurante."""
    pass

class MesaError(RestauranteError):
    """Error relacionado con las mesas."""
    pass

class PedidoError(RestauranteError):
    """Error relacionado con los pedidos."""
    pass


# ════════════════════════════════════════════════════════════════════════════
#  Clase Base
# ════════════════════════════════════════════════════════════════════════════

class EntidadBase:
    """
    Clase base de la que heredan todas las entidades.
    Encapsula el id y la fecha de creación.
    """
    IVA = 0.10   # atributo de clase compartido (IVA del 10 % en restaurantes)

    def __init__(self, id: int | None = None):
        self._id = id                            # atributo privado encapsulado

    @property
    def id(self) -> int | None:
        """Devuelve el id (encapsulación con @property)."""
        return self._id

    @classmethod
    def precio_con_iva(cls, precio: float) -> float:
        """Calcula el precio con IVA aplicado (método de clase)."""
        return round(precio * (1 + cls.IVA), 2)

    def __eq__(self, other) -> bool:
        return isinstance(other, type(self)) and self._id == other._id


# ════════════════════════════════════════════════════════════════════════════
#  Mesa
# ════════════════════════════════════════════════════════════════════════════

class Mesa(EntidadBase):
    """
    Representa una mesa del restaurante.

    Estados posibles: 'libre', 'ocupada', 'reservada', 'unida'
    Hereda de EntidadBase.
    """

    ESTADOS_VALIDOS = {"libre", "ocupada", "reservada", "unida"}
    COLORES         = {
        "libre":    "#2ecc71",
        "ocupada":  "#e74c3c",
        "reservada":"#f39c12",
        "unida":    "#3498db",
    }
    ICONOS = {
        "libre":    "🟢",
        "ocupada":  "🔴",
        "reservada":"🟡",
        "unida":    "🔵",
    }

    def __init__(self, id: int, numero: int, capacidad: int,
                 estado: str = "libre", grupo_id: int | None = None,
                 zona: str = "interior", pos_x: int = 0, pos_y: int = 0):
        super().__init__(id)
        self.numero    = numero
        self.capacidad = capacidad
        self._estado   = estado
        self.grupo_id  = grupo_id
        self.zona      = zona
        self.pos_x     = pos_x
        self.pos_y     = pos_y

    # ── Propiedades ──────────────────────────────────────────────────────
    @property
    def estado(self) -> str:
        return self._estado

    @estado.setter
    def estado(self, nuevo: str) -> None:
        if nuevo not in self.ESTADOS_VALIDOS:
            raise MesaError(f"Estado '{nuevo}' no válido. Usa: {self.ESTADOS_VALIDOS}")
        self._estado = nuevo

    @property
    def color(self) -> str:
        return self.COLORES[self._estado]

    @property
    def icono(self) -> str:
        return self.ICONOS[self._estado]

    @property
    def esta_libre(self) -> bool:
        return self._estado == "libre"

    # ── Métodos de acción ─────────────────────────────────────────────────
    def abrir(self, num_comensales: int = 1) -> None:
        """Abre la mesa para servicio."""
        if not self.esta_libre:
            raise MesaError(f"Mesa {self.numero} no está libre.")
        if num_comensales > self.capacidad:
            raise MesaError(f"La mesa {self.numero} tiene capacidad para {self.capacidad} personas.")
        self._estado = "ocupada"

    def cerrar(self) -> None:
        """Libera la mesa."""
        self._estado = "libre"
        self.grupo_id = None

    def guardar(self) -> None:
        """Persiste el estado actual en la base de datos."""
        db = Database()
        db.execute(
            "UPDATE mesas SET estado=?, grupo_id=? WHERE id=?",
            (self._estado, self.grupo_id, self._id)
        )

    # ── Representación ────────────────────────────────────────────────────
    def __str__(self) -> str:
        return f"Mesa {self.numero} ({self.zona}) — {self.icono} {self._estado} — cap. {self.capacidad}"

    def __repr__(self) -> str:
        return f"Mesa(id={self._id}, numero={self.numero}, estado='{self._estado}')"

    # ── Factory ───────────────────────────────────────────────────────────
    @classmethod
    def desde_dict(cls, d: dict) -> "Mesa":
        """Crea un objeto Mesa a partir de un diccionario (resultado DB)."""
        return cls(
            id=d["id"], numero=d["numero"], capacidad=d["capacidad"],
            estado=d["estado"], grupo_id=d.get("grupo_id"),
            zona=d.get("zona", "interior"),
            pos_x=d.get("pos_x", 0), pos_y=d.get("pos_y", 0)
        )

    @classmethod
    def todas(cls) -> list["Mesa"]:
        """Devuelve todas las mesas de la base de datos."""
        db = Database()
        rows = db.fetchall("SELECT * FROM mesas ORDER BY numero")
        return [cls.desde_dict(r) for r in rows]

    @classmethod
    def por_id(cls, mesa_id: int) -> "Mesa | None":
        db = Database()
        row = db.fetchone("SELECT * FROM mesas WHERE id=?", (mesa_id,))
        return cls.desde_dict(row) if row else None


# ════════════════════════════════════════════════════════════════════════════
#  Producto
# ════════════════════════════════════════════════════════════════════════════

class Producto(EntidadBase):
    """
    Representa un plato/bebida de la carta.
    Hereda de EntidadBase.
    """

    def __init__(self, id: int, nombre: str, categoria: str, precio: float,
                 descripcion: str = "", disponible: bool = True,
                 tiempo_prep: int = 10, categoria_id: int = 0):
        super().__init__(id)
        self.nombre      = nombre
        self.categoria   = categoria
        self.categoria_id = categoria_id
        self._precio     = precio
        self.descripcion = descripcion
        self._disponible = disponible
        self.tiempo_prep = tiempo_prep

    # ── Propiedades ──────────────────────────────────────────────────────
    @property
    def precio(self) -> float:
        return self._precio

    @precio.setter
    def precio(self, valor: float) -> None:
        if valor < 0:
            raise ValueError("El precio no puede ser negativo.")
        self._precio = round(valor, 2)

    @property
    def precio_iva(self) -> float:
        """Precio con IVA del 10 %."""
        return self.precio_con_iva(self._precio)

    @property
    def disponible(self) -> bool:
        return self._disponible

    # ── Representación ────────────────────────────────────────────────────
    def __str__(self) -> str:
        estado = "✅" if self._disponible else "❌"
        return f"{estado} {self.nombre} — {self._precio:.2f} €"

    def __repr__(self) -> str:
        return f"Producto(id={self._id}, nombre='{self.nombre}', precio={self._precio})"

    @classmethod
    def desde_dict(cls, d: dict) -> "Producto":
        return cls(
            id=d["id"], nombre=d["nombre"],
            categoria=d.get("categoria", ""),
            categoria_id=d.get("categoria_id", 0),
            precio=d["precio"],
            descripcion=d.get("descripcion", ""),
            disponible=bool(d.get("disponible", 1)),
            tiempo_prep=d.get("tiempo_prep", 10)
        )

    @classmethod
    def todos(cls) -> list["Producto"]:
        db = Database()
        rows = db.fetchall("""
            SELECT p.*, c.nombre AS categoria
            FROM productos p
            LEFT JOIN categorias c ON p.categoria_id = c.id
            ORDER BY c.orden, p.nombre
        """)
        return [cls.desde_dict(r) for r in rows]

    @classmethod
    def por_categoria(cls, categoria: str) -> list["Producto"]:
        db = Database()
        rows = db.fetchall("""
            SELECT p.*, c.nombre AS categoria
            FROM productos p
            JOIN categorias c ON p.categoria_id = c.id
            WHERE c.nombre = ? AND p.disponible = 1
            ORDER BY p.nombre
        """, (categoria,))
        return [cls.desde_dict(r) for r in rows]


# ════════════════════════════════════════════════════════════════════════════
#  LineaPedido
# ════════════════════════════════════════════════════════════════════════════

class LineaPedido(EntidadBase):
    """Una línea de pedido (producto + cantidad)."""

    def __init__(self, id: int | None, pedido_id: int, producto_id: int,
                 producto_nombre: str, cantidad: int, precio_unitario: float,
                 estado: str = "pendiente", notas: str = ""):
        super().__init__(id)
        self.pedido_id       = pedido_id
        self.producto_id     = producto_id
        self.producto_nombre = producto_nombre
        self.cantidad        = cantidad
        self.precio_unitario = precio_unitario
        self.estado          = estado
        self.notas           = notas

    @property
    def subtotal(self) -> float:
        return round(self.cantidad * self.precio_unitario, 2)

    def __str__(self) -> str:
        return f"{self.cantidad}× {self.producto_nombre} — {self.subtotal:.2f} €"

    @classmethod
    def desde_dict(cls, d: dict) -> "LineaPedido":
        return cls(
            id=d["id"], pedido_id=d["pedido_id"],
            producto_id=d["producto_id"],
            producto_nombre=d["producto_nombre"],
            cantidad=d["cantidad"],
            precio_unitario=d["precio_unitario"],
            estado=d.get("estado", "pendiente"),
            notas=d.get("notas", "")
        )


# ════════════════════════════════════════════════════════════════════════════
#  Pedido
# ════════════════════════════════════════════════════════════════════════════

class Pedido(EntidadBase):
    """
    Representa un pedido completo de una mesa.
    Hereda de EntidadBase.
    Demuestra: listas, lambdas, funciones de orden superior (map, filter, sum).
    """

    def __init__(self, id: int | None, mesa_id: int, mesa_numero: int,
                 num_comensales: int = 1, estado: str = "abierto",
                 notas: str = "", fecha_apertura: str = ""):
        super().__init__(id)
        self.mesa_id        = mesa_id
        self.mesa_numero    = mesa_numero
        self.num_comensales = num_comensales
        self.estado         = estado
        self.notas          = notas
        self.fecha_apertura = fecha_apertura or datetime.now().strftime("%Y-%m-%d %H:%M")
        self._lineas: list[LineaPedido] = []

    # ── Líneas ────────────────────────────────────────────────────────────
    def cargar_lineas(self) -> None:
        """Carga las líneas desde la base de datos."""
        db = Database()
        rows = db.fetchall(
            "SELECT * FROM lineas_pedido WHERE pedido_id=? ORDER BY id",
            (self._id,)
        )
        # Uso de list comprehension (tema del curso)
        self._lineas = [LineaPedido.desde_dict(r) for r in rows]

    def agregar_linea(self, producto: Producto, cantidad: int = 1,
                      notas: str = "") -> None:
        """Agrega o incrementa una línea de pedido."""
        db = Database()
        # Buscar si ya existe esa línea (uso de filter + lambda)
        existente = next(
            filter(lambda l: l.producto_id == producto.id, self._lineas),
            None
        )
        if existente:
            existente.cantidad += cantidad
            existente.estado = "pendiente"
            db.execute(
                "UPDATE lineas_pedido SET cantidad=?, subtotal=? WHERE id=?",
                (existente.cantidad, existente.subtotal, existente.id)
            )
        else:
            linea_id = db.execute(
                """INSERT INTO lineas_pedido
                   (pedido_id, producto_id, producto_nombre, cantidad, precio_unitario, subtotal, notas)
                   VALUES (?,?,?,?,?,?,?)""",
                (self._id, producto.id, producto.nombre, cantidad,
                 producto.precio, cantidad * producto.precio, notas)
            )
            linea = LineaPedido(
                id=linea_id, pedido_id=self._id,
                producto_id=producto.id, producto_nombre=producto.nombre,
                cantidad=cantidad, precio_unitario=producto.precio, notas=notas
            )
            self._lineas.append(linea)
        self._actualizar_total()

    def quitar_linea(self, linea_id: int) -> None:
        """Elimina una línea del pedido."""
        db = Database()
        db.execute("DELETE FROM lineas_pedido WHERE id=?", (linea_id,))
        self._lineas = [l for l in self._lineas if l.id != linea_id]
        self._actualizar_total()

    # ── Totales ───────────────────────────────────────────────────────────
    @property
    def lineas(self) -> list[LineaPedido]:
        return self._lineas

    @property
    def subtotal(self) -> float:
        """Suma de subtotales usando map + sum (funciones de orden superior)."""
        return round(sum(map(lambda l: l.subtotal, self._lineas)), 2)

    @property
    def iva(self) -> float:
        return round(self.subtotal * EntidadBase.IVA, 2)

    @property
    def total(self) -> float:
        return round(self.subtotal + self.iva, 2)

    def _actualizar_total(self) -> None:
        db = Database()
        db.execute("UPDATE pedidos SET total=? WHERE id=?", (self.total, self._id))

    # ── Estado ────────────────────────────────────────────────────────────
    def cerrar(self, metodo_pago: str = "efectivo", propina: float = 0.0) -> int:
        """Cierra el pedido y registra la transacción."""
        if not self._lineas:
            raise PedidoError("No se puede cerrar un pedido vacío.")
        db = Database()
        ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        db.execute(
            "UPDATE pedidos SET estado='cerrado', fecha_cierre=?, total=? WHERE id=?",
            (ahora, self.total, self._id)
        )
        trans_id = db.execute(
            """INSERT INTO transacciones (pedido_id, subtotal, iva, total, propina, metodo_pago)
               VALUES (?,?,?,?,?,?)""",
            (self._id, self.subtotal, self.iva, self.total + propina, propina, metodo_pago)
        )
        self.estado = "cerrado"
        # Liberar la mesa
        # Liberar la mesa y, si estaba unida, separar todo su grupo
        db.execute("UPDATE mesas SET estado='libre', grupo_id=NULL WHERE id=? OR grupo_id=?",
                   (self.mesa_id, self.mesa_id))
        return trans_id

    # ── Representación ────────────────────────────────────────────────────
    def __str__(self) -> str:
        return (f"Pedido #{self._id} — Mesa {self.mesa_numero} "
                f"({self.num_comensales} comensales) — {self.total:.2f} € — {self.estado}")

    def __repr__(self) -> str:
        return f"Pedido(id={self._id}, mesa={self.mesa_numero}, total={self.total})"

    # ── Factory ───────────────────────────────────────────────────────────
    @classmethod
    def desde_dict(cls, d: dict) -> "Pedido":
        return cls(
            id=d["id"], mesa_id=d["mesa_id"], mesa_numero=d["mesa_numero"],
            num_comensales=d.get("num_comensales", 1),
            estado=d.get("estado", "abierto"),
            notas=d.get("notas", ""),
            fecha_apertura=d.get("fecha_apertura", "")
        )

    @classmethod
    def de_mesa(cls, mesa_id: int) -> "Pedido | None":
        """Devuelve el pedido abierto de una mesa."""
        db = Database()
        row = db.fetchone(
            "SELECT * FROM pedidos WHERE mesa_id=? AND estado='abierto' ORDER BY id DESC LIMIT 1",
            (mesa_id,)
        )
        if not row:
            return None
        pedido = cls.desde_dict(row)
        pedido.cargar_lineas()
        return pedido

    @classmethod
    def crear(cls, mesa: Mesa, num_comensales: int = 1) -> "Pedido":
        """Crea un nuevo pedido y lo guarda en la BD."""
        if mesa.estado not in ("libre", "reservada"):
            raise PedidoError(f"La mesa {mesa.numero} ya tiene un pedido abierto.")
        db = Database()
        pedido_id = db.execute(
            """INSERT INTO pedidos (mesa_id, mesa_numero, num_comensales, estado)
               VALUES (?,?,?,'abierto')""",
            (mesa.id, mesa.numero, num_comensales)
        )
        db.execute("UPDATE mesas SET estado='ocupada' WHERE id=?", (mesa.id,))
        pedido = cls(
            id=pedido_id, mesa_id=mesa.id,
            mesa_numero=mesa.numero, num_comensales=num_comensales
        )
        return pedido
