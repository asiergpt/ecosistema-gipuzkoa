"""
Modelo de datos del ecosistema empresarial guipuzcoano.

Este archivo es la fuente de verdad del schema. Cualquier campo nuevo
se define aquí primero y luego se propaga al pipeline.
"""

from __future__ import annotations

from datetime import date
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


# ═══════════════════════════════════════════════════════════════
# ENUMS — Valores permitidos para campos categóricos
# ═══════════════════════════════════════════════════════════════


class MercadoCotizacion(str, Enum):
    """Dimensión 1 de la taxonomía: mercado de cotización."""
    IBEX_35 = "IBEX 35"
    MERCADO_CONTINUO = "Mercado Continuo"
    BME_GROWTH = "BME Growth"
    BME_SCALEUP = "BME Scaleup"
    NO_COTIZA = "No cotiza"


class TipologiaPropiedad(str, Enum):
    """Dimensión 2 de la taxonomía: propiedad y gobernanza.
    
    El orden refleja la regla de prelación: se asigna la primera
    categoría que encaje recorriendo de arriba a abajo.
    """
    FILIAL_MULTINACIONAL = "Filial de multinacional extranjera"
    FILIAL_GRUPO_ESPANOL = "Filial de grupo español no vasco"
    COOPERATIVA_MONDRAGON = "Cooperativa Mondragón"
    COOP_INDEPENDIENTE_GRANDE = "Cooperativa independiente — Gran grupo"
    COOP_INDEPENDIENTE_PYME = "Cooperativa independiente — Pyme / Sociedad Laboral"
    PARTICIPADA_PE = "Participada por PE / capital riesgo / family office"
    FAMILIAR_GRANDE = "Empresa familiar — Gran grupo"
    FAMILIAR_PYME = "Empresa familiar — Pyme"
    PROPIEDAD_PARTICIPATIVA = "Empresa con propiedad participativa de trabajadores"
    PUBLICA = "Empresa pública o participada por sector público"
    OTROS = "Otros"


class NivelConfianza(str, Enum):
    """Nivel de confianza en un dato."""
    ALTA = "alta"      # Dato verificado en fuente oficial
    MEDIA = "media"    # Estimación razonable o fuente secundaria
    BAJA = "baja"      # Placeholder, estimación gruesa, o sin verificar


class RolEcosistema(str, Enum):
    """Dimensión 3 de la taxonomía: rol en el ecosistema.
    
    Basada en el modelo de Campeonas Ocultas (INML) de Orkestra,
    Instituto Vasco de Competitividad.
    """
    CAMPEONA_OCULTA = "Campeona oculta"       # INML Orkestra: líder mundial en nicho, B2B, vasca
    CAMPEONA_FAMOSA = "Campeona famosa"        # Empresa vasca grande y conocida
    CAMPEONA_TRACTORA = "Campeona tractora"    # Filial extranjera/española que tira del ecosistema
    RESTO = "Resto del tejido empresarial"     # No encaja en las anteriores


class FuenteEntrada(str, Enum):
    """De dónde proviene la empresa en el dataset."""
    ELECONOMISTA = "eleconomista"
    CAMPEONAS_ORKESTRA = "campeonas_orkestra"
    INVESTIGACION_ADICIONAL = "investigacion_adicional"


class RolEnGrupo(str, Enum):
    """Rol de la entidad dentro de un grupo empresarial."""
    MATRIZ = "matriz"
    FILIAL = "filial"
    COOPERATIVA_DEL_GRUPO = "cooperativa_del_grupo"
    INDEPENDIENTE = "independiente"


class AmbitoEmpleados(str, Enum):
    """Si el dato de empleados es local o del grupo global."""
    ENTIDAD_LOCAL = "entidad_local"
    GRUPO_GLOBAL = "grupo_global"
    DESCONOCIDO = "desconocido"



# ═══════════════════════════════════════════════════════════════
# MODELOS DE DATOS
# ═══════════════════════════════════════════════════════════════


