import hashlib
import streamlit as st
import bcrypt
from pymongo import MongoClient


@st.cache_resource
def _get_client():
    uri = st.secrets["mongodb"]["uri"].split("?")[0]
    return MongoClient(
        uri,
        tls=True,
        tlsAllowInvalidCertificates=False,
        serverSelectionTimeoutMS=10000,
        connectTimeoutMS=10000,
        socketTimeoutMS=10000,
        retryWrites=True,
        appName="ISMR",
    )


def _conectar_coleccion_usuarios():
    try:
        db_name = st.secrets["mongodb"].get("db_name", "ismr")
        db = _get_client()[db_name]
        coleccion = db["usuarios"]
        coleccion.create_index("username", unique=True, background=True)
        return coleccion
    except Exception as e:
        st.error(f"Error al conectar MongoDB (usuarios): {str(e)}")
        return None


def conectar_sheet_usuarios():
    return _conectar_coleccion_usuarios()


def obtener_usuario(username):
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


def hashear_password(password: str) -> str:
    """
    Genera un hash bcrypt de la contraseña.
    Retorna el hash como string (bcrypt ya incluye la sal internamente).
    """
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12)).decode()


def verificar_password(password: str, hash_guardado: str) -> bool:
    """
    Verifica una contraseña contra su hash.
    Soporta tanto bcrypt (nuevo) como SHA-256 (legado) para migración automática.
    Retorna (es_valida, es_sha256_legado).
    """
    # Detectar si es bcrypt por el prefijo $2b$ o $2a$
    if hash_guardado.startswith("$2b$") or hash_guardado.startswith("$2a$"):
        try:
            es_valida = bcrypt.checkpw(password.encode(), hash_guardado.encode())
            return es_valida, False
        except Exception:
            return False, False
    else:
        # Hash SHA-256 legado — verificar y marcar para migración
        sha_hash = hashlib.sha256(password.encode()).hexdigest()
        return sha_hash == hash_guardado, True


def actualizar_password(username, nuevo_hash, debe_cambiar=False):
    """
    Actualiza password_hash. Acepta tanto hash bcrypt (str con $2b$)
    como hash SHA-256 legado para compatibilidad durante migración.
    """
    coleccion = _conectar_coleccion_usuarios()
    if coleccion is None:
        return False
    try:
        resultado = coleccion.update_one(
            {"username": username},
            {"$set": {
                "password_hash": nuevo_hash,
                "debe_cambiar_password": "FALSE"
            }}
        )
        return resultado.matched_count > 0
    except Exception as e:
        st.error(f"Error al actualizar contraseña: {str(e)}")
        return False


def _migrar_a_bcrypt(username: str, password: str) -> None:
    """
    Migra silenciosamente un hash SHA-256 a bcrypt al momento del login.
    El usuario no nota ningún cambio en su experiencia.
    """
    try:
        nuevo_hash = hashear_password(password)
        coleccion = _conectar_coleccion_usuarios()
        if coleccion:
            coleccion.update_one(
                {"username": username},
                {"$set": {"password_hash": nuevo_hash}}
            )
    except Exception:
        pass  # Si falla la migración, no interrumpir el login


def crear_usuario(username, password_plano, nombre_completo, es_admin=False, debe_cambiar=True, email=None):
    """
    Inserta un nuevo usuario hasheando la contraseña con bcrypt.
    Acepta la contraseña en texto plano (no el hash) para aplicar bcrypt internamente.
    El email se infiere automáticamente del username si no se provee.
    """
    coleccion = _conectar_coleccion_usuarios()
    if coleccion is None:
        return False
    try:
        if obtener_usuario(username):
            return False
        email_final = email or f"{username.strip().lower()}@unp.gov.co"
        # Hashear con bcrypt
        hash_bcrypt = hashear_password(password_plano)
        coleccion.insert_one({
            "username": username,
            "password_hash": hash_bcrypt,
            "nombre_completo": nombre_completo,
            "es_admin": "TRUE" if es_admin else "FALSE",
            "debe_cambiar_password": "TRUE" if debe_cambiar else "FALSE",
            "email": email_final,
        })
        return True
    except Exception as e:
        st.error(f"Error al crear usuario: {str(e)}")
        return False


def listar_usuarios():
    coleccion = _conectar_coleccion_usuarios()
    if coleccion is None:
        return []
    try:
        return [_normalizar_usuario(doc) for doc in coleccion.find({}, {"_id": 0})]
    except Exception:
        return []


def usuario_existe(username: str) -> bool:
    """Retorna True si el username existe en la base de datos."""
    return obtener_usuario(username) is not None


# ── Helpers ───────────────────────────────────────────────────────────────────

def _normalizar_usuario(doc):
    for campo in ("es_admin", "debe_cambiar_password"):
        valor = doc.get(campo, False)
        if isinstance(valor, bool):
            doc[campo] = "TRUE" if valor else "FALSE"
        elif isinstance(valor, str):
            doc[campo] = "TRUE" if valor.strip().upper() == "TRUE" else "FALSE"
        else:
            doc[campo] = "FALSE"
    if "email" not in doc or not doc["email"]:
        doc["email"] = f"{doc.get('username','').strip().lower()}@unp.gov.co"
    return doc
