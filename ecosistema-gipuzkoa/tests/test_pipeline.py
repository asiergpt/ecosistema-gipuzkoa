"""Tests para los steps 1-4 del pipeline."""

import pandas as pd
import pytest

from src.pipeline.step1_recuperar import _parsear_ventas_texto
from src.pipeline.step2_mapping_sectorial import _extraer_cnae_digitos, asignar_sector
from src.pipeline.step3_deduplicar import _detectar_por_nombre, _determinar_rol
from src.utils.cleaning import limpiar_nombre_legal, normalizar_texto, parsear_empleados


# ─── Step 1: Parsear ventas ───


class TestParsearVentas:
    def test_numero_con_puntos(self):
        valor, texto = _parsear_ventas_texto("1.861.621.350")
        assert valor == 1861621350.0
        assert texto is None

    def test_categoria_corporativa(self):
        valor, texto = _parsear_ventas_texto("corporativa")
        assert valor is None
        assert texto == "corporativa"

    def test_categoria_grande(self):
        valor, texto = _parsear_ventas_texto("grande")
        assert valor is None
        assert texto == "grande"

    def test_categoria_mediana(self):
        valor, texto = _parsear_ventas_texto("mediana")
        assert valor is None
        assert texto == "mediana"

    def test_nan(self):
        valor, texto = _parsear_ventas_texto(float("nan"))
        assert valor is None
        assert texto is None

    def test_numero_pequeno(self):
        valor, texto = _parsear_ventas_texto("500.000")
        assert valor == 500000.0


# ─── Step 2: CNAE ───


class TestExtraerCNAE:
    def test_cnae_4_digitos(self):
        cnae3, cnae2 = _extraer_cnae_digitos("3020")
        assert cnae3 == "302"
        assert cnae2 == "30"

    def test_cnae_2_digitos(self):
        cnae3, cnae2 = _extraer_cnae_digitos("30")
        assert cnae3 is None
        assert cnae2 == "30"

    def test_cnae_nan(self):
        cnae3, cnae2 = _extraer_cnae_digitos(float("nan"))
        assert cnae3 is None
        assert cnae2 is None

    def test_cnae_con_texto(self):
        cnae3, cnae2 = _extraer_cnae_digitos("30.20")
        assert cnae3 == "302"
        assert cnae2 == "30"


class TestAsignarSector:
    def test_match_3_digitos_prioridad(self):
        m3 = {"302": "Ferroviario"}
        m2 = {"30": "Transporte genérico"}
        assert asignar_sector("3020", None, m3, m2) == "Ferroviario"

    def test_fallback_2_digitos(self):
        m3 = {}
        m2 = {"30": "Transporte genérico"}
        assert asignar_sector("3099", None, m3, m2) == "Transporte genérico"

    def test_fallback_investigacion(self):
        assert asignar_sector(None, "Distribución alimentaria", {}, {}) == "Distribución alimentaria"

    def test_sin_clasificar(self):
        assert asignar_sector(None, None, {}, {}) == "Sin clasificar"


# ─── Step 3: Grupos ───


class TestDetectarGrupo:
    def test_detecta_caf(self):
        grupos = [{"raiz": "CAF", "nombre_grupo": "Grupo CAF"}]
        # El nombre legal completo no contiene "CAF", pero filiales sí
        result = _detectar_por_nombre("CAF POWER AND AUTOMATION SL", grupos)
        assert result is not None
        assert result["nombre_grupo"] == "Grupo CAF"

    def test_no_detecta_nombre_largo_sin_raiz(self):
        grupos = [{"raiz": "CAF", "nombre_grupo": "Grupo CAF"}]
        result = _detectar_por_nombre("CONSTRUCCIONES Y AUXILIAR DE FERROCARRILES, SA", grupos)
        assert result is None  # La raíz "CAF" no aparece en el nombre completo

    def test_no_detecta_irrelevante(self):
        grupos = [{"raiz": "CAF", "nombre_grupo": "Grupo CAF"}]
        result = _detectar_por_nombre("DACHSER SPAIN SA.", grupos)
        assert result is None

    def test_determinar_rol_matriz_por_nif(self):
        rol = _determinar_rol("CAF SA", "CAF", "A20001020", "A20001020")
        assert rol == "matriz"

    def test_determinar_rol_filial(self):
        rol = _determinar_rol("CAF POWER AND AUTOMATION SL", "CAF", "B20123456", None)
        assert rol == "filial"

    def test_determinar_rol_cooperativa(self):
        rol = _determinar_rol("FAGOR ARRASATE SCOOP", "FAGOR", "F20123456", None)
        assert rol == "cooperativa_del_grupo"


# ─── Utilidades de limpieza ───


class TestCleaning:
    def test_parsear_empleados_con_fuente(self):
        num, fuente = parsear_empleados("535 (eInforma/Empresite)")
        assert num == 535
        assert fuente == "eInforma/Empresite"

    def test_parsear_empleados_rango(self):
        num, fuente = parsear_empleados("~500-1000 técnicos")
        assert num == 750
        assert fuente is None

    def test_parsear_empleados_sin_datos(self):
        num, fuente = parsear_empleados("No identificado públicamente")
        assert num is None
        assert fuente is None

    def test_limpiar_nombre_legal(self):
        result = limpiar_nombre_legal("CONSTRUCCIONES Y AUXILIAR DE FERROCARRILES, SA")
        assert "FERROCARRILES" in result
        assert "SA" not in result.split()  # SA debe haberse eliminado

    def test_normalizar_texto(self):
        assert normalizar_texto("guipúzcoa") == "GUIPUZCOA"
