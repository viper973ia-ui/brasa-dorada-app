"""
gestor_mesas.py — Lógica de unión y separación de mesas
========================================================
Permite unir varias mesas para grupos grandes y separarlas después,
y sugiere automáticamente la mejor combinación según el número de comensales.

Temas del curso cubiertos:
  ✔ Diccionarios y conjuntos (capítulo 7)
  ✔ Funciones, lambdas, sorted(key=...) (capítulo 8)
  ✔ itertools.combinations
  ✔ Excepciones propias
"""
from itertools import combinations
from database import Database
from models import Mesa, MesaError


class GestorMesas:
    """Servicio que agrupa las operaciones sobre conjuntos de mesas."""

    def __init__(self):
        self.db = Database()

    # ── Consultas ─────────────────────────────────────────────────────────
    def mesas(self) -> list[Mesa]:
        return Mesa.todas()

    def grupos(self) -> dict[int, list[Mesa]]:
        """Devuelve {grupo_id: [mesas]} de las mesas unidas."""
        grupos: dict[int, list[Mesa]] = {}
        for m in self.mesas():
            if m.grupo_id:
                grupos.setdefault(m.grupo_id, []).append(m)
        return grupos

    def capacidad_grupo(self, grupo_id: int) -> int:
        return sum(m.capacidad for m in self.grupos().get(grupo_id, []))

    def capacidad_efectiva(self, mesa: Mesa) -> int:
        """Capacidad real: si está unida, la suma de su grupo."""
        return self.capacidad_grupo(mesa.grupo_id) if mesa.grupo_id else mesa.capacidad

    # ── Unir ──────────────────────────────────────────────────────────────
    def unir(self, ids: list[int]) -> int:
        """
        Une varias mesas libres. La de menor número pasa a ser la principal
        (grupo_id = su id) y las demás quedan en estado 'unida'.
        Devuelve el id de la mesa principal.
        """
        if len(ids) < 2:
            raise MesaError("Selecciona al menos 2 mesas para unir.")
        mesas = [Mesa.por_id(i) for i in ids]
        zonas = {m.zona for m in mesas}           # conjunto → zonas distintas
        if len(zonas) > 1:
            raise MesaError("Solo se pueden unir mesas de la misma zona.")
        ocupadas = [m.numero for m in mesas if m.estado != "libre" or m.grupo_id]
        if ocupadas:
            raise MesaError(f"Las mesas {ocupadas} no están libres o ya están unidas.")

        principal = min(mesas, key=lambda m: m.numero)
        for m in mesas:
            estado = "libre" if m.id == principal.id else "unida"
            self.db.execute("UPDATE mesas SET grupo_id=?, estado=? WHERE id=?",
                            (principal.id, estado, m.id))
        return principal.id

    # ── Separar ───────────────────────────────────────────────────────────
    def separar(self, grupo_id: int) -> None:
        """Separa un grupo de mesas (solo si no hay pedido abierto)."""
        abierto = self.db.fetchone(
            "SELECT id FROM pedidos WHERE mesa_id=? AND estado='abierto'", (grupo_id,))
        if abierto:
            raise MesaError("No se puede separar: el grupo tiene un pedido abierto. Cobra primero.")
        self.db.execute("UPDATE mesas SET grupo_id=NULL, estado='libre' WHERE grupo_id=?",
                        (grupo_id,))

    def liberar_grupo(self, grupo_id: int) -> None:
        """Al cobrar un grupo, separa automáticamente las mesas."""
        self.db.execute("UPDATE mesas SET grupo_id=NULL, estado='libre' WHERE grupo_id=?",
                        (grupo_id,))

    # ── Sugerencia automática ─────────────────────────────────────────────
    def sugerir(self, comensales: int, zona: str | None = None,
                max_mesas: int = 4) -> list[Mesa] | None:
        """
        Busca la combinación de mesas libres (de la misma zona) que acomode
        a los comensales desperdiciando el menor número de sillas.
        Criterio: (sillas sobrantes, nº de mesas) → menor es mejor.
        """
        libres = [m for m in self.mesas() if m.esta_libre and not m.grupo_id]
        if zona:
            libres = [m for m in libres if m.zona == zona]

        # 1) ¿Alguna mesa individual sirve?
        individuales = sorted((m for m in libres if m.capacidad >= comensales),
                              key=lambda m: m.capacidad - comensales)
        mejor, mejor_score = None, None
        if individuales:
            mejor = [individuales[0]]
            mejor_score = (individuales[0].capacidad - comensales, 1)

        # 2) Combinaciones de 2..max_mesas mesas de la misma zona
        por_zona: dict[str, list[Mesa]] = {}
        for m in libres:
            por_zona.setdefault(m.zona, []).append(m)
        for mesas_zona in por_zona.values():
            for n in range(2, max_mesas + 1):
                for combo in combinations(mesas_zona, n):
                    cap = sum(m.capacidad for m in combo)
                    if cap < comensales:
                        continue
                    score = (cap - comensales, n)
                    if mejor_score is None or score < mejor_score:
                        mejor, mejor_score = list(combo), score
        return mejor
