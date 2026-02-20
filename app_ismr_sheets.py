import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import pandas as pd
import hashlib
import time

st.set_page_config(page_title="Sistema ISMR", page_icon="📋", layout="centered")

# =============================================================================
# CONFIGURACIÓN Y ESTADO DE SESIÓN
# =============================================================================
defaults = {
    "autenticado": False, "username": None, "nombre_completo": None,
    "debe_cambiar_password": False, "es_admin": False, "vista": None,
    "hechos_individual": [], "hechos_colectivo": [],
    "antecedentes_individual": [], "antecedentes_colectivo": [],
    "perfil_antiguo_individual": [], "perfil_antiguo_colectivo": [],
    "desplazamientos_individual": [], "desplazamientos_colectivo": [],
    "verificaciones_individual": [], "verificaciones_colectivo": [],
    "form_submitted_individual": False, "form_submitted_colectivo": False,
}
for key, val in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = val

# Cache para datos de Google Sheets
if "casos_individual_cache" not in st.session_state:
    st.session_state.casos_individual_cache = {"timestamp": None, "data": []}
if "casos_colectivo_cache" not in st.session_state:
    st.session_state.casos_colectivo_cache = {"timestamp": None, "data": []}

# =============================================================================
# CSS
# =============================================================================
def inyectar_css_selector():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=DM+Sans:wght@300;400;500;600&display=swap');
        .stApp { background: #0A0A0F; }
        #MainMenu, footer, header { visibility: hidden; }
        .btn-individual > button, .btn-colectivo > button {
            width: 100% !important; min-height: 340px !important;
            border-radius: 4px !important; border: 1px solid !important;
            transition: all 0.3s ease !important;
            font-family: 'Bebas Neue', sans-serif !important;
            letter-spacing: 3px !important; font-size: 28px !important;
        }
        .btn-individual > button {
            background: linear-gradient(145deg, #1A1A2E 0%, #16213E 50%, #0F3460 100%) !important;
            border-color: rgba(79, 139, 255, 0.3) !important; color: #E8EEFF !important;
        }
        .btn-individual > button:hover {
            border-color: rgba(79, 139, 255, 0.7) !important;
            box-shadow: 0 20px 60px rgba(79, 139, 255, 0.2) !important;
        }
        .btn-colectivo > button {
            background: linear-gradient(145deg, #1A1A1A 0%, #1E2A1E 50%, #0A3D0A 100%) !important;
            border-color: rgba(74, 222, 128, 0.25) !important; color: #E8FFE8 !important;
        }
        .btn-colectivo > button:hover {
            border-color: rgba(74, 222, 128, 0.6) !important;
            box-shadow: 0 20px 60px rgba(74, 222, 128, 0.15) !important;
        }
        .stButton > button[kind="secondary"] {
            background: transparent !important; border: 1px solid #333 !important; color: #666 !important;
        }
        div[data-testid="stForm"] {
            border: 1px solid #333;
            padding: 20px;
            border-radius: 4px;
            background: rgba(255,255,255,0.02);
        }
    </style>
    """, unsafe_allow_html=True)

# =============================================================================
# GOOGLE SHEETS — CONEXIÓN OPTIMIZADA
# =============================================================================
@st.cache_resource(ttl=300)
def _get_credentials():
    """Cachea las credenciales de Google"""
    credentials_dict = st.secrets["gcp_service_account"]
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    return Credentials.from_service_account_info(credentials_dict, scopes=scopes)

@st.cache_resource(ttl=300)
def _get_client():
    """Cachea el cliente de Google Sheets"""
    creds = _get_credentials()
    return gspread.authorize(creds)

@st.cache_resource(ttl=300)
def _get_spreadsheet():
    """Cachea el spreadsheet principal"""
    client = _get_client()
    return client.open(st.secrets.get("sheet_name", "ISMR_Casos"))

@st.cache_resource(ttl=300)
def _get_spreadsheet_usuarios():
    """Cachea el spreadsheet de usuarios"""
    client = _get_client()
    sheet_name = st.secrets.get("sheet_usuarios", "ISMR_Usuarios")
    try:
        return client.open(sheet_name)
    except:
        spreadsheet = client.create(sheet_name)
        creds_dict = st.secrets["gcp_service_account"]
        spreadsheet.share(creds_dict["client_email"], perm_type='user', role='writer')
        return spreadsheet

# =============================================================================
# UTILIDADES PARA HOJAS
# =============================================================================
def _obtener_o_crear_hoja(spreadsheet, titulo, encabezados):
    """Obtiene una hoja o la crea si no existe (sin sleeps)"""
    try:
        hoja = spreadsheet.worksheet(titulo)
    except gspread.exceptions.WorksheetNotFound:
        hoja = spreadsheet.add_worksheet(title=titulo, rows="1000", cols="20")
    
    # Verificar encabezados solo una vez
    cache_key = f"_headers_{titulo}"
    if not st.session_state.get(cache_key):
        try:
            valores = hoja.get_all_values()
            if not valores:
                hoja.append_row(encabezados)
            else:
                encabezados_actuales = valores[0]
                faltantes = [col for col in encabezados if col not in encabezados_actuales]
                if faltantes:
                    col_inicio = len(encabezados_actuales) + 1
                    for i, nombre_col in enumerate(faltantes):
                        hoja.update_cell(1, col_inicio + i, nombre_col)
            st.session_state[cache_key] = True
        except Exception as e:
            if "429" not in str(e):  # Ignorar rate limiting
                st.warning(f"Error con encabezados de {titulo}: {e}")
    
    return hoja

def obtener_siguiente_id(hoja):
    """Obtiene el siguiente ID para una hoja"""
    return max(len(hoja.get_all_values()), 1)

@st.cache_data(ttl=60)
def obtener_casos_existentes_cache(_hoja, tipo):
    """Cachea los OT-TE existentes por 60 segundos"""
    try:
        todas_filas = _hoja.get_all_values()
        return [fila[1] for fila in todas_filas[1:] if len(fila) > 1]
    except:
        return []

# =============================================================================
# GOOGLE SHEETS — INDIVIDUAL (OPTIMIZADO)
# =============================================================================
@st.cache_resource(ttl=300)
def conectar_sheets_individual():
    """Conexión optimizada a hojas individuales"""
    try:
        spreadsheet = _get_spreadsheet()
        
        hojas = {
            'casos': _obtener_o_crear_hoja(spreadsheet, "Individual", [
                "Timestamp", "OT-TE", "Edad", "Sexo", "Departamento", "Municipio",
                "Solicitante", "Nivel de Riesgo", "Observaciones",
                "Analista", "Usuario Analista", "ID_Caso", "Tipo de Estudio", "Año OT", "Mes OT"
            ]),
            'hechos': _obtener_o_crear_hoja(spreadsheet, "Hechos_Individual", [
                "ID_Hecho", "ID_Caso", "OT-TE", "Tipo de Hecho",
                "Fecha del Hecho", "Lugar", "Autor", "Descripcion",
                "Analista", "Usuario Analista"
            ]),
            'antecedentes': _obtener_o_crear_hoja(spreadsheet, "Antecedentes_Individual", [
                "ID_Antecedente", "ID_Caso", "OT-TE",
                "Registra OT Antecedentes", "Registra Resoluciones o Medidas Vigentes",
                "Analista", "Usuario Analista"
            ]),
            'perfil': _obtener_o_crear_hoja(spreadsheet, "PerfilAntiguo_Individual", [
                "ID_Perfil", "ID_Caso", "OT-TE",
                "Modo de Participacion", "Lugar de Acreditacion",
                "Analista", "Usuario Analista"
            ]),
            'desplazamientos': _obtener_o_crear_hoja(spreadsheet, "Desplazamientos_Individual", [
                "ID_Desplazamiento", "ID_Caso", "OT-TE",
                "Motivo Desplazamiento", "Medio de Transporte",
                "Departamento Origen", "Departamento Destino",
                "Analista", "Usuario Analista"
            ]),
            'verificaciones': _obtener_o_crear_hoja(spreadsheet, "Verificaciones_Individual", [
                "ID_Verificacion", "ID_Caso", "OT-TE",
                "Fuente", "Nombre Fuente",
                "Analista", "Usuario Analista"
            ])
        }
        
        return (hojas['casos'], hojas['hechos'], hojas['antecedentes'],
                hojas['perfil'], hojas['desplazamientos'], hojas['verificaciones'],
                spreadsheet.url)
    except Exception as e:
        st.error(f"Error al conectar sheets individuales: {e}")
        return None, None, None, None, None, None, None

# =============================================================================
# GOOGLE SHEETS — COLECTIVO (OPTIMIZADO)
# =============================================================================
@st.cache_resource(ttl=300)
def conectar_sheets_colectivo():
    """Conexión optimizada a hojas colectivas"""
    try:
        spreadsheet = _get_spreadsheet()
        
        hojas = {
            'casos': _obtener_o_crear_hoja(spreadsheet, "Colectivo", [
                "Timestamp", "OT-TE", "Nombre Colectivo", "Fecha Creacion Colectivo",
                "Sector", "Departamento", "Municipio",
                "Analista", "Usuario Analista", "ID_Caso"
            ]),
            'hechos': _obtener_o_crear_hoja(spreadsheet, "Hechos_Colectivo", [
                "ID_Hecho", "ID_Caso", "OT-TE", "Tipo de Hecho",
                "Fecha del Hecho", "Lugar", "Autor", "Descripcion",
                "Analista", "Usuario Analista"
            ]),
            'antecedentes': _obtener_o_crear_hoja(spreadsheet, "Antecedentes_Colectivo", [
                "ID_Antecedente", "ID_Caso", "OT-TE",
                "Registra OT Antecedentes", "Registra Resoluciones o Medidas Vigentes",
                "Analista", "Usuario Analista"
            ]),
            'perfil': _obtener_o_crear_hoja(spreadsheet, "PerfilAntiguo_Colectivo", [
                "ID_Perfil", "ID_Caso", "OT-TE",
                "Modo de Participacion", "Lugar de Acreditacion",
                "Analista", "Usuario Analista"
            ]),
            'desplazamientos': _obtener_o_crear_hoja(spreadsheet, "Desplazamientos_Colectivo", [
                "ID_Desplazamiento", "ID_Caso", "OT-TE",
                "Motivo Desplazamiento", "Medio de Transporte",
                "Departamento Origen", "Departamento Destino",
                "Analista", "Usuario Analista"
            ]),
            'verificaciones': _obtener_o_crear_hoja(spreadsheet, "Verificaciones_Colectivo", [
                "ID_Verificacion", "ID_Caso", "OT-TE",
                "Fuente", "Nombre Fuente",
                "Analista", "Usuario Analista"
            ])
        }
        
        return (hojas['casos'], hojas['hechos'], hojas['antecedentes'],
                hojas['perfil'], hojas['desplazamientos'], hojas['verificaciones'],
                spreadsheet.url)
    except Exception as e:
        st.error(f"Error al conectar sheets colectivos: {e}")
        return None, None, None, None, None, None, None

# =============================================================================
# GOOGLE SHEETS — USUARIOS
# =============================================================================
@st.cache_resource(ttl=300)
def conectar_sheet_usuarios():
    """Conexión cacheada a hoja de usuarios"""
    try:
        spreadsheet = _get_spreadsheet_usuarios()
        try:
            worksheet = spreadsheet.worksheet("Usuarios")
        except:
            worksheet = spreadsheet.add_worksheet(title="Usuarios", rows="100", cols="5")
        
        # Verificar encabezados
        if not worksheet.row_values(1):
            worksheet.append_row(["username", "password_hash", "nombre_completo",
                                 "es_admin", "debe_cambiar_password"])
        return worksheet
    except Exception as e:
        st.error(f"Error al conectar sheet de usuarios: {e}")
        return None

def obtener_usuario(username):
    """Obtiene usuario por username (con cache local)"""
    ws = conectar_sheet_usuarios()
    if not ws:
        return None
    try:
        # Cache simple en memoria
        cache_key = f"user_{username}"
        if cache_key in st.session_state:
            return st.session_state[cache_key]
        
        for u in ws.get_all_records():
            if u.get("username") == username:
                st.session_state[cache_key] = u
                return u
        return None
    except Exception:
        return None

def actualizar_password(username, nuevo_hash, debe_cambiar=False):
    ws = conectar_sheet_usuarios()
    if not ws:
        return False
    try:
        datos = ws.get_all_values()
        for idx, fila in enumerate(datos[1:], start=2):
            if fila[0] == username:
                ws.update_cell(idx, 2, nuevo_hash)
                ws.update_cell(idx, 5, str(debe_cambiar).upper())
                # Limpiar cache
                st.session_state.pop(f"user_{username}", None)
                return True
        return False
    except Exception as e:
        st.error(f"Error al actualizar contraseña: {e}")
        return False

def crear_usuario(username, password_hash, nombre_completo, es_admin=False, debe_cambiar=True):
    ws = conectar_sheet_usuarios()
    if not ws:
        return False
    try:
        if obtener_usuario(username):
            return False
        ws.append_row([username, password_hash, nombre_completo,
                      str(es_admin).upper(), str(debe_cambiar).upper()])
        return True
    except Exception as e:
        st.error(f"Error al crear usuario: {e}")
        return False

@st.cache_data(ttl=60)
def listar_usuarios_cache():
    """Lista usuarios con cache de 60 segundos"""
    ws = conectar_sheet_usuarios()
    if not ws:
        return []
    try:
        return ws.get_all_records()
    except Exception:
        return []

# =============================================================================
# BORRADORES (OPTIMIZADOS)
# =============================================================================
@st.cache_resource(ttl=300)
def _conectar_hoja_borradores():
    """Conexión cacheada a hoja de borradores"""
    try:
        spreadsheet = _get_spreadsheet()
        try:
            hoja = spreadsheet.worksheet("Borradores")
        except gspread.exceptions.WorksheetNotFound:
            hoja = spreadsheet.add_worksheet(title="Borradores", rows="500", cols="10")
        
        # Verificar encabezados
        if not hoja.row_values(1):
            hoja.append_row(["username", "tipo", "timestamp_guardado", "campos_json", "listas_json"])
        return hoja
    except Exception:
        return None

def guardar_borrador(tipo, campos):
    import json
    hoja = _conectar_hoja_borradores()
    if not hoja:
        return False
    try:
        username = st.session_state.username
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        campos_json = json.dumps(campos, ensure_ascii=False)
        listas = {
            "hechos": st.session_state.get(f"hechos_{tipo}", []),
            "antecedentes": st.session_state.get(f"antecedentes_{tipo}", []),
            "perfil_antiguo": st.session_state.get(f"perfil_antiguo_{tipo}", []),
            "desplazamientos": st.session_state.get(f"desplazamientos_{tipo}", []),
            "verificaciones": st.session_state.get(f"verificaciones_{tipo}", []),
        }
        listas_json = json.dumps(listas, ensure_ascii=False)
        
        datos = hoja.get_all_values()
        for idx, fila in enumerate(datos[1:], start=2):
            if len(fila) >= 2 and fila[0] == username and fila[1] == tipo:
                hoja.update(f"A{idx}:E{idx}", [[username, tipo, timestamp, campos_json, listas_json]])
                return True
        hoja.append_row([username, tipo, timestamp, campos_json, listas_json])
        return True
    except Exception as e:
        st.error(f"Error al guardar borrador: {e}")
        return False

def cargar_borrador(tipo):
    import json
    hoja = _conectar_hoja_borradores()
    if not hoja:
        return None, None, None
    try:
        username = st.session_state.username
        for fila in hoja.get_all_values()[1:]:
            if len(fila) >= 5 and fila[0] == username and fila[1] == tipo:
                campos = json.loads(fila[3]) if fila[3] else {}
                listas_raw = json.loads(fila[4]) if fila[4] else {}
                if isinstance(listas_raw, list):
                    listas = {"hechos": listas_raw}
                else:
                    listas = listas_raw
                return campos, listas, fila[2]
        return None, None, None
    except Exception as e:
        st.error(f"Error al cargar borrador: {e}")
        return None, None, None

def eliminar_borrador(tipo):
    hoja = _conectar_hoja_borradores()
    if not hoja:
        return
    try:
        username = st.session_state.username
        datos = hoja.get_all_values()
        for idx, fila in enumerate(datos[1:], start=2):
            if len(fila) >= 2 and fila[0] == username and fila[1] == tipo:
                hoja.delete_rows(idx)
                return
    except Exception as e:
        st.error(f"Error al eliminar borrador: {e}")

# =============================================================================
# SECCIONES REUTILIZABLES (OPTIMIZADAS CON FORMS)
# =============================================================================
def seccion_antecedentes(tipo):
    key_list = f"antecedentes_{tipo}"
    lista = st.session_state[key_list]
    
    st.markdown("---")
    st.subheader("📁 Antecedentes")
    st.caption("Opcional. Registra antecedentes asociados a este caso.")
    
    # Mostrar antecedentes existentes
    for i, ant in enumerate(lista):
        with st.container(border=True):
            col_tit, col_del = st.columns([5, 1])
            with col_tit:
                st.markdown(f"**Antecedente #{i+1}**")
            with col_del:
                if st.button("🗑️", key=f"del_ant_{tipo}_{i}"):
                    lista.pop(i)
                    st.rerun()
            c1, c2 = st.columns(2)
            with c1:
                st.write(f"📋 **Registra OT antecedentes:** {ant['registra_ot']}")
            with c2:
                st.write(f"📋 **Registra resoluciones/medidas vigentes:** {ant['registra_resoluciones']}")
    
    # Formulario para agregar
    with st.form(key=f"form_antecedente_{tipo}", clear_on_submit=True):
        st.markdown("**Agregar nuevo antecedente**")
        c1, c2 = st.columns(2)
        with c1:
            registra_ot = st.radio("Registra OT antecedentes", ["Sí", "No"], horizontal=True, key=f"ant_ot_{tipo}")
        with c2:
            registra_res = st.radio("Registra resoluciones o medidas vigentes", ["Sí", "No"], horizontal=True, key=f"ant_res_{tipo}")
        
        if st.form_submit_button("➕ Agregar antecedente", use_container_width=True):
            lista.append({"registra_ot": registra_ot, "registra_resoluciones": registra_res})
            st.success("✅ Antecedente agregado")
            st.rerun()

def seccion_perfil_antiguo(tipo):
    key_list = f"perfil_antiguo_{tipo}"
    lista = st.session_state[key_list]
    
    st.markdown("---")
    st.subheader("🗂️ Perfil Antiguo")
    st.caption("Opcional. Registra información de perfil anterior.")
    
    for i, perfil in enumerate(lista):
        with st.container(border=True):
            col_tit, col_del = st.columns([5, 1])
            with col_tit:
                st.markdown(f"**Perfil #{i+1}**")
            with col_del:
                if st.button("🗑️", key=f"del_perf_{tipo}_{i}"):
                    lista.pop(i)
                    st.rerun()
            c1, c2 = st.columns(2)
            with c1:
                st.write(f"🎭 **Modo de participación:** {perfil['modo_participacion']}")
            with c2:
                st.write(f"📍 **Lugar de acreditación:** {perfil['lugar_acreditacion']}")
    
    with st.form(key=f"form_perfil_{tipo}", clear_on_submit=True):
        st.markdown("**Agregar nuevo perfil**")
        c1, c2 = st.columns(2)
        with c1:
            modo = st.text_input("Modo de Participación *", placeholder="Ej: Combatiente, Miliciano...", key=f"perf_modo_{tipo}")
        with c2:
            lugar = st.text_input("Lugar de Acreditación *", placeholder="Ej: Bogotá D.C.", key=f"perf_lugar_{tipo}")
        
        if st.form_submit_button("➕ Agregar perfil", use_container_width=True):
            errores = []
            if not modo.strip():
                errores.append("El modo de participación es obligatorio")
            if not lugar.strip():
                errores.append("El lugar de acreditación es obligatorio")
            if errores:
                for e in errores:
                    st.error(f"• {e}")
            else:
                lista.append({"modo_participacion": modo.strip(), "lugar_acreditacion": lugar.strip()})
                st.success("✅ Perfil agregado")
                st.rerun()

def seccion_desplazamientos(tipo):
    key_list = f"desplazamientos_{tipo}"
    lista = st.session_state[key_list]
    
    st.markdown("---")
    st.subheader("🚗 Desplazamientos")
    st.caption("Opcional. Registra desplazamientos asociados a este caso.")
    
    for i, desp in enumerate(lista):
        with st.container(border=True):
            col_tit, col_del = st.columns([5, 1])
            with col_tit:
                st.markdown(f"**Desplazamiento #{i+1}**")
            with col_del:
                if st.button("🗑️", key=f"del_desp_{tipo}_{i}"):
                    lista.pop(i)
                    st.rerun()
            c1, c2 = st.columns(2)
            with c1:
                st.write(f"❓ **Motivo:** {desp['motivo']}")
                st.write(f"🚌 **Medio de transporte:** {desp['medio']}")
            with c2:
                st.write(f"📤 **Departamento origen:** {desp['depto_origen']}")
                st.write(f"📥 **Departamento destino:** {desp['depto_destino']}")
    
    with st.form(key=f"form_desplazamiento_{tipo}", clear_on_submit=True):
        st.markdown("**Agregar nuevo desplazamiento**")
        c1, c2 = st.columns(2)
        with c1:
            motivo = st.text_input("Motivo Desplazamiento *", placeholder="Ej: Amenaza directa", key=f"desp_motivo_{tipo}")
            depto_origen = st.text_input("Departamento de Origen *", placeholder="Ej: Antioquia", key=f"desp_origen_{tipo}")
        with c2:
            medio = st.text_input("Medio de Transporte *", placeholder="Ej: Bus, a pie...", key=f"desp_medio_{tipo}")
            depto_destino = st.text_input("Departamento Destino *", placeholder="Ej: Bogotá D.C.", key=f"desp_destino_{tipo}")
        
        if st.form_submit_button("➕ Agregar desplazamiento", use_container_width=True):
            errores = []
            if not motivo.strip():
                errores.append("El motivo es obligatorio")
            if not medio.strip():
                errores.append("El medio de transporte es obligatorio")
            if not depto_origen.strip():
                errores.append("El departamento de origen es obligatorio")
            if not depto_destino.strip():
                errores.append("El departamento destino es obligatorio")
            if errores:
                for e in errores:
                    st.error(f"• {e}")
            else:
                lista.append({
                    "motivo": motivo.strip(), "medio": medio.strip(),
                    "depto_origen": depto_origen.strip(), "depto_destino": depto_destino.strip()
                })
                st.success("✅ Desplazamiento agregado")
                st.rerun()

def seccion_verificaciones(tipo):
    key_list = f"verificaciones_{tipo}"
    lista = st.session_state[key_list]
    
    st.markdown("---")
    st.subheader("✅ Verificaciones")
    st.caption("Opcional. Registra fuentes de verificación para este caso.")
    
    for i, ver in enumerate(lista):
        with st.container(border=True):
            col_tit, col_del = st.columns([5, 1])
            with col_tit:
                st.markdown(f"**Verificación #{i+1}**")
            with col_del:
                if st.button("🗑️", key=f"del_ver_{tipo}_{i}"):
                    lista.pop(i)
                    st.rerun()
            c1, c2 = st.columns(2)
            with c1:
                st.write(f"🔎 **Fuente:** {ver['fuente']}")
            with c2:
                st.write(f"👤 **Nombre fuente:** {ver['nombre_fuente']}")
    
    with st.form(key=f"form_verificacion_{tipo}", clear_on_submit=True):
        st.markdown("**Agregar nueva verificación**")
        c1, c2 = st.columns(2)
        with c1:
            fuente = st.text_input("Fuente *", placeholder="Ej: Entrevista, Documento oficial...", key=f"ver_fuente_{tipo}")
        with c2:
            nombre_fuente = st.text_input("Nombre Fuente *", placeholder="Ej: Juan Pérez, Alcaldía de...", key=f"ver_nombre_{tipo}")
        
        if st.form_submit_button("➕ Agregar verificación", use_container_width=True):
            errores = []
            if not fuente.strip():
                errores.append("La fuente es obligatoria")
            if not nombre_fuente.strip():
                errores.append("El nombre de la fuente es obligatorio")
            if errores:
                for e in errores:
                    st.error(f"• {e}")
            else:
                lista.append({"fuente": fuente.strip(), "nombre_fuente": nombre_fuente.strip()})
                st.success("✅ Verificación agregada")
                st.rerun()

def seccion_hechos(tipo):
    """Sección de hechos (común para individual y colectivo)"""
    key_list = f"hechos_{tipo}"
    lista = st.session_state[key_list]
    
    st.markdown("---")
    st.subheader("⚠️ Hechos de Riesgo")
    st.caption("Opcional. Agrega uno o varios hechos de riesgo asociados a este caso.")
    
    for i, hecho in enumerate(lista):
        with st.container(border=True):
            col_tit, col_del = st.columns([5, 1])
            with col_tit:
                st.markdown(f"**Hecho #{i+1} — {hecho['tipo']}**")
            with col_del:
                if st.button("🗑️", key=f"del_{tipo}_{i}"):
                    lista.pop(i)
                    st.rerun()
            c1, c2 = st.columns(2)
            with c1:
                st.write(f"📅 **Fecha:** {hecho['fecha']}")
                st.write(f"📍 **Lugar:** {hecho['lugar']}")
            with c2:
                st.write(f"👤 **Autor:** {hecho['autor']}")
            st.write(f"📄 **Descripción:** {hecho['descripcion']}")
    
    with st.form(key=f"form_hecho_{tipo}", clear_on_submit=True):
        st.markdown("**Agregar nuevo hecho**")
        c1, c2 = st.columns(2)
        with c1:
            tipo_hecho = st.selectbox("Tipo de Hecho *", [
                "Seleccione...", "Amenaza", "Atentado", "Desplazamiento forzado",
                "Homicidio", "Secuestro", "Extorsión", "Reclutamiento forzado",
                "Violencia sexual", "Confinamiento", "Otro"
            ], key=f"tipo_hecho_{tipo}")
            fecha_hecho = st.date_input("Fecha del Hecho *", key=f"fecha_hecho_{tipo}")
            lugar_hecho = st.text_input("Lugar donde ocurrió *", placeholder="Municipio, vereda, barrio...", key=f"lugar_hecho_{tipo}")
        with c2:
            autor_hecho = st.text_input("Autor *", placeholder="Grupo armado, persona, etc.", key=f"autor_hecho_{tipo}")
            descripcion_hecho = st.text_area("Descripción *", placeholder="Describe brevemente el hecho...", height=122, key=f"desc_hecho_{tipo}")
        
        if st.form_submit_button("➕ Agregar este hecho", use_container_width=True):
            errores = []
            if tipo_hecho == "Seleccione...":
                errores.append("Selecciona el tipo de hecho")
            if not lugar_hecho.strip():
                errores.append("El lugar es obligatorio")
            if not autor_hecho.strip():
                errores.append("El autor es obligatorio")
            if not descripcion_hecho.strip():
                errores.append("La descripción es obligatoria")
            if errores:
                for e in errores:
                    st.error(f"• {e}")
            else:
                lista.append({
                    "tipo": tipo_hecho, "fecha": str(fecha_hecho),
                    "lugar": lugar_hecho.strip(), "autor": autor_hecho.strip(),
                    "descripcion": descripcion_hecho.strip()
                })
                st.success("✅ Hecho agregado")
                st.rerun()

# =============================================================================
# AUTENTICACIÓN
# =============================================================================
def verificar_credenciales(username, password):
    usuario = obtener_usuario(username)
    if not usuario:
        return False, None, False, False
    try:
        phash = hashlib.sha256(password.encode()).hexdigest()
        if phash == usuario.get("password_hash", ""):
            debe_cambiar = str(usuario.get("debe_cambiar_password", "FALSE")).upper() == "TRUE"
            es_admin = str(usuario.get("es_admin", "FALSE")).upper() == "TRUE"
            return True, usuario.get("nombre_completo", username), debe_cambiar, es_admin
        return False, None, False, False
    except Exception as e:
        st.error(f"Error en verificación: {e}")
        return False, None, False, False

def logout():
    for key in defaults:
        st.session_state[key] = defaults[key]
    st.rerun()

# =============================================================================
# PANTALLAS
# =============================================================================
def login_page():
    st.title("🔐 Acceso al Sistema ISMR")
    st.markdown("---")
    st.info("👋 Identifícate para acceder al sistema")
    
    with st.form("login_form"):
        username = st.text_input("Usuario", placeholder="tu.usuario")
        password = st.text_input("Contraseña", type="password")
        submit = st.form_submit_button("🔓 Iniciar Sesión", use_container_width=True, type="primary")
        
        if submit:
            if username and password:
                ok, nombre, cambiar, admin = verificar_credenciales(username, password)
                if ok:
                    st.session_state.autenticado = True
                    st.session_state.username = username
                    st.session_state.nombre_completo = nombre
                    st.session_state.debe_cambiar_password = cambiar
                    st.session_state.es_admin = admin
                    st.session_state.hechos_individual = []
                    st.session_state.hechos_colectivo = []
                    st.rerun()
                else:
                    st.error("❌ Usuario o contraseña incorrectos")
            else:
                st.warning("⚠️ Por favor completa todos los campos")
    
    st.markdown("---")
    st.caption("🔒 Si tienes problemas, contacta al administrador")

def pantalla_cambiar_password():
    st.title("🔐 Cambio de Contraseña Obligatorio")
    st.markdown("---")
    st.warning("⚠️ Debes cambiar tu contraseña antes de continuar")
    st.info(f"👤 Usuario: **{st.session_state.username}**")
    
    with st.form("cambiar_password_form"):
        nueva = st.text_input("Nueva Contraseña", type="password", help="Mínimo 8 caracteres")
        confirmar = st.text_input("Confirmar Contraseña", type="password")
        st.caption("💡 Usa una contraseña segura con letras, números y símbolos")
        submit = st.form_submit_button("✅ Cambiar Contraseña", use_container_width=True, type="primary")
        
        if submit:
            errores = []
            if not nueva:
                errores.append("La contraseña no puede estar vacía")
            elif len(nueva) < 8:
                errores.append("La contraseña debe tener mínimo 8 caracteres")
            if nueva != confirmar:
                errores.append("Las contraseñas no coinciden")
            if errores:
                for e in errores:
                    st.error(f"❌ {e}")
            else:
                nuevo_hash = hashlib.sha256(nueva.encode()).hexdigest()
                if actualizar_password(st.session_state.username, nuevo_hash, False):
                    st.session_state.debe_cambiar_password = False
                    st.success("✅ ¡Contraseña actualizada!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("❌ Error al actualizar. Intenta de nuevo.")

def pantalla_selector():
    inyectar_css_selector()
    nombre = st.session_state.nombre_completo or "Analista"
    nombre_corto = nombre.split()[0] if nombre else "Analista"
    
    st.markdown(f"""
    <div style="text-align:center; margin-bottom:48px; margin-top:20px;">
        <p style="font-family:'DM Sans',sans-serif; font-weight:300; font-size:13px;
                  letter-spacing:4px; text-transform:uppercase; color:#555; margin-bottom:6px;">BIENVENIDO</p>
        <p style="font-family:'Bebas Neue',sans-serif; font-size:clamp(28px,5vw,40px);
                  letter-spacing:3px; color:#F0F0F0; margin:0;">{nombre_corto}</p>
        <p style="font-size:12px; color:#444; letter-spacing:1px; margin-top:6px;">SELECCIONA EL TIPO DE FORMULARIO</p>
    </div>""", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2, gap="medium")
    with col1:
        st.markdown('<div style="text-align:center;margin-bottom:12px;"><span style="font-size:32px;">👤</span></div>', unsafe_allow_html=True)
        st.markdown('<div class="btn-individual">', unsafe_allow_html=True)
        if st.button("FORMULARIO\nINDIVIDUAL", key="btn_individual", use_container_width=True):
            st.session_state.vista = "individual"
            st.session_state.hechos_individual = []
            st.session_state.antecedentes_individual = []
            st.session_state.perfil_antiguo_individual = []
            st.session_state.desplazamientos_individual = []
            st.session_state.verificaciones_individual = []
            st.session_state.form_submitted_individual = False
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('<p style="text-align:center;font-size:11px;color:#444;margin-top:10px;">Un caso por registro</p>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div style="text-align:center;margin-bottom:12px;"><span style="font-size:32px;">👥</span></div>', unsafe_allow_html=True)
        st.markdown('<div class="btn-colectivo">', unsafe_allow_html=True)
        if st.button("FORMULARIO\nCOLECTIVO", key="btn_colectivo", use_container_width=True):
            st.session_state.vista = "colectivo"
            st.session_state.hechos_colectivo = []
            st.session_state.antecedentes_colectivo = []
            st.session_state.perfil_antiguo_colectivo = []
            st.session_state.desplazamientos_colectivo = []
            st.session_state.verificaciones_colectivo = []
            st.session_state.form_submitted_colectivo = False
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('<p style="text-align:center;font-size:11px;color:#444;margin-top:10px;">Múltiples personas afectadas</p>', unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    _, col_logout, _ = st.columns([2, 1, 2])
    with col_logout:
        if st.button("🚪 Cerrar sesión", use_container_width=True, type="secondary"):
            logout()

# =============================================================================
# FORMULARIO INDIVIDUAL (OPTIMIZADO)
# =============================================================================
def formulario_individual():
    resultado = conectar_sheets_individual()
    hoja_casos, hoja_hechos, hoja_antecedentes, hoja_perfil, hoja_desplazamientos, hoja_verificaciones, sheet_url = resultado
    if hoja_casos is None:
        st.error("⚠️ No se pudo conectar a Google Sheets")
        return
    
    # Verificar borrador solo una vez
    if not st.session_state.get("_borrador_ind_revisado"):
        campos_b, listas_b, ts_b = cargar_borrador("individual")
        if campos_b:
            st.session_state["_borrador_ind_pendiente"] = (campos_b, listas_b, ts_b)
        st.session_state["_borrador_ind_revisado"] = True
    
    if st.session_state.get("_borrador_ind_pendiente"):
        campos_b, listas_b, ts_b = st.session_state["_borrador_ind_pendiente"]
        st.warning(f"📂 Tienes un borrador guardado del **{ts_b}**. ¿Deseas retomarlo?")
        col_si, col_no = st.columns(2)
        with col_si:
            if st.button("✅ Sí, retomar borrador", use_container_width=True, type="primary"):
                for k, v in campos_b.items():
                    st.session_state[k] = v
                st.session_state["hechos_individual"] = listas_b.get("hechos", [])
                st.session_state["antecedentes_individual"] = listas_b.get("antecedentes", [])
                st.session_state["perfil_antiguo_individual"] = listas_b.get("perfil_antiguo", [])
                st.session_state["desplazamientos_individual"] = listas_b.get("desplazamientos", [])
                st.session_state["verificaciones_individual"] = listas_b.get("verificaciones", [])
                del st.session_state["_borrador_ind_pendiente"]
                st.rerun()
        with col_no:
            if st.button("🗑️ No, descartar borrador", use_container_width=True):
                eliminar_borrador("individual")
                del st.session_state["_borrador_ind_pendiente"]
                st.rerun()
        st.markdown("---")
    
    col_back, col_title = st.columns([1, 4])
    with col_back:
        if st.button("← Volver", type="secondary"):
            st.session_state.vista = None
            st.session_state.hechos_individual = []
            st.session_state.antecedentes_individual = []
            st.session_state.perfil_antiguo_individual = []
            st.session_state.desplazamientos_individual = []
            st.session_state.verificaciones_individual = []
            st.session_state.pop("_borrador_ind_revisado", None)
            st.session_state.pop("_borrador_ind_pendiente", None)
            st.session_state.form_submitted_individual = False
            st.rerun()
    with col_title:
        st.markdown("""
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:4px;">
            <span style="font-size:22px;">👤</span>
            <span style="font-size:22px;font-weight:600;color:#F0F0F0;">Formulario Individual</span>
            <span style="background:rgba(79,139,255,0.1);border:1px solid rgba(79,139,255,0.3);
                         color:#4F8BFF;font-size:10px;letter-spacing:2px;
                         padding:3px 9px;border-radius:2px;">INDIVIDUAL</span>
        </div>""", unsafe_allow_html=True)
        st.markdown(
            f'<p style="font-size:12px;color:#555;margin:0;">Registrando como: '
            f'<strong style="color:#888;">{st.session_state.nombre_completo}</strong></p>',
            unsafe_allow_html=True
        )
    
    st.markdown("---")
    
    # Formulario principal con st.form
    with st.form(key="form_individual", clear_on_submit=False):
        st.subheader("📝 Información del Caso")
        
        ot_te = st.text_input("OT-TE *", placeholder="Ejemplo: OT-2024-001", key="ind_ot")
        
        col1, col2 = st.columns(2)
        with col1:
            edad = st.number_input("Edad *", min_value=0, max_value=120, value=None, key="ind_edad")
            sexo = st.selectbox("Sexo *", ["Seleccione...", "Hombre", "Mujer", "Otro", "No Reporta"], key="ind_sexo")
            departamento = st.text_input("Departamento *", placeholder="Ejemplo: Antioquia", key="ind_depto")
            año = st.number_input("Año OT *", min_value=2000, max_value=2026, value=None, key="ind_anio")
            mes = st.number_input("Mes OT *", min_value=1, max_value=12, value=None, key="ind_mes")
        with col2:
            municipio = st.text_input("Municipio *", placeholder="Ejemplo: Medellín", key="ind_muni")
            solicitante = st.selectbox("Entidad Solicitante *", ["Seleccione...", "ARN", "SESP", "OTRO"], key="ind_sol")
            tipo_estudio = st.selectbox("Tipo de Estudio *", ["Seleccione...", "ORDEN DE TRABAJO OT", "TRÁMITE DE EMERGENCIA TE"], key="ind_tipo_estudio")
            nivel_riesgo = st.selectbox("Nivel de Riesgo *", ["Seleccione...", "EXTRAORDINARIO", "EXTREMO", "ORDINARIO"], key="ind_riesgo")
        
        observaciones = st.text_area("Observaciones (Opcional)", height=80, key="ind_obs")
        
        st.markdown("---")
        st.markdown("### 📋 Secciones adicionales (completar después)")
        
        # Botones del formulario
        col_draft, col_register = st.columns([1, 2])
        with col_draft:
            guardar_borrador_btn = st.form_submit_button("💾 Guardar borrador", use_container_width=True)
        with col_register:
            registrar_btn = st.form_submit_button("✅ REGISTRAR CASO INDIVIDUAL", use_container_width=True, type="primary")
    
    # Secciones fuera del formulario principal para mejor UX
    seccion_antecedentes("individual")
    seccion_perfil_antiguo("individual")
    seccion_desplazamientos("individual")
    seccion_hechos("individual")
    seccion_verificaciones("individual")
    
    # Procesar acciones del formulario
    if guardar_borrador_btn and not st.session_state.form_submitted_individual:
        campos = {
            "ind_ot": ot_te, "ind_edad": edad, "ind_sexo": sexo,
            "ind_depto": departamento, "ind_muni": municipio,
            "ind_sol": solicitante, "ind_riesgo": nivel_riesgo,
            "ind_tipo_estudio": tipo_estudio, "ind_anio": año,
            "ind_mes": mes, "ind_obs": observaciones
        }
        if guardar_borrador("individual", campos):
            st.success("💾 Borrador guardado.")
    
    if registrar_btn and not st.session_state.form_submitted_individual:
        st.session_state.form_submitted_individual = True
        
        # Validaciones
        errores = []
        if not ot_te or not ot_te.strip():
            errores.append("El campo OT-TE es obligatorio")
        if edad is None or edad == 0:
            errores.append("La edad es obligatoria")
        if sexo == "Seleccione...":
            errores.append("Debe seleccionar un sexo")
        if not departamento or not departamento.strip():
            errores.append("El departamento es obligatorio")
        if not municipio or not municipio.strip():
            errores.append("El municipio es obligatorio")
        if solicitante == "Seleccione...":
            errores.append("Debe seleccionar una entidad solicitante")
        if nivel_riesgo == "Seleccione...":
            errores.append("Debe seleccionar un nivel de riesgo")
        if tipo_estudio == "Seleccione...":
            errores.append("Debe seleccionar un tipo de estudio")
        if año is None:
            errores.append("El año es obligatorio")
        if mes is None:
            errores.append("El mes es obligatorio")
        
        if errores:
            st.error("❌ Por favor corrija los siguientes errores:")
            for e in errores:
                st.write(f"   • {e}")
            st.session_state.form_submitted_individual = False
        else:
            try:
                # Verificar duplicados (con cache)
                ot_existentes = obtener_casos_existentes_cache(hoja_casos, "individual")
                if ot_te.strip() in ot_existentes:
                    st.error(f"❌ El caso '{ot_te}' ya existe en la hoja Individual")
                    st.session_state.form_submitted_individual = False
                else:
                    # Guardar datos
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    id_caso = obtener_siguiente_id(hoja_casos)
                    
                    # Caso principal
                    hoja_casos.append_row([
                        timestamp, ot_te.strip(), edad, sexo,
                        departamento.strip(), municipio.strip(), solicitante, nivel_riesgo,
                        observaciones.strip() if observaciones else "",
                        st.session_state.nombre_completo, st.session_state.username, id_caso,
                        tipo_estudio, año, mes
                    ])
                    
                    # Hechos
                    for hecho in st.session_state.hechos_individual:
                        hoja_hechos.append_row([
                            obtener_siguiente_id(hoja_hechos), id_caso, ot_te.strip(),
                            hecho["tipo"], hecho["fecha"], hecho["lugar"],
                            hecho["autor"], hecho["descripcion"],
                            st.session_state.nombre_completo, st.session_state.username
                        ])
                    
                    # Antecedentes
                    for ant in st.session_state.antecedentes_individual:
                        hoja_antecedentes.append_row([
                            obtener_siguiente_id(hoja_antecedentes), id_caso, ot_te.strip(),
                            ant["registra_ot"], ant["registra_resoluciones"],
                            st.session_state.nombre_completo, st.session_state.username
                        ])
                    
                    # Perfil antiguo
                    for perf in st.session_state.perfil_antiguo_individual:
                        hoja_perfil.append_row([
                            obtener_siguiente_id(hoja_perfil), id_caso, ot_te.strip(),
                            perf["modo_participacion"], perf["lugar_acreditacion"],
                            st.session_state.nombre_completo, st.session_state.username
                        ])
                    
                    # Desplazamientos
                    for desp in st.session_state.desplazamientos_individual:
                        hoja_desplazamientos.append_row([
                            obtener_siguiente_id(hoja_desplazamientos), id_caso, ot_te.strip(),
                            desp["motivo"], desp["medio"],
                            desp["depto_origen"], desp["depto_destino"],
                            st.session_state.nombre_completo, st.session_state.username
                        ])
                    
                    # Verificaciones
                    for ver in st.session_state.verificaciones_individual:
                        hoja_verificaciones.append_row([
                            obtener_siguiente_id(hoja_verificaciones), id_caso, ot_te.strip(),
                            ver["fuente"], ver["nombre_fuente"],
                            st.session_state.nombre_completo, st.session_state.username
                        ])
                    
                    # Limpiar
                    eliminar_borrador("individual")
                    st.session_state.hechos_individual = []
                    st.session_state.antecedentes_individual = []
                    st.session_state.perfil_antiguo_individual = []
                    st.session_state.desplazamientos_individual = []
                    st.session_state.verificaciones_individual = []
                    st.session_state.pop("_borrador_ind_revisado", None)
                    st.session_state.form_submitted_individual = False
                    
                    # Limpiar cache
                    st.cache_data.clear()
                    
                    st.success(f"✅ Caso **{ot_te}** registrado como Individual!")
                    st.balloons()
                    
                    # Resumen
                    st.info(f"""
                    **Resumen:**
                    - **ID Caso:** {id_caso}
                    - **OT-TE:** {ot_te}
                    - **Ubicación:** {municipio}, {departamento}
                    - **Nivel de Riesgo:** {nivel_riesgo}
                    - **Tipo de Estudio:** {tipo_estudio}
                    - **Hechos registrados:** {len(st.session_state.hechos_individual)}
                    - **Registrado por:** {st.session_state.nombre_completo}
                    - **Fecha:** {timestamp}
                    """)
                    
            except Exception as e:
                st.error(f"❌ Error al guardar: {e}")
                st.session_state.form_submitted_individual = False
    
    st.markdown("---")
    st.caption("🔒 Los datos se guardan en Google Sheets")

# =============================================================================
# FORMULARIO COLECTIVO (OPTIMIZADO)
# =============================================================================
SECTORES_COLECTIVO = [
    "Seleccione...", "Comunidad campesina", "Comunidad indígena",
    "Comunidad afrodescendiente", "Organización social", "Organización sindical",
    "Organización de mujeres", "Organización de jóvenes", "Organización LGBTIQ+",
    "Defensores de DDHH", "Líderes sociales", "Otro",
]

def formulario_colectivo():
    resultado = conectar_sheets_colectivo()
    hoja_casos, hoja_hechos, hoja_antecedentes, hoja_perfil, hoja_desplazamientos, hoja_verificaciones, sheet_url = resultado
    if hoja_casos is None:
        st.error("⚠️ No se pudo conectar a Google Sheets")
        return
    
    # Verificar borrador solo una vez
    if not st.session_state.get("_borrador_col_revisado"):
        campos_b, listas_b, ts_b = cargar_borrador("colectivo")
        if campos_b:
            st.session_state["_borrador_col_pendiente"] = (campos_b, listas_b, ts_b)
        st.session_state["_borrador_col_revisado"] = True
    
    if st.session_state.get("_borrador_col_pendiente"):
        campos_b, listas_b, ts_b = st.session_state["_borrador_col_pendiente"]
        st.warning(f"📂 Tienes un borrador guardado del **{ts_b}**. ¿Deseas retomarlo?")
        col_si, col_no = st.columns(2)
        with col_si:
            if st.button("✅ Sí, retomar borrador", use_container_width=True, type="primary"):
                for k, v in campos_b.items():
                    st.session_state[k] = v
                st.session_state["hechos_colectivo"] = listas_b.get("hechos", [])
                st.session_state["antecedentes_colectivo"] = listas_b.get("antecedentes", [])
                st.session_state["perfil_antiguo_colectivo"] = listas_b.get("perfil_antiguo", [])
                st.session_state["desplazamientos_colectivo"] = listas_b.get("desplazamientos", [])
                st.session_state["verificaciones_colectivo"] = listas_b.get("verificaciones", [])
                del st.session_state["_borrador_col_pendiente"]
                st.rerun()
        with col_no:
            if st.button("🗑️ No, descartar borrador", use_container_width=True):
                eliminar_borrador("colectivo")
                del st.session_state["_borrador_col_pendiente"]
                st.rerun()
        st.markdown("---")
    
    col_back, col_title = st.columns([1, 4])
    with col_back:
        if st.button("← Volver", type="secondary"):
            st.session_state.vista = None
            st.session_state.hechos_colectivo = []
            st.session_state.antecedentes_colectivo = []
            st.session_state.perfil_antiguo_colectivo = []
            st.session_state.desplazamientos_colectivo = []
            st.session_state.verificaciones_colectivo = []
            st.session_state.pop("_borrador_col_revisado", None)
            st.session_state.pop("_borrador_col_pendiente", None)
            st.session_state.form_submitted_colectivo = False
            st.rerun()
    with col_title:
        st.markdown("""
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:4px;">
            <span style="font-size:22px;">👥</span>
            <span style="font-size:22px;font-weight:600;color:#F0F0F0;">Formulario Colectivo</span>
            <span style="background:rgba(74,222,128,0.1);border:1px solid rgba(74,222,128,0.3);
                         color:#4ADE80;font-size:10px;letter-spacing:2px;
                         padding:3px 9px;border-radius:2px;">COLECTIVO</span>
        </div>""", unsafe_allow_html=True)
        st.markdown(
            f'<p style="font-size:12px;color:#555;margin:0;">Registrando como: '
            f'<strong style="color:#888;">{st.session_state.nombre_completo}</strong></p>',
            unsafe_allow_html=True
        )
    
    st.markdown("---")
    
    # Formulario principal con st.form
    with st.form(key="form_colectivo", clear_on_submit=False):
        st.subheader("📝 Información del Colectivo")
        
        ot_te = st.text_input("OT-TE *", placeholder="Ejemplo: OT-2024-001", key="col_ot")
        
        col1, col2 = st.columns(2)
        with col1:
            nombre_colectivo = st.text_input("Nombre del Colectivo *", placeholder="Nombre del grupo u organización", key="col_nombre")
            fecha_creacion = st.date_input("Fecha de Creación del Colectivo *", key="col_fecha")
            sector = st.selectbox("Sector *", SECTORES_COLECTIVO, key="col_sector")
        with col2:
            departamento = st.text_input("Departamento *", placeholder="Ejemplo: Córdoba", key="col_depto")
            municipio = st.text_input("Municipio *", placeholder="Ejemplo: Montería", key="col_muni")
        
        st.markdown("---")
        st.markdown("### 📋 Secciones adicionales (completar después)")
        
        # Botones del formulario
        col_draft, col_register = st.columns([1, 2])
        with col_draft:
            guardar_borrador_btn = st.form_submit_button("💾 Guardar borrador", use_container_width=True)
        with col_register:
            registrar_btn = st.form_submit_button("✅ REGISTRAR CASO COLECTIVO", use_container_width=True, type="primary")
    
    # Secciones fuera del formulario principal
    seccion_antecedentes("colectivo")
    seccion_perfil_antiguo("colectivo")
    seccion_desplazamientos("colectivo")
    seccion_hechos("colectivo")
    seccion_verificaciones("colectivo")
    
    # Procesar acciones del formulario
    if guardar_borrador_btn and not st.session_state.form_submitted_colectivo:
        campos = {
            "col_ot": ot_te, "col_nombre": nombre_colectivo,
            "col_sector": sector, "col_depto": departamento,
            "col_muni": municipio
        }
        if guardar_borrador("colectivo", campos):
            st.success("💾 Borrador guardado.")
    
    if registrar_btn and not st.session_state.form_submitted_colectivo:
        st.session_state.form_submitted_colectivo = True
        
        # Validaciones
        errores = []
        if not ot_te or not ot_te.strip():
            errores.append("El campo OT-TE es obligatorio")
        if not nombre_colectivo or not nombre_colectivo.strip():
            errores.append("El nombre del colectivo es obligatorio")
        if sector == "Seleccione...":
            errores.append("Debe seleccionar un sector")
        if not departamento or not departamento.strip():
            errores.append("El departamento es obligatorio")
        if not municipio or not municipio.strip():
            errores.append("El municipio es obligatorio")
        
        if errores:
            st.error("❌ Por favor corrija los siguientes errores:")
            for e in errores:
                st.write(f"   • {e}")
            st.session_state.form_submitted_colectivo = False
        else:
            try:
                # Verificar duplicados (con cache)
                ot_existentes = obtener_casos_existentes_cache(hoja_casos, "colectivo")
                if ot_te.strip() in ot_existentes:
                    st.error(f"❌ El caso '{ot_te}' ya existe en la hoja Colectivo")
                    st.session_state.form_submitted_colectivo = False
                else:
                    # Guardar datos
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    id_caso = obtener_siguiente_id(hoja_casos)
                    
                    # Caso principal
                    hoja_casos.append_row([
                        timestamp, ot_te.strip(), nombre_colectivo.strip(),
                        str(fecha_creacion), sector, departamento.strip(), municipio.strip(),
                        st.session_state.nombre_completo, st.session_state.username, id_caso
                    ])
                    
                    # Hechos
                    for hecho in st.session_state.hechos_colectivo:
                        hoja_hechos.append_row([
                            obtener_siguiente_id(hoja_hechos), id_caso, ot_te.strip(),
                            hecho["tipo"], hecho["fecha"], hecho["lugar"],
                            hecho["autor"], hecho["descripcion"],
                            st.session_state.nombre_completo, st.session_state.username
                        ])
                    
                    # Antecedentes
                    for ant in st.session_state.antecedentes_colectivo:
                        hoja_antecedentes.append_row([
                            obtener_siguiente_id(hoja_antecedentes), id_caso, ot_te.strip(),
                            ant["registra_ot"], ant["registra_resoluciones"],
                            st.session_state.nombre_completo, st.session_state.username
                        ])
                    
                    # Perfil antiguo
                    for perf in st.session_state.perfil_antiguo_colectivo:
                        hoja_perfil.append_row([
                            obtener_siguiente_id(hoja_perfil), id_caso, ot_te.strip(),
                            perf["modo_participacion"], perf["lugar_acreditacion"],
                            st.session_state.nombre_completo, st.session_state.username
                        ])
                    
                    # Desplazamientos
                    for desp in st.session_state.desplazamientos_colectivo:
                        hoja_desplazamientos.append_row([
                            obtener_siguiente_id(hoja_desplazamientos), id_caso, ot_te.strip(),
                            desp["motivo"], desp["medio"],
                            desp["depto_origen"], desp["depto_destino"],
                            st.session_state.nombre_completo, st.session_state.username
                        ])
                    
                    # Verificaciones
                    for ver in st.session_state.verificaciones_colectivo:
                        hoja_verificaciones.append_row([
                            obtener_siguiente_id(hoja_verificaciones), id_caso, ot_te.strip(),
                            ver["fuente"], ver["nombre_fuente"],
                            st.session_state.nombre_completo, st.session_state.username
                        ])
                    
                    # Limpiar
                    eliminar_borrador("colectivo")
                    st.session_state.hechos_colectivo = []
                    st.session_state.antecedentes_colectivo = []
                    st.session_state.perfil_antiguo_colectivo = []
                    st.session_state.desplazamientos_colectivo = []
                    st.session_state.verificaciones_colectivo = []
                    st.session_state.pop("_borrador_col_revisado", None)
                    st.session_state.form_submitted_colectivo = False
                    
                    # Limpiar cache
                    st.cache_data.clear()
                    
                    st.success(f"✅ Caso **{ot_te}** registrado como Colectivo!")
                    st.balloons()
                    
                    # Resumen
                    st.info(f"""
                    **Resumen:**
                    - **ID Caso:** {id_caso}
                    - **OT-TE:** {ot_te}
                    - **Colectivo:** {nombre_colectivo}
                    - **Sector:** {sector}
                    - **Ubicación:** {municipio}, {departamento}
                    - **Fecha creación colectivo:** {fecha_creacion}
                    - **Hechos registrados:** {len(st.session_state.hechos_colectivo)}
                    - **Registrado por:** {st.session_state.nombre_completo}
                    - **Fecha registro:** {timestamp}
                    """)
                    
            except Exception as e:
                st.error(f"❌ Error al guardar: {e}")
                st.session_state.form_submitted_colectivo = False
    
    st.markdown("---")
    st.caption("🔒 Los datos se guardan en la hoja 'Colectivo' de Google Sheets")

# =============================================================================
# PANEL DE VISUALIZACIÓN (OPTIMIZADO)
# =============================================================================
@st.cache_data(ttl=60)
def obtener_datos_individual():
    """Obtiene todos los datos individuales con cache de 60 segundos"""
    resultado = conectar_sheets_individual()
    if resultado[0] is None:
        return None
    
    hojas = resultado[:6]
    datos = {}
    nombres = ["casos", "hechos", "antecedentes", "perfil", "desplazamientos", "verificaciones"]
    
    for i, nombre in enumerate(nombres):
        try:
            records = hojas[i].get_all_records()
            if records:
                datos[nombre] = pd.DataFrame(records)
            else:
                datos[nombre] = pd.DataFrame()
        except:
            datos[nombre] = pd.DataFrame()
    
    return datos, resultado[6]  # datos y URL

@st.cache_data(ttl=60)
def obtener_datos_colectivo():
    """Obtiene todos los datos colectivos con cache de 60 segundos"""
    resultado = conectar_sheets_colectivo()
    if resultado[0] is None:
        return None
    
    hojas = resultado[:6]
    datos = {}
    nombres = ["casos", "hechos", "antecedentes", "perfil", "desplazamientos", "verificaciones"]
    
    for i, nombre in enumerate(nombres):
        try:
            records = hojas[i].get_all_records()
            if records:
                datos[nombre] = pd.DataFrame(records)
            else:
                datos[nombre] = pd.DataFrame()
        except:
            datos[nombre] = pd.DataFrame()
    
    return datos, resultado[6]

def mostrar_tabla_con_filtros(df, titulo, columnas_filtro=None):
    """Muestra una tabla con filtros"""
    if df.empty:
        st.info(f"📭 No hay datos en {titulo}")
        return
    
    st.subheader(f"📋 {titulo} ({len(df)} registros)")
    
    # Filtros
    if columnas_filtro:
        cols = st.columns(len(columnas_filtro))
        filtros = {}
        for i, col in enumerate(columnas_filtro):
            if col in df.columns:
                opciones = ["Todos"] + sorted(df[col].dropna().unique().tolist())
                filtros[col] = cols[i].selectbox(f"Filtrar por {col}", opciones, key=f"filtro_{col}_{titulo}")
        
        # Aplicar filtros
        df_filtrado = df.copy()
        for col, valor in filtros.items():
            if valor != "Todos" and col in df_filtrado.columns:
                df_filtrado = df_filtrado[df_filtrado[col] == valor]
    else:
        df_filtrado = df
    
    # Mostrar tabla
    st.dataframe(df_filtrado, use_container_width=True, hide_index=True)
    
    # Botón de descarga
    st.download_button(
        f"📥 Descargar {titulo} CSV",
        df_filtrado.to_csv(index=False, encoding="utf-8-sig"),
        f"{titulo.lower().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.csv",
        "text/csv"
    )

def panel_visualizacion():
    st.title("📊 Casos Registrados")
    st.markdown("---")
    
    # Botón para refrescar datos
    if st.button("🔄 Refrescar datos", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    
    st.markdown("---")
    
    tab_ind, tab_col = st.tabs(["👤 Individual", "👥 Colectivo"])
    
    with tab_ind:
        datos = obtener_datos_individual()
        if datos is None:
            st.error("No se pudo conectar a la hoja Individual")
        else:
            datos_df, sheet_url = datos
            if sheet_url:
                st.markdown(f"[📝 Abrir en Google Sheets]({sheet_url})")
            
            if not datos_df["casos"].empty:
                # Métricas
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Total Casos", len(datos_df["casos"]))
                if "Departamento" in datos_df["casos"].columns:
                    c2.metric("Departamentos", datos_df["casos"]["Departamento"].nunique())
                if "Municipio" in datos_df["casos"].columns:
                    c3.metric("Municipios", datos_df["casos"]["Municipio"].nunique())
                if "Nivel de Riesgo" in datos_df["casos"].columns:
                    riesgo_alto = datos_df["casos"]["Nivel de Riesgo"].isin(["EXTREMO", "EXTRAORDINARIO"]).sum()
                    c4.metric("Riesgo Alto", riesgo_alto)
                
                # Tabs para diferentes vistas
                sub1, sub2, sub3, sub4, sub5, sub6 = st.tabs([
                    "📋 Casos", "⚠️ Hechos", "📁 Antecedentes",
                    "🗂️ Perfil Antiguo", "🚗 Desplazamientos", "✅ Verificaciones"
                ])
                
                with sub1:
                    mostrar_tabla_con_filtros(
                        datos_df["casos"],
                        "Casos Individuales",
                        ["Departamento", "Nivel de Riesgo", "Analista"]
                    )
                
                with sub2:
                    if not datos_df["hechos"].empty:
                        c1, c2, c3 = st.columns(3)
                        c1.metric("Total Hechos", len(datos_df["hechos"]))
                        if "Tipo de Hecho" in datos_df["hechos"].columns:
                            c2.metric("Tipos distintos", datos_df["hechos"]["Tipo de Hecho"].nunique())
                        if "ID_Caso" in datos_df["hechos"].columns:
                            c3.metric("Casos con hechos", datos_df["hechos"]["ID_Caso"].nunique())
                        mostrar_tabla_con_filtros(
                            datos_df["hechos"],
                            "Hechos Individuales",
                            ["Tipo de Hecho"]
                        )
                    else:
                        st.info("📭 No hay hechos registrados")
                
                with sub3:
                    if not datos_df["antecedentes"].empty:
                        mostrar_tabla_con_filtros(datos_df["antecedentes"], "Antecedentes")
                    else:
                        st.info("📭 No hay antecedentes registrados")
                
                with sub4:
                    if not datos_df["perfil"].empty:
                        mostrar_tabla_con_filtros(datos_df["perfil"], "Perfil Antiguo")
                    else:
                        st.info("📭 No hay perfiles registrados")
                
                with sub5:
                    if not datos_df["desplazamientos"].empty:
                        mostrar_tabla_con_filtros(datos_df["desplazamientos"], "Desplazamientos")
                    else:
                        st.info("📭 No hay desplazamientos registrados")
                
                with sub6:
                    if not datos_df["verificaciones"].empty:
                        mostrar_tabla_con_filtros(datos_df["verificaciones"], "Verificaciones")
                    else:
                        st.info("📭 No hay verificaciones registradas")
            else:
                st.info("📭 No hay casos individuales registrados")
    
    with tab_col:
        datos = obtener_datos_colectivo()
        if datos is None:
            st.error("No se pudo conectar a la hoja Colectivo")
        else:
            datos_df, sheet_url = datos
            if sheet_url:
                st.markdown(f"[📝 Abrir en Google Sheets]({sheet_url})")
            
            if not datos_df["casos"].empty:
                # Métricas
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Total Colectivos", len(datos_df["casos"]))
                if "Departamento" in datos_df["casos"].columns:
                    c2.metric("Departamentos", datos_df["casos"]["Departamento"].nunique())
                if "Municipio" in datos_df["casos"].columns:
                    c3.metric("Municipios", datos_df["casos"]["Municipio"].nunique())
                if "Sector" in datos_df["casos"].columns:
                    c4.metric("Sectores", datos_df["casos"]["Sector"].nunique())
                
                # Tabs para diferentes vistas
                sub1, sub2, sub3, sub4, sub5, sub6 = st.tabs([
                    "📋 Casos", "⚠️ Hechos", "📁 Antecedentes",
                    "🗂️ Perfil Antiguo", "🚗 Desplazamientos", "✅ Verificaciones"
                ])
                
                with sub1:
                    mostrar_tabla_con_filtros(
                        datos_df["casos"],
                        "Casos Colectivos",
                        ["Departamento", "Sector", "Analista"]
                    )
                
                with sub2:
                    if not datos_df["hechos"].empty:
                        c1, c2, c3 = st.columns(3)
                        c1.metric("Total Hechos", len(datos_df["hechos"]))
                        if "Tipo de Hecho" in datos_df["hechos"].columns:
                            c2.metric("Tipos distintos", datos_df["hechos"]["Tipo de Hecho"].nunique())
                        if "ID_Caso" in datos_df["hechos"].columns:
                            c3.metric("Casos con hechos", datos_df["hechos"]["ID_Caso"].nunique())
                        mostrar_tabla_con_filtros(
                            datos_df["hechos"],
                            "Hechos Colectivos",
                            ["Tipo de Hecho"]
                        )
                    else:
                        st.info("📭 No hay hechos registrados")
                
                with sub3:
                    if not datos_df["antecedentes"].empty:
                        mostrar_tabla_con_filtros(datos_df["antecedentes"], "Antecedentes")
                    else:
                        st.info("📭 No hay antecedentes registrados")
                
                with sub4:
                    if not datos_df["perfil"].empty:
                        mostrar_tabla_con_filtros(datos_df["perfil"], "Perfil Antiguo")
                    else:
                        st.info("📭 No hay perfiles registrados")
                
                with sub5:
                    if not datos_df["desplazamientos"].empty:
                        mostrar_tabla_con_filtros(datos_df["desplazamientos"], "Desplazamientos")
                    else:
                        st.info("📭 No hay desplazamientos registrados")
                
                with sub6:
                    if not datos_df["verificaciones"].empty:
                        mostrar_tabla_con_filtros(datos_df["verificaciones"], "Verificaciones")
                    else:
                        st.info("📭 No hay verificaciones registradas")
            else:
                st.info("📭 No hay casos colectivos registrados")

# =============================================================================
# PANEL DE GESTIÓN DE USUARIOS
# =============================================================================
def panel_gestion_usuarios():
    st.title("👥 Gestión de Usuarios")
    st.markdown("---")
    
    tab1, tab2, tab3 = st.tabs(["➕ Crear Usuario", "📋 Ver Usuarios", "🔑 Ver Hashes"])
    
    with tab1:
        st.subheader("➕ Crear Nuevo Usuario")
        with st.form("crear_usuario_form"):
            col1, col2 = st.columns(2)
            with col1:
                nuevo_username = st.text_input("Usuario *", placeholder="nombre.apellido")
                nuevo_nombre = st.text_input("Nombre Completo *", placeholder="Juan Pérez")
            with col2:
                password_default = st.text_input("Contraseña por Defecto *", value="ISMR2024")
                es_admin_nuevo = st.checkbox("¿Es Administrador?", value=False)
            
            st.info("💡 El usuario deberá cambiar la contraseña en su primer acceso")
            
            if st.form_submit_button("✅ Crear Usuario", use_container_width=True, type="primary"):
                if nuevo_username and nuevo_nombre and password_default:
                    phash = hashlib.sha256(password_default.encode()).hexdigest()
                    if crear_usuario(nuevo_username, phash, nuevo_nombre, es_admin_nuevo, True):
                        st.success(f"✅ Usuario '{nuevo_username}' creado!")
                        st.info(f"Usuario: **{nuevo_username}** | Contraseña temporal: **{password_default}**")
                        st.cache_data.clear()
                    else:
                        st.error("❌ El usuario ya existe o hubo un problema al crearlo")
                else:
                    st.warning("⚠️ Completa todos los campos")
    
    with tab2:
        st.subheader("📋 Lista de Usuarios")
        usuarios = listar_usuarios_cache()
        if usuarios:
            df = pd.DataFrame(usuarios)
            c1, c2, c3 = st.columns(3)
            c1.metric("Total", len(df))
            admins = df[df["es_admin"].astype(str).str.upper() == "TRUE"].shape[0] if "es_admin" in df.columns else 0
            c2.metric("Admins", admins)
            c3.metric("Analistas", len(df) - admins)
            st.dataframe(df[["username", "nombre_completo", "es_admin", "debe_cambiar_password"]],
                        use_container_width=True)
        else:
            st.info("📭 No hay usuarios")
    
    with tab3:
        st.subheader("🔑 Hashes de Contraseñas")
        st.warning("⚠️ Información sensible — solo visible para administradores")
        if st.checkbox("Mostrar hashes"):
            for u in listar_usuarios_cache():
                with st.expander(f"👤 {u.get('nombre_completo','?')} (@{u.get('username','?')})"):
                    st.code(u.get("password_hash", "N/A"), language=None)
                    st.caption(f"Debe cambiar: {u.get('debe_cambiar_password','N/A')}")

# =============================================================================
# MAIN
# =============================================================================
def main():
    if not st.session_state.autenticado:
        login_page()
        return
    
    if st.session_state.debe_cambiar_password:
        pantalla_cambiar_password()
        return
    
    # Menú para administradores
    if st.session_state.es_admin:
        st.sidebar.title("📊 Sistema ISMR")
        st.sidebar.success(f"👤 {st.session_state.nombre_completo}")
        st.sidebar.markdown("---")
        
        opcion = st.sidebar.radio("Menú", [
            "🏠 Inicio", "👤 Individual", "👥 Colectivo",
            "📊 Ver Datos", "👥 Gestionar Usuarios"
        ])
        
        if st.sidebar.button("🚪 Cerrar Sesión", use_container_width=True):
            logout()
        
        if opcion == "🏠 Inicio":
            pantalla_selector()
        elif opcion == "👤 Individual":
            formulario_individual()
        elif opcion == "👥 Colectivo":
            formulario_colectivo()
        elif opcion == "📊 Ver Datos":
            panel_visualizacion()
        else:
            panel_gestion_usuarios()
        return
    
    # Usuario normal
    vista = st.session_state.vista
    if vista is None:
        pantalla_selector()
    elif vista == "individual":
        formulario_individual()
    elif vista == "colectivo":
        formulario_colectivo()

if __name__ == "__main__":
    main()