class DatosVentas(BaseModel):
    """Información de ventas con trazabilidad."""
    ventas_estimado: float = Field(
        description="Valor numérico de ventas. Puede ser real o placeholder (50M/25M/1.9M)."
    )
    ventas_texto_original: Optional[str] = Field(
        default=None,
        description="Texto original de ElEconomista ('corporativa', 'grande', 'mediana', etc.)"
    )
    ventas_reales: Optional[float] = Field(
        default=None,
        description="Cifra real de facturación cuando se ha verificado en fuente fiable."
    )
    ventas_fuente: Optional[str] = Field(
        default=None,
        description="Fuente del dato de ventas (eInforma, SABI, cuentas anuales, etc.)"
    )
    ventas_confianza: NivelConfianza = Field(
        default=NivelConfianza.BAJA,
        description="Nivel de confianza en el dato de ventas."
    )
    ventas_ano: Optional[int] = Field(
        default=None,
        description="Año fiscal al que corresponden las ventas."
    )


class DatosEmpleados(BaseModel):
    """Información de empleados con trazabilidad."""
    empleados_texto_original: Optional[str] = Field(
        default=None,
        description="Texto original del campo numero_empleados de Gemini."
    )
    empleados_numero: Optional[int] = Field(
        default=None,
        description="Número parseado de empleados."
    )
    empleados_fuente: Optional[str] = Field(
        default=None,
        description="Fuente: eInforma, Empresite, Wikipedia, LinkedIn, estimación, etc."
    )
    empleados_confianza: NivelConfianza = Field(
        default=NivelConfianza.BAJA
    )
    empleados_ambito: AmbitoEmpleados = Field(
        default=AmbitoEmpleados.DESCONOCIDO,
        description="Si el dato es de la entidad local o del grupo global."
    )


class Taxonomia(BaseModel):
    """Clasificación según las 3 dimensiones de la taxonomía."""
    
    # Dimensión 1: Cotización
    mercado_cotizacion: MercadoCotizacion = Field(
        default=MercadoCotizacion.NO_COTIZA
    )
    
    # Dimensión 2: Propiedad y gobernanza
    tipologia_propiedad: Optional[TipologiaPropiedad] = Field(
        default=None,
        description="Se asigna con regla de prelación."
    )
    taxonomia_confianza: NivelConfianza = Field(
        default=NivelConfianza.BAJA
    )
    taxonomia_razonamiento: Optional[str] = Field(
        default=None,
        description="Explicación de por qué se asignó esta categoría de propiedad."
    )
    
    # Dimensión 3: Rol en el ecosistema
    rol_ecosistema: Optional[RolEcosistema] = Field(
        default=None,
        description="Basado en criterios Orkestra INML."
    )
    rol_ecosistema_confianza: NivelConfianza = Field(
        default=NivelConfianza.BAJA
    )
    rol_ecosistema_razonamiento: Optional[str] = Field(
        default=None,
        description="Explicación: por qué oculta/famosa/tractora/resto."
    )


class GrupoEmpresarial(BaseModel):
    """Información de pertenencia a grupo."""
    grupo_empresarial: Optional[str] = Field(
        default=None,
        description="Nombre del grupo (ej: 'Grupo CAF', 'Grupo ULMA')"
    )
    rol_en_grupo: RolEnGrupo = Field(
        default=RolEnGrupo.INDEPENDIENTE
    )
    ventas_consolidadas_grupo: Optional[float] = Field(
        default=None,
        description="Solo para matrices: ventas consolidadas del grupo."
    )


class DatosGemini(BaseModel):
    """Campos procedentes del enriquecimiento con Gemini (datos cualitativos)."""
    ceo_actual: Optional[str] = None
    ano_constitucion: Optional[str] = None
    poblacion: Optional[str] = None
    web_oficial: Optional[str] = None
    actividad_resumen: Optional[str] = None
    tamano_ing: Optional[str] = None
    complejidad_txt: Optional[str] = None
    cto_actual: Optional[str] = None
    propiedad_accionistas: Optional[str] = None
    inversores_capital_privado: Optional[str] = None
    financiacion_publica_detalle: Optional[str] = None
    usa_inteligencia_artificial: Optional[str] = None
    plataforma_cloud: Optional[str] = None
    solvencia_txt: Optional[str] = None
    puntos_solv: Optional[str] = None
    perfil_txt: Optional[str] = None


class Scoring(BaseModel):
    """Scoring de encaje con perfil (solo fiable cuando los datos subyacentes lo son)."""
    score_encaje: Optional[float] = Field(
        default=None,
        description="Score de encaje con el perfil de Asier (0-100)."
    )
    justificacion_encaje: Optional[str] = None
    score_confianza: NivelConfianza = Field(
        default=NivelConfianza.BAJA,
        description="Refleja la calidad de los datos subyacentes al scoring."
    )


