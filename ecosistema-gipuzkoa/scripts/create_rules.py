"""Creates cleanup_rules.json from the defined rules."""
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT = PROJECT_ROOT / "data" / "raw" / "cleanup_rules.json"

rules = {
    "provincia": "Gipuzkoa",
    "version": "1.0",
    "fecha": "2026-03-24",
    "grupos_consolidar": [
        {
            "nombre_final": "CAF (Construcciones y Auxiliar de Ferrocarriles)",
            "mantener": "CONSTRUCCIONES Y AUXILIAR DE FERROCARRILES, SA",
            "eliminar": [
                "CAF ENGINEERED MODERNIZATIONS SL.",
                "CAF SIGNALLING SL.",
                "CAF POWER & AUTOMATION SL.",
                "CAF INVESTMENT PROJECTS SA.",
                "PLAN METRO SA",
                "RAIL LINE COMPONENTS SL.",
                "LANDER SIMULATION & TRAINING SOLUTIONS SA",
                "CENTRO DE ENSAYOS Y ANALISIS CETEST SL",
                "CAF RAIL DIGITAL SERVICES SL.",
                "CONSTRUCCIONES Y AUXILIAR DE FERROCARRILES INVESTIGACION Y DESARROLLO CAFIRD SL.",
                "CARTERA SOCIAL SA",
                "GESTION ELABORACION DE MANUALES INDUSTRIALES INGENIERIA Y SERVICIOS COMPLEMENTARIOS SL",
            ],
            "razon": "Grupo CAF — filiales consolidadas en la matriz",
        },
        {
            "nombre_final": "Grupo ULMA",
            "mantener": "ULMA INVERSIONES, SOCIEDAD COOPERATIVA",
            "renombrar_a": "Grupo ULMA",
            "eliminar": [
                "ULMA PACKAGING S COOP",
                "ULMA C Y E, S. COOP.",
                "ULMA SERVICIOS DE MANUTENCION, S. COOP.",
                "ULMA FORJA, S. COOP.",
                "ULMA HORMIGON POLIMERO S.C.",
                "ULMA PROYECTOS DE EJECUCION SL.",
                "Ulma Construction",
                "Ulma Handling Systems",
            ],
            "razon": "Grupo ULMA — cooperativas y filiales consolidadas en el holding",
        },
        {
            "nombre_final": "Irizar Group",
            "mantener": "Irizar Group",
            "eliminar": [
                "IRIZAR E-MOBILITY SL.",
                "JEMA ENERGY SA",
                "DATIK INFORMACION INTELIGENTE SL.",
                "Datik (Grupo Irizar)",
                "Irizar Forge",
            ],
            "razon": "Grupo Irizar — filiales consolidadas en la matriz",
        },
        {
            "nombre_final": "Grupo Fagor",
            "eliminar": ["FagorArrasate", "EDERLAN SUBSIDIARIES SA"],
            "razon": "Duplicado exacto y filial instrumental",
        },
        {
            "nombre_final": "Grupo Uvesco",
            "mantener": "Grupo Uvesco",
            "eliminar": ["FOOD RETAIL SOLUTIONS SL.", "UVESCO FOOD RETAIL, S.L."],
            "razon": "Duplicados — 3 razones sociales para la misma empresa",
        },
        {
            "nombre_final": "Orona",
            "mantener": "Orona",
            "eliminar": ["ORONA HOLDING SA"],
            "razon": "Duplicado — holding vs operativa",
        },
        {
            "nombre_final": "Gureak",
            "mantener": "Gureak",
            "eliminar": [
                "GUREAK LANEAN SA.",
                "GUREAK GARBITASUNA SL.",
                "GUREAK MARKETING SL.",
                "GUREAK ZERBITZU ANITZAK SL.",
                "GUREAK BERDEA SL.",
                "GUREAK IKUZTEGIA SL.",
                "GUREAK OSTALARITZA SL",
                "GUREAK ZERBITZUGUNEAK SL.",
            ],
            "razon": "Filiales de Gureak — consolidar en una sola entrada",
        },
        {
            "nombre_final": "Estibadora Algeposa",
            "mantener": "ESTIBADORA ALGEPOSA SA",
            "eliminar": [
                "ALGEPOSA SERVICIOS LOGISTICOS FERROVIARIOS SL",
                "Algeposa/Railsider",
                "ALGEPOSA GESTION PORTUARIA SL",
                "AGENCIA MARITIMA ALGEPOSA SA",
                "INVERSIONES ALGEPOSA SA",
                "ALGEPOSA CORPORATE SERVICES SL",
                "ALGEPOSA GESTION Y TRANSPORTE SL",
            ],
            "razon": "Filiales y holdings del grupo Algeposa",
        },
        {
            "nombre_final": "GH Cranes",
            "mantener": "GH Cranes",
            "eliminar": ["INDUSTRIAS ELECTROMECANICAS G H SA"],
            "razon": "Duplicado exacto",
        },
        {
            "nombre_final": "Sarralle",
            "mantener": "SARRALLE SL",
            "eliminar": [
                "SARRALLE ENGINEERING SL",
                "SARRALLE STEEL MELTING PLANT SL",
                "SARRALLE SERVICIOS GENERALES SL",
                "SARRALLE COMERCIAL S.L.",
            ],
            "razon": "Filiales del grupo Sarralle",
        },
        {
            "nombre_final": "Ayesa Ibermática",
            "mantener": "AYESA IBERMATICA SA.",
            "eliminar": [
                "IBERMATICA PROVISION DE SERVICIOS S.L.",
                "INSTITUTO IBERMATICA DE INNOVACION S.L.",
            ],
            "razon": "Duplicado y filial I+D",
        },
        {
            "nombre_final": "Sabico Seguridad",
            "mantener": "SABICO SEGURIDAD SOCIEDAD ANONIMA",
            "eliminar": ["SABICO GRUPO EMPRESARIAL SA."],
            "razon": "Duplicado — holding vs operativa",
        },
        {
            "nombre_final": "Multiverse Computing",
            "mantener": "Multiverse Computing",
            "eliminar": ["MULTIVERSE COMPUTING RESEARCH SL."],
            "razon": "Duplicado exacto",
        },
        {
            "nombre_final": "Connect Group",
            "mantener": "CONNECT GROUP ESPAÑA DONOSTIA SL.",
            "eliminar": ["CONNECT GROUP CORPORATE DONOSTIA SL."],
            "razon": "Duplicado exacto",
        },
        {
            "nombre_final": "OBE Hettich",
            "mantener": "OBE HETTICH SL SOCIEDAD EN COMANDITA",
            "eliminar": ["OBE HETTICH SL"],
            "razon": "Duplicado exacto",
        },
        {
            "nombre_final": "JMA Alejandro Altuna",
            "mantener": "JMA ALEJANDRO ALTUNA, S.L.",
            "eliminar": ["ALEJANDRO ALTUNA SA"],
            "razon": "Duplicado exacto",
        },
        {
            "nombre_final": "Sociedad Vascongada de Publicaciones",
            "mantener": "SOCIEDAD VASCONGADA DE PUBLICACIONES, SOCIEDAD ANONIMA",
            "eliminar": ["El Diario Vasco"],
            "razon": "Duplicado — marca vs razón social",
        },
        {
            "nombre_final": "Lazpiur",
            "mantener": "Lazpiur",
            "eliminar": [
                "CONSTRUCCIONES MECANICAS JOSE LAZPIUR SLU",
                "GRUPO J. LAZPIUR SL.",
            ],
            "razon": "Duplicado y holding",
        },
        {
            "nombre_final": "Ibarmia",
            "mantener": "IBARMIA INNOVATEK SL",
            "eliminar": ["Ibarmia", "IBARMIA GESTINVER SL", "IBARMIA PRECISION SL"],
            "razon": "Duplicados y filiales",
        },
        {
            "nombre_final": "Erreka (Matz-Erreka)",
            "mantener": "Erreka (Matz-Erreka)",
            "eliminar": ["MATZ ERREKA SDAD COOP LMTDA"],
            "razon": "Duplicado exacto",
        },
        {
            "nombre_final": "Depósitos de Comercio Exterior (Decoexsa)",
            "mantener": "DEPOSITOS DE COMERCIO EXTERIOR, SA",
            "eliminar": ["Decoexsa"],
            "razon": "Duplicado — marca vs razón social",
        },
        {
            "nombre_final": "Jaso Group",
            "mantener": "Jaso Group",
            "eliminar": [
                "JASO EQUIPOS DE OBRAS Y CONSTRUCCIONES SL",
                "TALLERES JASO INDUSTRIAL SL",
                "SERVICIO DE ASISTENCIA TECNICA JASO SL",
            ],
            "razon": "Filiales del grupo Jaso",
        },
        {
            "nombre_final": "S21sec / Thales",
            "mantener": "S21sec / Thales Cyber Solutions",
            "eliminar": ["THALES S21 SEC ESPAÑA SA."],
            "razon": "Duplicado exacto",
        },
        {
            "nombre_final": "Giroa",
            "mantener": "GIROA SOCIEDAD ANONIMA",
            "eliminar": ["GIROA COGENERACION AIE."],
            "razon": "Filial del grupo",
        },
        {
            "nombre_final": "Iparlat",
            "mantener": "IPARLAT SA",
            "eliminar": ["Iparlat + Esnelat", "ESNELAT SL", "IPARLAT TECNO SL."],
            "razon": "Filiales del grupo Iparlat",
        },
        {
            "nombre_final": "LKS Next",
            "mantener": "LKS Next",
            "eliminar": [
                "LKS Krean",
                "KREAN ECS INDUSTRIAL PLANTS SL.",
                "LKS AUDITORES SL",
                "KREAN DB IBERICA SL.",
            ],
            "razon": "Filiales del grupo LKS/Krean",
        },
        {
            "nombre_final": "Olano",
            "mantener": "OLANO LOGISTICA DEL MAR SL.",
            "eliminar": [
                "OLANO NORTE SL.",
                "OLANO SEAFOOD S.L.",
                "OLANO SUR SL.",
                "OLANO LEVANTE SOCIEDAD ANONIMA.",
                "OLANO SEAFOOD IBERICA SA.",
                "OLANO MURCIA SL",
                "OLANO LOGISTICS INTERNACIONAL SL",
            ],
            "razon": "Filiales regionales del grupo Olano",
        },
        {
            "nombre_final": "Bellota",
            "eliminar": ["SOCIEDAD DE CARTERA ZESTOA SA."],
            "razon": "Holding — mantener Bellota Herramientas y Bellota Agrisolutions como independientes",
        },
        {
            "nombre_final": "Hine",
            "mantener": "HINE SA",
            "eliminar": ["HINE RENOVABLES SL"],
            "razon": "Filial del grupo",
        },
        {
            "nombre_final": "Haizea WEC",
            "mantener": "HAIZEA WEC FUNDICION SL.",
            "eliminar": [
                "HAIZEA WEC TRATAMIENTO SUPERFICIAL SA.",
                "HAIZEA WEC MECANIZADO SL.",
            ],
            "razon": "Filiales del grupo Haizea WEC",
        },
        {
            "nombre_final": "Biele",
            "mantener": "BIELE SA",
            "eliminar": ["BIELE DIGITAL SL."],
            "razon": "Filial digital",
        },
        {
            "nombre_final": "Hijos de Juan de Garay",
            "mantener": "HIJOS DE JUAN DE GARAY, SA",
            "eliminar": ["HJ GARAY CORPORACION INDUSTRIAL SA."],
            "razon": "Holding del grupo",
        },
        {
            "nombre_final": "Kendu",
            "mantener": "Kendu",
            "eliminar": ["KENDU RETAIL SL."],
            "razon": "Duplicado — razón social vs marca",
        },
        {
            "nombre_final": "Createch Medical",
            "mantener": "CREATECH MEDICAL S.L.",
            "eliminar": ["CREATECH INSTITUTE AEIE."],
            "razon": "Filial I+D",
        },
        {
            "nombre_final": "Etxe-Tar",
            "mantener": "ETXE TAR SA",
            "eliminar": ["Etxe-Tar (Etxetar)"],
            "razon": "Duplicado — marca vs razón social",
        },
        {
            "nombre_final": "Amenabar",
            "mantener": "CONSTRUCCIONES AMENABAR SA",
            "eliminar": ["AMENABAR ETXEGINTZA BERRIA SL."],
            "razon": "Duplicado del mismo grupo constructor",
        },
        {
            "nombre_final": "Bost",
            "mantener": "BOST MACHINE TOOLS COMPANY SLU",
            "eliminar": ["BOST TRADING COMPANY SL."],
            "razon": "Holding/trading del grupo",
        },
        {
            "nombre_final": "ABC Compressors",
            "mantener": "ABC COMPRESSORS GESTION DE COMPRESORES Y RECAMBIOS SA",
            "eliminar": ["ABC COMPRESSORS TECHNOLOGY CENTRE AIE."],
            "razon": "Filial I+D",
        },
        {
            "nombre_final": "Silicia",
            "mantener": "SILICIA SERVICIOS INTEGRALES SL.",
            "eliminar": ["SILICIA SERVEIS AUXILIARS SL."],
            "razon": "Duplicado regional",
        },
        {
            "nombre_final": "Estaciones de Servicio de Guipúzcoa",
            "mantener": "ESTACIONES DE SERVICIO DE GUIPUZCOA SA",
            "eliminar": [
                "ESTACION DE SERVICIO ZAISA SL",
                "ESTACION DE SERVICIO BILLABONA SA",
                "ESTACION DE SERVICIO ZARAUTZ SA",
                "ESTACION DE SERVICIO AZPEITIA-AZKOITIA S. L.",
                "ESTACION DE SERVICIO DE SATURRARAN SL",
                "AREA DE SERVICIO LEGORRETA SL",
                "ESTACION DE SERVICIO ARRIARAN SL",
                "ESTACION DE SERVICIO BIDEBIETA SL",
                "ESTACION DE SERVICIO CARABEL SL",
                "ESTACION DE SERVICIO ARRASATE SA",
                "ESTACION DE SERVICIO AMASA SL.",
                "ESTACION DE SERVICIO LAZKAO SL",
                "ESTACION DE SERVICIO LASARTE ORIA SA",
                "ESTACION DE SERVICIO KANTOI SA",
                "AUTO ESTACION DE SERVICIO DE IRUN SL",
            ],
            "razon": "Filiales individuales (gasolineras) del grupo",
        },
    ],
    "correcciones_datos": [
        {
            "empresa": "BOJ OLAÑETA SL",
            "renombrar_a": "BOJ Olañeta",
            "campos": {
                "empleados_numero": "50",
                "ventas_reales": "82000000",
                "ventas_confianza": "media",
            },
            "razon": "Boj Global SL absorbida por Boj Olañeta en feb 2025. Datos corregidos.",
        }
    ],
}

with open(OUTPUT, "w", encoding="utf-8") as f:
    json.dump(rules, f, ensure_ascii=False, indent=2)

total_elim = sum(len(g.get("eliminar", [])) for g in rules["grupos_consolidar"])
print(f"Rules saved to {OUTPUT}")
print(f"{len(rules['grupos_consolidar'])} groups, {total_elim} total eliminations")
