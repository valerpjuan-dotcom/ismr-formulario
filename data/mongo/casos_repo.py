import streamlit as st
from pymongo import MongoClient, ASCENDING

from configuration.settings import TAB_NOMBRES
from data.mongo.usuarios_repo import _get_client

# Cabeceras canónicas por colección — espejo de lo que crea Google Sheets
_CABECERAS_CASOS = [
    "ID_Caso", "Timestamp",
    "Tipo de Estudio", "OT-TE", "Fecha Expedicion OT",
    "Tipo de Poblacion", "Subpoblacion",
    "Fecha de Nacimiento", "Sexo", "Género", "Orientación Sexual", "Jefatura del Hogar",
    "Zona Rural", "Zona de Reserva Campesina",
    "Departamento", "Municipio", "Solicitante",
    "Nivel de Riesgo", "Observaciones",
    "Num Personas Nucleo Familiar", "Companero Permanente",
    "Num Hijos Menores Edad", "Num Menores Otros", "Num Adultos Mayores", "Num Discapacidad",
    "OSIEGD", "Factor Discapacidad", "Factor Etnia", "Factor Campesino",
    "Factor Cuidador", "Factor Victima Conflicto Armado", "Factor Lider Social DDHH",
    "Analista", "Usuario Analista"
]
_CABECERAS_HECHOS = [
    "ID_Hecho", "ID_Caso", "OT-TE", "Tipo de Hecho",
    "Fecha del Hecho", "Departamento", "Municipio",
    "Tipo Actor Generador", "Actor Generador",
    "Medio Hecho", "Victima Situacion", "Tipo Amenaza",
    "Motivacion Amenaza", "Nexo Causal",
    "Descripcion",
    "Analista", "Usuario Analista"
]
_CABECERAS_ANTECEDENTES = [
    "ID_Antecedente", "ID_Caso", "OT-TE",
    "Registra OT Antecedentes", "Registra Resoluciones o Medidas Vigentes",
    "Dia Resolucion MTSP", "Mes Resolucion MTSP", "Anio Resolucion MTSP",
    "Analista", "Usuario Analista"
]
_CABECERAS_PERFILES = [
    "ID_Perfil", "ID_Caso", "OT-TE",
    "Modo de Participación", "Año Ingreso/Traslado/Captura", "Bloque de Operación",
    "Estructura", "Lugar de Acreditación", "Rol/Actividades",
    "Otro Rol", "Subpoblación Índice 1", "Meses Privado de Libertad",
    "Tipo Institución Penitenciaria", "Pabellón Alta Seguridad",
    "Analista", "Usuario Analista"
]
_CABECERAS_DESPLAZAMIENTOS = [
    "ID_Desplazamiento", "ID_Caso", "OT-TE",
    "Motivo Desplazamiento",
    "Medios de Transporte",
    "Departamento Origen", "Municipio Origen",
    "Departamento Destino", "Municipio Destino",
    "Frecuencia", "Tipo de Via",
    "Analista", "Usuario Analista"
]

_CABECERAS_PERFILES_ACTUALES = [
    "ID_Perfil_Actual", "ID_Caso", "OT-TE",
    "Nivel Educativo", "Fuente Principal de Ingresos",
    "Estado Proyecto ARN", "Actividad Economica",
    "Comparecencia JEP", "Macrocasos JEP",
    "Victima JEP", "Macrocaso Victima",
    "Participacion TOAR", "Busqueda Desaparecidos",
    "Participacion PNIS", "Desminado",
    "Participa Comunes", "Concejo Comunes",
    "Instancias Partido", "Roles Partido",
    "Consejeria Nacional", "Tipo Consejeria",
    "Participa Otras Org", "Tipo Org",
    "Nombre Org", "Ambito Org", "Escala Org",
    "Departamento Org", "Municipio Org", "Rol Org",
    "Anio Inicio Org", "Anio Fin Org",
    "Cargo Eleccion",
    "Analista", "Usuario Analista"
]


def _conectar_db():
    """Retorna la base de datos MongoDB usando el cliente singleton."""
    try:
        db_name = st.secrets["mongodb"].get("db_name", "ismr")
        return _get_client()[db_name]
    except Exception as e:
        st.error(f"Error al conectar MongoDB: {str(e)}")
        return None


