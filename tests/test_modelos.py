"""Tests unitarios con pytest (capítulo 19). Ejecutar: pytest -q"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import EntidadBase, Mesa, MesaError, Producto  # noqa: E402
from styles import euros  # noqa: E402


def test_precio_con_iva():
    assert EntidadBase.precio_con_iva(10) == pytest.approx(11.0)


def test_setter_precio_valida_negativos():
    p = Producto(1, "Croquetas", "Entrantes", 8.5)
    with pytest.raises(ValueError):
        p.precio = -1
    p.precio = 9.456
    assert p.precio == 9.46


def test_estado_mesa_invalido():
    m = Mesa(1, 1, 4, "libre")
    with pytest.raises((MesaError, ValueError)):
        m.estado = "volando"


def test_formato_euros():
    assert euros(1234.5) == "1.234,50 €"
