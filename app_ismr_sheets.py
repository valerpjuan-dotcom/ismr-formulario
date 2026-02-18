import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import pandas as pd
import hashlib
import time

# ── Configuración ─────────────────────────────────────────────────────────────
st.set_page_config(page_title="Sistema ISMR", page_icon="📋", layout="centered")

defaults = {
    "autenticado": False,
    "username": None,
    "nombre_completo": None,
    "debe_cambiar_password": False,
    "es_admin": False,
    "vista": None,
    "hechos": []
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ── Estilos ───────────────────────────────────────────────────────────────────
def inyectar_css_selector():
    st.markdown("""
    <style>
        .stApp { background: #0A0A0F; }
        #MainMenu, footer, header { visibility: hidden; }
    </style>
    """, unsafe_allow_html=True)

# ── Google Sheets base ─────────────────────────────────────────────────────────
def conectar_base_sheets():
    credentials_dict = st.secrets["gcp_service_account"]
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    credentials = Credentials.from_service_account_info(credentials_dict, scopes=scopes)
    client = gspread.authorize(credentials)
    spreadsheet = client.open(st.secrets.get("sheet_name", "ISMR_Casos"))
    return spreadsheet

# ── CONEXIÓN INDIVIDUAL ────────────────────────────────────────────────────────
def conectar_sheet_individual():
    ss = conectar_base_sheets()

    try:
        casos = ss.worksheet("Individual")
    except:
        casos = ss.add_worksheet("Individual", 1000, 20)
        casos.append_row([
            "Timestamp","OT-TE","Edad","Sexo","Departamento","Municipio",
            "Solicitante","Nivel de Riesgo","Observaciones",
            "Analista","Usuario Analista","ID_Caso"
        ])

    try:
        hechos = ss.worksheet("Hechos_Individual")
    except:
        hechos = ss.add_worksheet("Hechos_Individual", 1000, 20)
        hechos.append_row([
            "ID_Hecho","ID_Caso","OT-TE","Tipo de Hecho","Fecha",
            "Lugar","Autor","Descripcion","Analista","Usuario Analista"
        ])

    return casos, hechos, ss.url

# ── CONEXIÓN COLECTIVO ─────────────────────────────────────────────────────────
def conectar_sheet_colectivo():
    ss = conectar_base_sheets()

    try:
        casos = ss.worksheet("Colectivo")
    except:
        casos = ss.add_worksheet("Colectivo", 1000, 25)
        casos.append_row([
            "Timestamp","OT-TE","Tipo Colectivo","Numero Personas",
            "Grupo Etnico","Departamento","Municipio",
            "Solicitante","Nivel de Riesgo","Observaciones",
            "Analista","Usuario Analista","ID_Caso"
        ])

    try:
        hechos = ss.worksheet("Hechos_Colectivo")
    except:
        hechos = ss.add_worksheet("Hechos_Colectivo", 1000, 20)
        hechos.append_row([
            "ID_Hecho","ID_Caso","OT-TE","Tipo de Hecho","Fecha",
            "Lugar","Autor","Descripcion","Analista","Usuario Analista"
        ])

    return casos, hechos, ss.url

def obtener_siguiente_id(hoja):
    return max(len(hoja.get_all_values()), 1)

# ── FORMULARIO INDIVIDUAL ──────────────────────────────────────────────────────
def formulario_individual():
    hoja_casos, hoja_hechos, _ = conectar_sheet_individual()

    st.title("👤 Formulario Individual")

    ot_te = st.text_input("OT-TE *")
    edad  = st.number_input("Edad *", min_value=1, max_value=120)
    sexo  = st.selectbox("Sexo *", ["Hombre","Mujer","Otro","No Reporta"])
    departamento = st.text_input("Departamento *")
    municipio    = st.text_input("Municipio *")
    solicitante  = st.selectbox("Entidad Solicitante *", ["ARN","SESP","OTRO"])
    riesgo       = st.selectbox("Nivel de Riesgo *", ["ORDINARIO","EXTREMO","EXTRAORDINARIO"])
    obs          = st.text_area("Observaciones")

    if st.button("Registrar Caso Individual", type="primary"):
        id_caso = obtener_siguiente_id(hoja_casos)
        hoja_casos.append_row([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ot_te, edad, sexo, departamento, municipio,
            solicitante, riesgo, obs,
            st.session_state.nombre_completo,
            st.session_state.username,
            id_caso
        ])
        st.success("✅ Caso individual registrado")

# ── FORMULARIO COLECTIVO (INDEPENDIENTE) ───────────────────────────────────────
def formulario_colectivo():
    hoja_casos, hoja_hechos, _ = conectar_sheet_colectivo()

    st.title("👥 Formulario Colectivo")

    ot_te = st.text_input("OT-TE *")
    tipo_colectivo = st.selectbox(
        "Tipo de Colectivo *",
        ["Familia","Comunidad","Organización Social","Grupo Étnico","Otro"]
    )
    num_personas = st.number_input(
        "Número de personas afectadas *",
        min_value=2
    )
    grupo_etnico = st.selectbox(
        "Grupo Étnico",
        ["No aplica","Indígena","Afrodescendiente","Rrom","Raizal"]
    )
    departamento = st.text_input("Departamento *")
    municipio    = st.text_input("Municipio *")
    solicitante  = st.selectbox("Entidad Solicitante *", ["ARN","SESP","OTRO"])
    riesgo       = st.selectbox("Nivel de Riesgo *", ["ORDINARIO","EXTREMO","EXTRAORDINARIO"])
    obs          = st.text_area("Observaciones")

    if st.button("Registrar Caso Colectivo", type="primary"):
        id_caso = obtener_siguiente_id(hoja_casos)
        hoja_casos.append_row([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ot_te, tipo_colectivo, num_personas,
            grupo_etnico, departamento, municipio,
            solicitante, riesgo, obs,
            st.session_state.nombre_completo,
            st.session_state.username,
            id_caso
        ])
        st.success("✅ Caso colectivo registrado")

# ── AUTENTICACIÓN (SIN CAMBIOS FUNCIONALES) ────────────────────────────────────
def verificar_credenciales(username, password):
    credentials_dict = st.secrets["gcp_service_account"]
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    credentials = Credentials.from_service_account_info(credentials_dict, scopes=scopes)
    client = gspread.authorize(credentials)
    ss = client.open(st.secrets.get("sheet_usuarios","ISMR_Usuarios"))
    ws = ss.sheet1

    for u in ws.get_all_records():
        if u["username"] == username:
            if hashlib.sha256(password.encode()).hexdigest() == u["password_hash"]:
                return True, u["nombre_completo"], False, u["es_admin"] == "TRUE"
    return False, None, False, False

def login_page():
    st.title("🔐 Acceso ISMR")
    with st.form("login"):
        u = st.text_input("Usuario")
        p = st.text_input("Contraseña", type="password")
        if st.form_submit_button("Ingresar"):
            ok, nombre, _, admin = verificar_credenciales(u, p)
            if ok:
                st.session_state.autenticado = True
                st.session_state.username = u
                st.session_state.nombre_completo = nombre
                st.session_state.es_admin = admin
                st.rerun()
            else:
                st.error("Credenciales incorrectas")

def logout():
    for k in defaults:
        st.session_state[k] = defaults[k]
    st.rerun()

# ── MAIN ──────────────────────────────────────────────────────────────────────
def main():
    if not st.session_state.autenticado:
        login_page()
        return

    st.sidebar.title("Sistema ISMR")
    st.sidebar.write(st.session_state.nombre_completo)

    opcion = st.sidebar.radio(
        "Menú",
        ["Inicio","Formulario Individual","Formulario Colectivo"]
    )

    if st.sidebar.button("Cerrar sesión"):
        logout()

    if opcion == "Formulario Individual":
        formulario_individual()
    elif opcion == "Formulario Colectivo":
        formulario_colectivo()
    else:
        st.info("Selecciona un formulario")

if __name__ == "__main__":
    main()
