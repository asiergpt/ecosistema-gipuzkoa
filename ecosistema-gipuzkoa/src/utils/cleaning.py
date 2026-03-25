"""Funciones de limpieza de datos."""

import re
import unicodedata
from typing import Optional


def limpiar_nombre_legal(nombre: str) -> str:
    """Elimina sufijos legales (S.A., S.L., etc.) y normaliza."""
    if not isinstance(nombre, str):
        return ""
    sufijos = [
        r"\bSOCIEDAD ANONIMA UNIPERSONAL\b", r"\bSOCIEDAD LIMITADA UNIPERSONAL\b",
        r"\bSOCIEDAD ANONIMA\b", r"\bSOCIEDAD LIMITADA\b",
        r"\bS\.?L\.?U\.?\b", r"\bS\.?A\.?U\.?\b", r"\bS\.?L\.?\b", r"\bS\.?A\.?\b",
        r"\bS\.?\s*COOP\.?\b", r"\bCOOP\.?\b", r"\bSDAD\.?\b",
    ]
    nombre_limpio = nombre.upper().strip()
    for s in sufijos:
        nombre_limpio = re.sub(s, "", nombre_limpio)
    nombre_limpio = re.sub(r"[.,;:\-\"/()]", " ", nombre_limpio)
    return " ".join(nombre_limpio.split()).strip()


def normalizar_texto(texto: str) -> str:
    """Quita acentos y convierte a mayúsculas."""
    if not isinstance(texto, str):
        return ""
    nfkd = unicodedata.normalize("NFD", texto)
    sin_acentos = "".join(c for c in nfkd if unicodedata.category(c) != "Mn")
    return sin_acentos.upper().strip()


def parsear_empleados(texto: str) -> tuple[Optional[int], Optional[str]]:
    """Extrae número y fuente del campo de empleados de Gemini.
    
    Ejemplos:
        "535 (eInforma/Empresite)" → (535, "eInforma/Empresite")
        "~500-1000 técnicos" → (750, None)
        "No identificado públicamente" → (None, None)
    
    Returns:
        (numero, fuente)
    """
    if not texto or str(texto).lower() in ("nan", "no identificado", "sin datos", "n/a"):
        return None, None

    texto = str(texto)

    # Extraer fuente entre paréntesis
    fuente_match = re.search(r"\(([^)]+)\)", texto)
    fuente = fuente_match.group(1) if fuente_match else None

    # Extraer números (manejar formato español con puntos como separador de miles)
    # Primero intentar patrón con puntos de miles (ej: "16.333")
    numeros_raw = re.findall(r"\d[\d.]*\d|\d+", texto)
    if not numeros_raw:
        return None, fuente

    nums = []
    for n in numeros_raw:
        # Si tiene puntos, tratarlos como separadores de miles
        limpio = n.replace(".", "")
        try:
            val = int(limpio)
            if val > 0:
                nums.append(val)
        except ValueError:
            continue

    if len(nums) >= 2 and ("-" in texto or "entre" in texto.lower()):
        # Rango: tomar media
        return (nums[0] + nums[1]) // 2, fuente
    elif nums:
        return nums[0], fuente

    return None, fuente


def validar_nif(nif: str) -> bool:
    """Valida formato de NIF español."""
    return bool(re.match(r"^[A-Z]\d{7,8}$", nif.strip().upper()))