# ── Borradores ────────────────────────────────────────────────────────────────

def _serializar(obj):
    """Convierte tipos no serializables por BSON (datetime.date, datetime.datetime) a string ISO."""
    import datetime
    if isinstance(obj, (datetime.date, datetime.datetime)):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {k: _serializar(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_serializar(i) for i in obj]
    return obj


def guardar_borrador(username: str, tipo: str, datos: dict) -> bool:
    """
    Upsert de un borrador asociado a username + tipo de formulario.
    Sobreescribe el borrador anterior si existe.
    """
    db = _conectar_db()
    if db is None:
        return False
    try:
        from datetime import datetime
        from zoneinfo import ZoneInfo
        datos_serializados = _serializar(datos)
        datos_serializados["_guardado_en"] = datetime.now(tz=ZoneInfo("America/Bogota")).strftime("%Y-%m-%d %H:%M:%S")
        db["borradores"].update_one(
            {"_username": username, "_tipo": tipo},
            {"$set": {**datos_serializados, "_username": username, "_tipo": tipo}},
            upsert=True,
        )
        return True
    except Exception as e:
        st.error(f"Error al guardar borrador: {str(e)}")
        return False


def cargar_borrador(username: str, tipo: str) -> dict | None:
    """
    Devuelve el borrador del usuario para el tipo dado, o None si no existe.
    """
    db = _conectar_db()
    if db is None:
        return None
    try:
        doc = db["borradores"].find_one(
            {"_username": username, "_tipo": tipo}, {"_id": 0}
        )
        return doc or None
    except Exception as e:
        st.error(f"Error al cargar borrador: {str(e)}")
        return None


def eliminar_borrador(username: str, tipo: str) -> None:
    """
    Elimina el borrador del usuario tras un envío definitivo exitoso.
    """
    db = _conectar_db()
    if db is None:
        return
    try:
        db["borradores"].delete_one({"_username": username, "_tipo": tipo})
    except Exception as e:
        st.error(f"Error al eliminar borrador: {str(e)}")


def conectar_sheet_casos(tipo="individual"):
    """
    Equivalente a conectar_sheet_casos() de Google Sheets.
    Retorna (proxy_casos, proxy_hechos, db_url) donde los proxies
    implementan la misma interfaz que un gspread Worksheet:
      - get_all_values() -> list[list]
      - get_all_records() -> list[dict]
      - append_row(values: list) -> None
    Crea índices automáticamente si no existen (idempotente).
    """
    db = _conectar_db()
    if db is None:
        return None, None, None, None, None, None, None

    try:
        tab_casos              = TAB_NOMBRES[tipo]["casos"]
        tab_hechos             = TAB_NOMBRES[tipo]["hechos"]
        tab_perfiles           = TAB_NOMBRES[tipo]["perfiles"]
        tab_antecedentes       = TAB_NOMBRES[tipo]["antecedentes"]
        tab_perfiles_actuales  = TAB_NOMBRES[tipo]["perfiles_actuales"]
        tab_desplazamientos    = TAB_NOMBRES[tipo].get("desplazamientos", f"desplazamientos_{tipo}")

        nombre_col_casos              = f"casos_{tab_casos.lower()}"
        nombre_col_hechos             = f"hechos_{tab_hechos.lower()}"
        nombre_col_perfiles           = f"perfiles_{tab_perfiles.lower()}"
        nombre_col_antecedentes       = f"antecedentes_{tab_antecedentes.lower()}"
        nombre_col_perfiles_actuales  = f"perfiles_actuales_{tab_perfiles_actuales.lower()}"
        nombre_col_desplazamientos    = f"desplazamientos_{tab_desplazamientos.lower()}"

        col_casos             = db[nombre_col_casos]
        col_hechos            = db[nombre_col_hechos]
        col_perfiles          = db[nombre_col_perfiles]
        col_antecedentes      = db[nombre_col_antecedentes]
        col_perfiles_actuales = db[nombre_col_perfiles_actuales]
        col_desplazamientos   = db[nombre_col_desplazamientos]

        # Índices — idempotentes, no fallan si ya existen
        col_casos.create_index([("OT-TE", ASCENDING)], unique=True, background=True)
        col_hechos.create_index([("ID_Caso", ASCENDING)], background=True)
        col_perfiles.create_index([("ID_Caso", ASCENDING)], background=True)
        col_antecedentes.create_index([("ID_Caso", ASCENDING)], background=True)
        col_perfiles_actuales.create_index([("ID_Caso", ASCENDING)], background=True)
        col_desplazamientos.create_index([("ID_Caso", ASCENDING)], background=True)

        proxy_casos             = WorksheetProxy(col_casos,             _CABECERAS_CASOS)
        proxy_hechos            = WorksheetProxy(col_hechos,            _CABECERAS_HECHOS)
        proxy_perfiles          = WorksheetProxy(col_perfiles,          _CABECERAS_PERFILES)
        proxy_antecedentes      = WorksheetProxy(col_antecedentes,      _CABECERAS_ANTECEDENTES)
        proxy_perfiles_actuales = WorksheetProxy(col_perfiles_actuales, _CABECERAS_PERFILES_ACTUALES)
        proxy_desplazamientos   = WorksheetProxy(col_desplazamientos,   _CABECERAS_DESPLAZAMIENTOS)

        uri = st.secrets["mongodb"]["uri"]
        db_url = uri.split("@")[-1] if "@" in uri else uri  # oculta credenciales

        return proxy_casos, proxy_hechos, proxy_perfiles, proxy_antecedentes, proxy_perfiles_actuales, proxy_desplazamientos, db_url
    except Exception as e:
        st.error(f"Error al conectar colecciones MongoDB ({tipo}): {str(e)}")
        return None, None, None, None, None, None, None


# ── Proxy de Worksheet ────────────────────────────────────────────────────────

class WorksheetProxy:
    """
    Emula la interfaz de gspread.Worksheet que usa la capa de servicio y UI:
      - get_all_values()  -> list[list]   (primera fila = cabeceras)
      - get_all_records() -> list[dict]
      - append_row(values: list) -> None

    Internamente mapea cada fila a un documento MongoDB usando las
    cabeceras como nombres de campo.
    """

    def __init__(self, coleccion, cabeceras: list):
        self._col = coleccion
        self._cabeceras = cabeceras

    # ── Lectura ───────────────────────────────────────────────────────────────

    def get_all_records(self) -> list:
        """
        Retorna todos los documentos como lista de dicts,
        con las mismas keys que cabeceras, sin el campo _id de MongoDB.
        """
        try:
            docs = list(self._col.find({}, {"_id": 0}))
            return [self._completar_cabeceras(d) for d in docs]
        except Exception as e:
            st.error(f"Error al leer registros: {str(e)}")
            return []

    def get_all_values(self) -> list:
        """
        Retorna los datos como lista de listas, incluyendo la fila de
        cabeceras como primera fila (igual que gspread).
        """
        records = self.get_all_records()
        if not records:
            return [self._cabeceras]
        filas = [self._cabeceras]
        for rec in records:
            filas.append([str(rec.get(c, "")) for c in self._cabeceras])
        return filas

    # ── Escritura ─────────────────────────────────────────────────────────────

    def append_row(self, values: list) -> None:
        """
        Inserta un documento mapeando la lista de valores a las cabeceras
        en el mismo orden que Google Sheets.
        """
        from pymongo.errors import DuplicateKeyError
        if len(values) != len(self._cabeceras):
            raise ValueError(
                f"Se esperaban {len(self._cabeceras)} valores, "
                f"se recibieron {len(values)}"
            )
        doc = dict(zip(self._cabeceras, values))
        try:
            self._col.insert_one(doc)
        except DuplicateKeyError:
            ot_val = doc.get("OT-TE", "")
            st.error(f"❌ El caso '{ot_val}' ya existe en la base de datos.")
        except Exception as e:
            st.error(f"Error al insertar registro: {str(e)}")

    # ── Helper ────────────────────────────────────────────────────────────────

    def _completar_cabeceras(self, doc: dict) -> dict:
        """Garantiza que el dict tenga todas las cabeceras esperadas."""
        return {c: doc.get(c, "") for c in self._cabeceras}