class Empresa(BaseModel):
    """Modelo principal de una empresa del ecosistema guipuzcoano.
    
    Cada instancia representa una entidad jurídica única (un NIF).
    Los grupos empresariales se modelan con el campo `grupo`.
    """

    # --- Identificación ---
    nif: str = Field(description="NIF/CIF de la empresa. Patrón: [A-W][0-9]{8}")
    nombre: str = Field(description="Denominación social completa.")
    nombre_comercial: Optional[str] = Field(
        default=None,
        description="Nombre comercial / marca (sin sufijos legales)."
    )
    ranking_eleconomista: Optional[int] = Field(
        default=None,
        description="Posición en el ranking de ElEconomista."
    )
    provincia: str = Field(default="guipúzcoa")

    # --- Clasificación sectorial ---
    cnae_original: Optional[str] = Field(
        default=None,
        description="Código CNAE tal como viene de ElEconomista."
    )
    sector_nombre_cnae: Optional[str] = Field(
        default=None,
        description="Descripción literal del CNAE (campo SECTOR_NOMBRE original)."
    )
    sector_amigable: Optional[str] = Field(
        default=None,
        description="Uno de los 45 sectores del mapping (ej: 'Maquinaria y equipo')."
    )

    # --- Datos numéricos con trazabilidad ---
    ventas: DatosVentas = Field(default_factory=DatosVentas)
    empleados: DatosEmpleados = Field(default_factory=DatosEmpleados)

    # --- Grupo empresarial ---
    grupo: GrupoEmpresarial = Field(default_factory=GrupoEmpresarial)

    # --- Taxonomía (2 dimensiones) ---
    taxonomia: Taxonomia = Field(default_factory=Taxonomia)

    # --- Innovación ---
    patentes: int = Field(default=0)
    patentes_confianza: float = Field(
        default=0.0,
        description="Score de confianza del matching de patentes (0-1)."
    )
    patentes_criterio: Optional[str] = Field(
        default=None,
        description="Método de matching: 'Exacto', 'Fuzzy Match (...)', 'Sin match'."
    )

    # --- Datos cualitativos de Gemini ---
    gemini: DatosGemini = Field(default_factory=DatosGemini)

    # --- Scoring ---
    scoring: Scoring = Field(default_factory=Scoring)

    # --- Metadatos ---
    es_campeona_oculta: bool = Field(
        default=False,
        description="Identificada en la lista de campeonas ocultas de Orkestra."
    )
    fuente_entrada: Optional[FuenteEntrada] = Field(
        default=None,
        description="De dónde proviene esta empresa en el dataset."
    )
    necesita_enriquecimiento: bool = Field(
        default=False,
        description="True si es empresa recuperada que aún no ha pasado por Gemini/Claude."
    )
    fecha_actualizacion: Optional[date] = None
    notas: Optional[str] = Field(
        default=None,
        description="Notas manuales de Asier durante la revisión."
    )

    @field_validator("nif")
    @classmethod
    def validar_nif(cls, v: str) -> str:
        """Valida formato NIF español."""
        import re
        v = v.strip().upper()
        if not re.match(r"^[ABCDEFGHJPQRSUVW]\d{8}$", v):
            # Las cooperativas empiezan por F, las SA por A, las SL por B
            if not re.match(r"^[A-Z]\d{7,8}$", v):
                raise ValueError(f"NIF con formato inválido: {v}")
        return v

    def es_cooperativa(self) -> bool:
        """Las cooperativas tienen NIF que empieza por F."""
        return self.nif.startswith("F")

    def tiene_ventas_reales(self) -> bool:
        """True si el dato de ventas no es un placeholder."""
        return self.ventas.ventas_confianza != NivelConfianza.BAJA

    def es_gran_empresa(self) -> bool:
        """Definición UE: >50M€ facturación o >250 empleados."""
        ventas_ok = (
            self.ventas.ventas_reales is not None
            and self.ventas.ventas_reales > 50_000_000
        )
        empleados_ok = (
            self.empleados.empleados_numero is not None
            and self.empleados.empleados_numero > 250
        )
        return ventas_ok or empleados_ok
