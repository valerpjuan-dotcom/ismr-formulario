import streamlit as st
import hashlib
from data.usuarios_repo import obtener_usuario
from configuration.settings import defaults


def obtener_siguiente_id(hoja):
    return max(len(hoja.get_all_values()), 1)


def verificar_credenciales(username, password):
    usuario = obtener_usuario(username)
    if not usuario: return False, None, False, False
    try:
        if 'password_hash' not in usuario:
            st.error("La hoja de usuarios no tiene el formato correcto.")
            return False, None, False, False
        phash = hashlib.sha256(password.encode()).hexdigest()
        if phash == usuario['password_hash']:
            debe_cambiar = str(usuario.get('debe_cambiar_password','FALSE')).upper() == 'TRUE'
            es_admin     = str(usuario.get('es_admin','FALSE')).upper() == 'TRUE'
            return True, usuario.get('nombre_completo', username), debe_cambiar, es_admin
        return False, None, False, False
    except Exception as e:
        st.error(f"Error en verificación: {str(e)}")
        return False, None, False, False


def logout():
    for key in defaults: st.session_state[key] = defaults[key]
    st.rerun()
