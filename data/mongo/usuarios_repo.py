import streamlit as st
from pymongo import MongoClient


def _conectar_coleccion_usuarios():
    """Retorna la colección MongoDB de usuarios, o None si falla."""
    try:
        uri = st.secrets["mongodb"]["uri"]
        db_name = st.secrets["mongodb"].get("db_name", "ismr")
        client = MongoClient(uri)
        db = client[db_name]
        return db["usuarios"]
    except Exception as e:
        st.error(f"Error al conectar MongoDB (usuarios): {str(e)}")
        return None


def conectar_sheet_usuarios():
    """
    Equivalente a conectar_sheet_usuarios() de Google Sheets.
    Retorna la colección si la conexión es exitosa, None si falla.
    En MongoDB no es necesario crear cabeceras; los documentos se crean
    con la estructura correcta en crear_usuario().
    """
    return _conectar_coleccion_usuarios()


def obtener_usuario(username):
    """
    Retorna el documento del usuario como dict con las mismas keys que
    Google Sheets: username, password_hash, nombre_completo, es_admin,
    debe_cambiar_password.
    Los valores booleanos se normalizan a strings 'TRUE'/'FALSE' para
    mantener compatibilidad con service/auth_service.py.
    """
    coleccion = _conectar_coleccion_usuarios()
    if coleccion is None:
        return None
    try:
        doc = coleccion.find_one({"username": username}, {"_id": 0})
        if not doc:
            return None
        return _normalizar_usuario(doc)
    except Exception:
        return None


def actualizar_password(username, nuevo_hash, debe_cambiar=False):
    """
    Actualiza password_hash y debe_cambiar_password del usuario.
    Retorna True si se actualizó al menos un documento, False si no.
    """
    coleccion = _conectar_coleccion_usuarios()
    if coleccion is None:
        return False
    try:
        resultado = coleccion.update_one(
            {"username": username},
            {"$set": {
                "password_hash": nuevo_hash,
                "debe_cambiar_password": str(debe_cambiar).upper()
            }}
        )
        return resultado.matched_count > 0
    except Exception as e:
        st.error(f"Error al actualizar contraseña: {str(e)}")
        return False


def crear_usuario(username, password_hash, nombre_completo, es_admin=False, debe_cambiar=True):
    """
    Inserta un nuevo usuario. Retorna False si el usuario ya existe.
    Los booleanos se almacenan como strings 'TRUE'/'FALSE' para mantener
    compatibilidad con la lectura de Google Sheets.
    """
    coleccion = _conectar_coleccion_usuarios()
    if coleccion is None:
        return False
    try:
        if obtener_usuario(username):
            return False
        coleccion.insert_one({
            "username": username,
            "password_hash": password_hash,
            "nombre_completo": nombre_completo,
            "es_admin": str(es_admin).upper(),
            "debe_cambiar_password": str(debe_cambiar).upper()
        })
        return True
    except Exception as e:
        st.error(f"Error al crear usuario: {str(e)}")
        return False


def listar_usuarios():
    """
    Retorna una lista de dicts con los mismos campos que Google Sheets,
    excluyendo el _id de MongoDB.
    """
    coleccion = _conectar_coleccion_usuarios()
    if coleccion is None:
        return []
    try:
        return [_normalizar_usuario(doc) for doc in coleccion.find({}, {"_id": 0})]
    except Exception:
        return []


# ── Helpers ───────────────────────────────────────────────────────────────────

def _normalizar_usuario(doc):
    """
    Garantiza que las keys booleanas sean strings 'TRUE'/'FALSE',
    igual que Google Sheets, para que service/auth_service.py funcione
    sin modificaciones.
    """
    for campo in ("es_admin", "debe_cambiar_password"):
        if campo in doc and isinstance(doc[campo], bool):
            doc[campo] = str(doc[campo]).upper()
    return doc
