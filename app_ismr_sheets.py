import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import pandas as pd
import hashlib
import time

st.set_page_config(page_title="Sistema ISMR", page_icon="📋", layout="centered")

defaults = {
    "autenticado": False, "username": None, "nombre_completo": None,
    "debe_cambiar_password": False, "es_admin": False, "vista": None,
    "hechos_individual": [], "hechos_colectivo": []
}
for key, val in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = val


# ══════════════════════════════════════════════════════════════════════════════
# CSS
# ══════════════════════════════════════════════════════════════════════════════

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
    </style>
    """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# GOOGLE SHEETS — USUARIOS
# ══════════════════════════════════════════════════════════════════════════════

def _credenciales():
    credentials_dict = st.secrets["gcp_service_account"]
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    return Credentials.from_service_account_info(credentials_dict, scopes=scopes), credentials_dict

def conectar_sheet_usuarios():
    try:
        creds, creds_dict = _credenciales()
        client = gspread.authorize(creds)
        sheet_name = st.secrets.get("sheet_usuarios", "ISMR_Usuarios")
        try:
            spreadsheet = client.open(sheet_name)
        except Exception:
            spreadsheet = client.create(sheet_name)
            spreadsheet.share(creds_dict["client_email"], perm_type='user', role='writer')
        worksheet = spreadsheet.sheet1
        if not worksheet.row_values(1):
            worksheet.append_row(["username", "password_hash", "nombre_completo",
                                   "es_admin", "debe_cambiar_password"])
        return worksheet
    except Exception as e:
        st.error(f"Error al conectar sheet de usuarios: {e}")
        return None

def obtener_usuario(username):
    ws = conectar_sheet_usuarios()
    if not ws:
        return None
    try:
        for u in ws.get_all_records():
            if u.get("username") == username:
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

def listar_usuarios():
    ws = conectar_sheet_usuarios()
    if not ws:
        return []
    try:
        return ws.get_all_records()
    except Exception:
        return []


# ══════════════════════════════════════════════════════════════════════════════
# GOOGLE SHEETS — INDIVIDUAL
# ══════════════════════════════════════════════════════════════════════════════

def conectar_sheets_individual():
    """
    Conecta y retorna (hoja_casos_individual, hoja_hechos_individual, url).

    Hojas en el spreadsheet ISMR_Casos:
      • 'Individual'        — datos del caso individual
      • 'Hechos_Individual' — hechos de riesgo asociados a casos individuales
    """
    try:
        creds, _ = _credenciales()
        client = gspread.authorize(creds)
        spreadsheet = client.open(st.secrets.get("sheet_name", "ISMR_Casos"))

        # Hoja de casos individuales
        try:
            hoja_casos = spreadsheet.worksheet("Individual")
        except Exception:
            hoja_casos = spreadsheet.add_worksheet(title="Individual", rows="1000", cols="20")

        _sincronizar_encabezados(hoja_casos, [
            "Timestamp", "OT-TE", "Edad", "Sexo",
            "Departamento", "Municipio", "Solicitante",
            "Nivel de Riesgo", "Observaciones",
            "Analista", "Usuario Analista", "ID_Caso",
            "Tipo de Estudio", "Año OT", "Mes OT"   # ← tus nuevos campos ya están aquí
        ])
        
        # Hoja de hechos individuales
        try:
            hoja_hechos = spreadsheet.worksheet("Hechos_Individual")
        except Exception:
            hoja_hechos = spreadsheet.add_worksheet(title="Hechos_Individual", rows="1000", cols="20")

        _sincronizar_encabezados(hoja_hechos, [
                            "ID_Hecho", "ID_Caso", "OT-TE", "Tipo de Hecho",
                        "Fecha del Hecho", "Lugar", "Autor", "Descripcion",
                        "Analista", "Usuario Analista"
                        ])

        return hoja_casos, hoja_hechos, spreadsheet.url

    except Exception as e:
        st.error(f"Error al conectar sheets individuales: {e}")
        return None, None, None


# ══════════════════════════════════════════════════════════════════════════════
# GOOGLE SHEETS — COLECTIVO
# ══════════════════════════════════════════════════════════════════════════════

def conectar_sheets_colectivo():
    """
    Conecta y retorna (hoja_casos_colectivo, hoja_hechos_colectivo, url).

    Hojas en el spreadsheet ISMR_Casos:
      • 'Colectivo'        — datos del caso colectivo
      • 'Hechos_Colectivo' — hechos de riesgo asociados a casos colectivos
    """
    try:
        creds, _ = _credenciales()
        client = gspread.authorize(creds)
        spreadsheet = client.open(st.secrets.get("sheet_name", "ISMR_Casos"))

        # Hoja de casos colectivos
        try:
            hoja_casos = spreadsheet.worksheet("Colectivo")
        except Exception:
            hoja_casos = spreadsheet.add_worksheet(title="Colectivo", rows="1000", cols="20")

        _sincronizar_encabezados(hoja_casos, [
            "Timestamp", "OT-TE", "Nombre Colectivo", "Fecha Creacion Colectivo",
                "Sector", "Departamento", "Municipio",
                "Analista", "Usuario Analista", "ID_Caso"
        ])        

        # Hoja de hechos colectivos
        try:
            hoja_hechos = spreadsheet.worksheet("Hechos_Colectivo")
        except Exception:
            hoja_hechos = spreadsheet.add_worksheet(title="Hechos_Colectivo", rows="1000", cols="20")

        _sincronizar_encabezados(hoja_hechos, [
                    "ID_Hecho", "ID_Caso", "OT-TE", "Tipo de Hecho",
                "Fecha del Hecho", "Lugar", "Autor", "Descripcion",
                "Analista", "Usuario Analista"
                ])

        return hoja_casos, hoja_hechos, spreadsheet.url

    except Exception as e:
        st.error(f"Error al conectar sheets colectivos: {e}")
        return None, None, None


# ══════════════════════════════════════════════════════════════════════════════
# UTILIDADES
# ══════════════════════════════════════════════════════════════════════════════

def obtener_siguiente_id(hoja):
    return max(len(hoja.get_all_values()), 1)

def _sincronizar_encabezados(hoja, encabezados_esperados):
    cache_key = f"_headers_synced_{hoja.title}"
    if st.session_state.get(cache_key):
        return
    valores = hoja.get_all_values()
    if not valores:
        hoja.append_row(encabezados_esperados)
    else:
        encabezados_actuales = valores[0]
        faltantes = [col for col in encabezados_esperados if col not in encabezados_actuales]
        if faltantes:
            col_inicio = len(encabezados_actuales) + 1
            for i, nombre_col in enumerate(faltantes):
                hoja.update_cell(1, col_inicio + i, nombre_col)
    st.session_state[cache_key] = True


# ══════════════════════════════════════════════════════════════════════════════
# AUTH
# ══════════════════════════════════════════════════════════════════════════════

def verificar_credenciales(username, password):
    usuario = obtener_usuario(username)
    if not usuario:
        return False, None, False, False
    try:
        phash = hashlib.sha256(password.encode()).hexdigest()
        if phash == usuario.get("password_hash", ""):
            debe_cambiar = str(usuario.get("debe_cambiar_password", "FALSE")).upper() == "TRUE"
            es_admin     = str(usuario.get("es_admin", "FALSE")).upper() == "TRUE"
            return True, usuario.get("nombre_completo", username), debe_cambiar, es_admin
        return False, None, False, False
    except Exception as e:
        st.error(f"Error en verificación: {e}")
        return False, None, False, False

def logout():
    for key in defaults:
        st.session_state[key] = defaults[key]
    st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# PANTALLA: LOGIN
# ══════════════════════════════════════════════════════════════════════════════

def login_page():
    st.title("🔐 Acceso al Sistema ISMR")
    st.markdown("---")
    st.info("👋 Identifícate para acceder al sistema")
    with st.form("login_form"):
        username = st.text_input("Usuario", placeholder="tu.usuario")
        password = st.text_input("Contraseña", type="password")
        submit   = st.form_submit_button("🔓 Iniciar Sesión", use_container_width=True, type="primary")
        if submit:
            if username and password:
                ok, nombre, cambiar, admin = verificar_credenciales(username, password)
                if ok:
                    st.session_state.autenticado           = True
                    st.session_state.username              = username
                    st.session_state.nombre_completo       = nombre
                    st.session_state.debe_cambiar_password = cambiar
                    st.session_state.es_admin              = admin
                    st.session_state.hechos_individual     = []
                    st.session_state.hechos_colectivo      = []
                    st.rerun()
                else:
                    st.error("❌ Usuario o contraseña incorrectos")
            else:
                st.warning("⚠️ Por favor completa todos los campos")
    st.markdown("---")
    st.caption("🔒 Si tienes problemas, contacta al administrador")


# ══════════════════════════════════════════════════════════════════════════════
# PANTALLA: CAMBIO DE CONTRASEÑA
# ══════════════════════════════════════════════════════════════════════════════

def pantalla_cambiar_password():
    st.title("🔐 Cambio de Contraseña Obligatorio")
    st.markdown("---")
    st.warning("⚠️ Debes cambiar tu contraseña antes de continuar")
    st.info(f"👤 Usuario: **{st.session_state.username}**")
    with st.form("cambiar_password_form"):
        nueva     = st.text_input("Nueva Contraseña", type="password", help="Mínimo 8 caracteres")
        confirmar = st.text_input("Confirmar Contraseña", type="password")
        st.caption("💡 Usa una contraseña segura con letras, números y símbolos")
        submit = st.form_submit_button("✅ Cambiar Contraseña", use_container_width=True, type="primary")
        if submit:
            errores = []
            if not nueva:          errores.append("La contraseña no puede estar vacía")
            elif len(nueva) < 8:   errores.append("La contraseña debe tener mínimo 8 caracteres")
            if nueva != confirmar: errores.append("Las contraseñas no coinciden")
            if errores:
                for e in errores: st.error(f"❌ {e}")
            else:
                nuevo_hash = hashlib.sha256(nueva.encode()).hexdigest()
                if actualizar_password(st.session_state.username, nuevo_hash, False):
                    st.session_state.debe_cambiar_password = False
                    st.success("✅ ¡Contraseña actualizada!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("❌ Error al actualizar. Intenta de nuevo.")


# ══════════════════════════════════════════════════════════════════════════════
# PANTALLA: SELECTOR
# ══════════════════════════════════════════════════════════════════════════════

def pantalla_selector():
    inyectar_css_selector()
    nombre       = st.session_state.nombre_completo or "Analista"
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
            st.session_state.vista             = "individual"
            st.session_state.hechos_individual = []
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('<p style="text-align:center;font-size:11px;color:#444;margin-top:10px;">Un caso por registro</p>', unsafe_allow_html=True)

    with col2:
        st.markdown('<div style="text-align:center;margin-bottom:12px;"><span style="font-size:32px;">👥</span></div>', unsafe_allow_html=True)
        st.markdown('<div class="btn-colectivo">', unsafe_allow_html=True)
        if st.button("FORMULARIO\nCOLECTIVO", key="btn_colectivo", use_container_width=True):
            st.session_state.vista            = "colectivo"
            st.session_state.hechos_colectivo = []
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('<p style="text-align:center;font-size:11px;color:#444;margin-top:10px;">Múltiples personas afectadas</p>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    _, col_logout, _ = st.columns([2, 1, 2])
    with col_logout:
        if st.button("🚪 Cerrar sesión", use_container_width=True, type="secondary"):
            logout()


# ══════════════════════════════════════════════════════════════════════════════
# FORMULARIO INDIVIDUAL
# ══════════════════════════════════════════════════════════════════════════════

def formulario_individual():
    hoja_casos, hoja_hechos, sheet_url = conectar_sheets_individual()
    if hoja_casos is None:
        st.error("⚠️ No se pudo conectar a Google Sheets")
        return

    # Encabezado
    col_back, col_title = st.columns([1, 4])
    with col_back:
        if st.button("← Volver", type="secondary"):
            st.session_state.vista             = None
            st.session_state.hechos_individual = []
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
    st.subheader("📝 Información del Caso")

    ot_te = st.text_input("OT-TE *", placeholder="Ejemplo: OT-2024-001", key="ind_ot")

    col1, col2 = st.columns(2)
    with col1:
        edad         = st.number_input("Edad *", min_value=0, max_value=120, value=None, key="ind_edad")
        sexo         = st.selectbox("Sexo *", ["Seleccione...", "Hombre", "Mujer", "Otro", "No Reporta"], key="ind_sexo")
        departamento = st.text_input("Departamento *", placeholder="Ejemplo: Antioquia", key="ind_depto")
        año          = st.number_input("Año OT *", min_value=2000, max_value=2026, value=None, key="ind_anio")
	    mes          = st.number_input("Mes OT *", min_value=1, max_value=12, value=None, key="ind_mes")
    with col2:
        municipio    = st.text_input("Municipio *", placeholder="Ejemplo: Medellín", key="ind_muni")
        solicitante  = st.selectbox("Entidad Solicitante *", ["Seleccione...", "ARN", "SESP", "OTRO"], key="ind_sol")
        tipo_estudio = st.selectbox("Tipo de Estudio *", ["Seleccione...", "ORDEN DE TRABAJO OT", "TRÁMITE DE EMERGENCIA TE"], key="ind_tipo_estudio")
        nivel_riesgo = st.selectbox("Nivel de Riesgo *", ["Seleccione...", "EXTRAORDINARIO", "EXTREMO", "ORDINARIO"], key="ind_riesgo")

    observaciones = st.text_area("Observaciones (Opcional)", height=80, key="ind_obs")

    # Hechos de riesgo
    st.markdown("---")
    st.subheader("⚠️ Hechos de Riesgo")
    st.caption("Opcional. Agrega uno o varios hechos de riesgo asociados a este caso.")

    for i, hecho in enumerate(st.session_state.hechos_individual):
        with st.container(border=True):
            col_tit, col_del = st.columns([5, 1])
            with col_tit:
                st.markdown(f"**Hecho #{i+1} — {hecho['tipo']}**")
            with col_del:
                if st.button("🗑️", key=f"del_ind_{i}"):
                    st.session_state.hechos_individual.pop(i)
                    st.rerun()
            c1, c2 = st.columns(2)
            with c1:
                st.write(f"📅 **Fecha:** {hecho['fecha']}")
                st.write(f"📍 **Lugar:** {hecho['lugar']}")
            with c2:
                st.write(f"👤 **Autor:** {hecho['autor']}")
            st.write(f"📄 **Descripción:** {hecho['descripcion']}")

    with st.expander("➕ Agregar hecho de riesgo", expanded=len(st.session_state.hechos_individual) == 0):
        with st.form("form_hecho_individual", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                tipo_hecho  = st.selectbox("Tipo de Hecho *", [
                    "Seleccione...", "Amenaza", "Atentado", "Desplazamiento forzado",
                    "Homicidio", "Secuestro", "Extorsión", "Reclutamiento forzado",
                    "Violencia sexual", "Confinamiento", "Otro"])
                fecha_hecho = st.date_input("Fecha del Hecho *")
                lugar_hecho = st.text_input("Lugar donde ocurrió *", placeholder="Municipio, vereda, barrio...")
            with c2:
                autor_hecho       = st.text_input("Autor *", placeholder="Grupo armado, persona, etc.")
                descripcion_hecho = st.text_area("Descripción *", placeholder="Describe brevemente el hecho...", height=122)
            if st.form_submit_button("➕ Agregar este hecho", use_container_width=True):
                err_h = []
                if tipo_hecho == "Seleccione...": err_h.append("Selecciona el tipo de hecho")
                if not lugar_hecho.strip():        err_h.append("El lugar es obligatorio")
                if not autor_hecho.strip():        err_h.append("El autor es obligatorio")
                if not descripcion_hecho.strip():  err_h.append("La descripción es obligatoria")
                if err_h:
                    for e in err_h: st.error(f"• {e}")
                else:
                    st.session_state.hechos_individual.append({
                        "tipo": tipo_hecho,
                        "fecha": str(fecha_hecho),
                        "lugar": lugar_hecho.strip(),
                        "autor": autor_hecho.strip(),
                        "descripcion": descripcion_hecho.strip()
                    })
                    st.success("✅ Hecho agregado")
                    st.rerun()

    # Botón registrar
    st.markdown("---")
    if st.button("✅ REGISTRAR CASO INDIVIDUAL", use_container_width=True, type="primary"):
        errores = []
        if not ot_te or not ot_te.strip():               errores.append("El campo OT-TE es obligatorio")
        if edad is None or edad == 0:                    errores.append("La edad es obligatoria")
        if sexo == "Seleccione...":                      errores.append("Debe seleccionar un sexo")
        if not departamento or not departamento.strip(): errores.append("El departamento es obligatorio")
        if not municipio or not municipio.strip():       errores.append("El municipio es obligatorio")
        if solicitante == "Seleccione...":               errores.append("Debe seleccionar una entidad solicitante")
        if nivel_riesgo == "Seleccione...":              errores.append("Debe seleccionar un nivel de riesgo")
        if tipo_estudio == "Seleccione...":              errores.append("Debe seleccionar un tipo de estudio")    
        if año is None:                                  errores.append("el año es obligatorio")
	    if mes is None:                                  errores.append("el mes es obligatorio")
        
        if errores:
            st.error("❌ Por favor corrija los siguientes errores:")
            for e in errores: st.write(f"   • {e}")
        else:
            try:
                todas_filas   = hoja_casos.get_all_values()
                ot_existentes = [fila[1] for fila in todas_filas[1:]]
                if ot_te.strip() in ot_existentes:
                    st.error(f"❌ El caso '{ot_te}' ya existe en la hoja Individual")
                else:
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    id_caso   = obtener_siguiente_id(hoja_casos)
                    hoja_casos.append_row([
                        timestamp, ot_te.strip(), edad, sexo,
                        departamento.strip(), municipio.strip(), solicitante, nivel_riesgo,
                        observaciones.strip() if observaciones else "",
                        st.session_state.nombre_completo, st.session_state.username, id_caso, 
                        tipo_estudio, año, mes
                    ])
                    hechos_guardados = 0
                    for hecho in st.session_state.hechos_individual:
                        id_hecho = obtener_siguiente_id(hoja_hechos)
                        hoja_hechos.append_row([
                            id_hecho, id_caso, ot_te.strip(),
                            hecho["tipo"], hecho["fecha"], hecho["lugar"],
                            hecho["autor"], hecho["descripcion"],
                            st.session_state.nombre_completo, st.session_state.username
                        ])
                        hechos_guardados += 1
                    st.session_state.hechos_individual = []
                    st.success(f"✅ Caso **{ot_te}** registrado como Individual!")
                    if hechos_guardados > 0:
                        st.info(f"⚠️ {hechos_guardados} hecho(s) de riesgo registrados")
                    st.balloons()
                    st.info(f"""
                    **Resumen:**
                    - **ID Caso:** {id_caso}
                    - **OT-TE:** {ot_te}
                    - **Ubicación:** {municipio}, {departamento}
                    - **Nivel de Riesgo:** {nivel_riesgo}
                    - **Hechos registrados:** {hechos_guardados}
                    - **Registrado por:** {st.session_state.nombre_completo}
                    - **Fecha:** {timestamp}
                    """)
            except Exception as e:
                st.error(f"❌ Error al guardar: {e}")

    st.markdown("---")
    st.caption("🔒 Los datos se guardan en la hoja 'Individual' de Google Sheets")


# ══════════════════════════════════════════════════════════════════════════════
# FORMULARIO COLECTIVO
# ══════════════════════════════════════════════════════════════════════════════

SECTORES_COLECTIVO = [
    "Seleccione...",
    "Comunidad campesina",
    "Comunidad indígena",
    "Comunidad afrodescendiente",
    "Organización social",
    "Organización sindical",
    "Organización de mujeres",
    "Organización de jóvenes",
    "Organización LGBTIQ+",
    "Defensores de DDHH",
    "Líderes sociales",
    "Otro",
]

def formulario_colectivo():
    hoja_casos, hoja_hechos, sheet_url = conectar_sheets_colectivo()
    if hoja_casos is None:
        st.error("⚠️ No se pudo conectar a Google Sheets")
        return

    # Encabezado
    col_back, col_title = st.columns([1, 4])
    with col_back:
        if st.button("← Volver", type="secondary"):
            st.session_state.vista            = None
            st.session_state.hechos_colectivo = []
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
    st.subheader("📝 Información del Colectivo")

    ot_te = st.text_input("OT-TE *", placeholder="Ejemplo: OT-2024-001", key="col_ot")

    col1, col2 = st.columns(2)
    with col1:
        nombre_colectivo = st.text_input(
            "Nombre del Colectivo *",
            placeholder="Nombre del grupo u organización",
            key="col_nombre"
        )
        fecha_creacion = st.date_input(
            "Fecha de Creación del Colectivo *",
            key="col_fecha"
        )
        sector = st.selectbox("Sector *", SECTORES_COLECTIVO, key="col_sector")
    with col2:
        departamento = st.text_input(
            "Departamento *",
            placeholder="Ejemplo: Córdoba",
            key="col_depto"
        )
        municipio = st.text_input(
            "Municipio *",
            placeholder="Ejemplo: Montería",
            key="col_muni"
        )

    # Hechos de riesgo
    st.markdown("---")
    st.subheader("⚠️ Hechos de Riesgo")
    st.caption("Opcional. Agrega uno o varios hechos de riesgo asociados a este colectivo.")

    for i, hecho in enumerate(st.session_state.hechos_colectivo):
        with st.container(border=True):
            col_tit, col_del = st.columns([5, 1])
            with col_tit:
                st.markdown(f"**Hecho #{i+1} — {hecho['tipo']}**")
            with col_del:
                if st.button("🗑️", key=f"del_col_{i}"):
                    st.session_state.hechos_colectivo.pop(i)
                    st.rerun()
            c1, c2 = st.columns(2)
            with c1:
                st.write(f"📅 **Fecha:** {hecho['fecha']}")
                st.write(f"📍 **Lugar:** {hecho['lugar']}")
            with c2:
                st.write(f"👤 **Autor:** {hecho['autor']}")
            st.write(f"📄 **Descripción:** {hecho['descripcion']}")

    with st.expander("➕ Agregar hecho de riesgo", expanded=len(st.session_state.hechos_colectivo) == 0):
        with st.form("form_hecho_colectivo", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                tipo_hecho  = st.selectbox("Tipo de Hecho *", [
                    "Seleccione...", "Amenaza", "Atentado", "Desplazamiento forzado",
                    "Homicidio", "Secuestro", "Extorsión", "Reclutamiento forzado",
                    "Violencia sexual", "Confinamiento", "Otro"])
                fecha_hecho = st.date_input("Fecha del Hecho *")
                lugar_hecho = st.text_input("Lugar donde ocurrió *", placeholder="Municipio, vereda, barrio...")
            with c2:
                autor_hecho       = st.text_input("Autor *", placeholder="Grupo armado, persona, etc.")
                descripcion_hecho = st.text_area("Descripción *", placeholder="Describe brevemente el hecho...", height=122)
            if st.form_submit_button("➕ Agregar este hecho", use_container_width=True):
                err_h = []
                if tipo_hecho == "Seleccione...": err_h.append("Selecciona el tipo de hecho")
                if not lugar_hecho.strip():        err_h.append("El lugar es obligatorio")
                if not autor_hecho.strip():        err_h.append("El autor es obligatorio")
                if not descripcion_hecho.strip():  err_h.append("La descripción es obligatoria")
                if err_h:
                    for e in err_h: st.error(f"• {e}")
                else:
                    st.session_state.hechos_colectivo.append({
                        "tipo": tipo_hecho,
                        "fecha": str(fecha_hecho),
                        "lugar": lugar_hecho.strip(),
                        "autor": autor_hecho.strip(),
                        "descripcion": descripcion_hecho.strip()
                    })
                    st.success("✅ Hecho agregado")
                    st.rerun()

    # Botón registrar
    st.markdown("---")
    if st.button("✅ REGISTRAR CASO COLECTIVO", use_container_width=True, type="primary"):
        errores = []
        if not ot_te or not ot_te.strip():                       errores.append("El campo OT-TE es obligatorio")
        if not nombre_colectivo or not nombre_colectivo.strip(): errores.append("El nombre del colectivo es obligatorio")
        if sector == "Seleccione...":                            errores.append("Debe seleccionar un sector")
        if not departamento or not departamento.strip():         errores.append("El departamento es obligatorio")
        if not municipio or not municipio.strip():               errores.append("El municipio es obligatorio")

        if errores:
            st.error("❌ Por favor corrija los siguientes errores:")
            for e in errores: st.write(f"   • {e}")
        else:
            try:
                todas_filas   = hoja_casos.get_all_values()
                ot_existentes = [fila[1] for fila in todas_filas[1:]]
                if ot_te.strip() in ot_existentes:
                    st.error(f"❌ El caso '{ot_te}' ya existe en la hoja Colectivo")
                else:
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    id_caso   = obtener_siguiente_id(hoja_casos)
                    hoja_casos.append_row([
                        timestamp,
                        ot_te.strip(),
                        nombre_colectivo.strip(),
                        str(fecha_creacion),
                        sector,
                        departamento.strip(),
                        municipio.strip(),
                        st.session_state.nombre_completo,
                        st.session_state.username,
                        id_caso
                    ])
                    hechos_guardados = 0
                    for hecho in st.session_state.hechos_colectivo:
                        id_hecho = obtener_siguiente_id(hoja_hechos)
                        hoja_hechos.append_row([
                            id_hecho, id_caso, ot_te.strip(),
                            hecho["tipo"], hecho["fecha"], hecho["lugar"],
                            hecho["autor"], hecho["descripcion"],
                            st.session_state.nombre_completo, st.session_state.username
                        ])
                        hechos_guardados += 1
                    st.session_state.hechos_colectivo = []
                    st.success(f"✅ Caso **{ot_te}** registrado como Colectivo!")
                    if hechos_guardados > 0:
                        st.info(f"⚠️ {hechos_guardados} hecho(s) de riesgo registrados")
                    st.balloons()
                    st.info(f"""
                    **Resumen:**
                    - **ID Caso:** {id_caso}
                    - **OT-TE:** {ot_te}
                    - **Colectivo:** {nombre_colectivo}
                    - **Sector:** {sector}
                    - **Ubicación:** {municipio}, {departamento}
                    - **Fecha creación colectivo:** {fecha_creacion}
                    - **Hechos registrados:** {hechos_guardados}
                    - **Registrado por:** {st.session_state.nombre_completo}
                    - **Fecha registro:** {timestamp}
                    """)
            except Exception as e:
                st.error(f"❌ Error al guardar: {e}")

    st.markdown("---")
    st.caption("🔒 Los datos se guardan en la hoja 'Colectivo' de Google Sheets")


# ══════════════════════════════════════════════════════════════════════════════
# PANEL: VISUALIZACIÓN
# ══════════════════════════════════════════════════════════════════════════════

def panel_visualizacion():
    st.title("📊 Casos Registrados")
    st.markdown("---")
    tab_ind, tab_col = st.tabs(["👤 Individual", "👥 Colectivo"])

    # Tab Individual
    with tab_ind:
        hoja_casos, hoja_hechos, sheet_url = conectar_sheets_individual()
        if hoja_casos is None:
            st.error("No se pudo conectar a la hoja Individual")
        else:
            if sheet_url:
                st.markdown(f"[📝 Abrir en Google Sheets]({sheet_url})")
            sub1, sub2 = st.tabs(["📋 Casos", "⚠️ Hechos de Riesgo"])

            with sub1:
                try:
                    datos = hoja_casos.get_all_records()
                    if datos:
                        df = pd.DataFrame(datos)
                        c1, c2, c3, c4 = st.columns(4)
                        c1.metric("Total Casos",   len(df))
                        c2.metric("Departamentos", df["Departamento"].nunique()  if "Departamento"  in df.columns else 0)
                        c3.metric("Municipios",    df["Municipio"].nunique()     if "Municipio"     in df.columns else 0)
                        c4.metric("Riesgo Alto",   df["Nivel de Riesgo"].isin(["EXTREMO","EXTRAORDINARIO"]).sum() if "Nivel de Riesgo" in df.columns else 0)
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            depto = st.selectbox("Departamento", ["Todos"] + sorted(df["Departamento"].unique().tolist()) if "Departamento" in df.columns else ["Todos"], key="vi_ind_depto")
                        with col2:
                            riesgo = st.selectbox("Nivel de Riesgo", ["Todos"] + sorted(df["Nivel de Riesgo"].unique().tolist()) if "Nivel de Riesgo" in df.columns else ["Todos"], key="vi_ind_riesgo")
                        with col3:
                            analista_f = st.selectbox("Analista", ["Todos"] + sorted(df["Analista"].unique().tolist()) if "Analista" in df.columns else ["Todos"], key="vi_ind_analista")
                        df_f = df.copy()
                        if depto      != "Todos" and "Departamento"    in df.columns: df_f = df_f[df_f["Departamento"]    == depto]
                        if riesgo     != "Todos" and "Nivel de Riesgo" in df.columns: df_f = df_f[df_f["Nivel de Riesgo"] == riesgo]
                        if analista_f != "Todos" and "Analista"        in df.columns: df_f = df_f[df_f["Analista"]        == analista_f]
                        st.subheader(f"📋 Resultados ({len(df_f)} casos)")
                        st.dataframe(df_f, use_container_width=True, hide_index=True)
                        csv = df_f.to_csv(index=False, encoding="utf-8-sig")
                        st.download_button("📥 Descargar CSV", csv,
                                           f"casos_individual_{datetime.now().strftime('%Y%m%d')}.csv",
                                           "text/csv", key="dl_casos_ind")
                    else:
                        st.info("📭 No hay casos individuales registrados")
                except Exception as e:
                    st.error(f"Error al cargar casos individuales: {e}")

            with sub2:
                try:
                    datos_h = hoja_hechos.get_all_records()
                    if datos_h:
                        df_h = pd.DataFrame(datos_h)
                        c1, c2, c3 = st.columns(3)
                        c1.metric("Total Hechos",    len(df_h))
                        c2.metric("Tipos distintos",  df_h["Tipo de Hecho"].nunique() if "Tipo de Hecho" in df_h.columns else 0)
                        c3.metric("Casos con hechos", df_h["ID_Caso"].nunique()       if "ID_Caso"       in df_h.columns else 0)
                        tipo_f = st.selectbox("Filtrar por Tipo", ["Todos"] + sorted(df_h["Tipo de Hecho"].unique().tolist()) if "Tipo de Hecho" in df_h.columns else ["Todos"], key="vi_ind_tipo_hecho")
                        df_hf  = df_h[df_h["Tipo de Hecho"] == tipo_f].copy() if tipo_f != "Todos" else df_h.copy()
                        st.dataframe(df_hf, use_container_width=True, hide_index=True)
                        csv_h = df_hf.to_csv(index=False, encoding="utf-8-sig")
                        st.download_button("📥 Descargar CSV Hechos", csv_h,
                                           f"hechos_individual_{datetime.now().strftime('%Y%m%d')}.csv",
                                           "text/csv", key="dl_hechos_ind")
                    else:
                        st.info("📭 No hay hechos individuales registrados")
                except Exception as e:
                    st.error(f"Error al cargar hechos individuales: {e}")

    # Tab Colectivo
    with tab_col:
        hoja_casos, hoja_hechos, sheet_url = conectar_sheets_colectivo()
        if hoja_casos is None:
            st.error("No se pudo conectar a la hoja Colectivo")
        else:
            if sheet_url:
                st.markdown(f"[📝 Abrir en Google Sheets]({sheet_url})")
            sub1, sub2 = st.tabs(["📋 Casos", "⚠️ Hechos de Riesgo"])

            with sub1:
                try:
                    datos = hoja_casos.get_all_records()
                    if datos:
                        df = pd.DataFrame(datos)
                        c1, c2, c3, c4 = st.columns(4)
                        c1.metric("Total Colectivos", len(df))
                        c2.metric("Departamentos",    df["Departamento"].nunique() if "Departamento" in df.columns else 0)
                        c3.metric("Municipios",       df["Municipio"].nunique()    if "Municipio"    in df.columns else 0)
                        c4.metric("Sectores",         df["Sector"].nunique()       if "Sector"       in df.columns else 0)
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            depto = st.selectbox("Departamento", ["Todos"] + sorted(df["Departamento"].unique().tolist()) if "Departamento" in df.columns else ["Todos"], key="vi_col_depto")
                        with col2:
                            sector_f = st.selectbox("Sector", ["Todos"] + sorted(df["Sector"].unique().tolist()) if "Sector" in df.columns else ["Todos"], key="vi_col_sector")
                        with col3:
                            analista_f = st.selectbox("Analista", ["Todos"] + sorted(df["Analista"].unique().tolist()) if "Analista" in df.columns else ["Todos"], key="vi_col_analista")
                        df_f = df.copy()
                        if depto      != "Todos" and "Departamento" in df.columns: df_f = df_f[df_f["Departamento"] == depto]
                        if sector_f   != "Todos" and "Sector"       in df.columns: df_f = df_f[df_f["Sector"]       == sector_f]
                        if analista_f != "Todos" and "Analista"     in df.columns: df_f = df_f[df_f["Analista"]     == analista_f]
                        st.subheader(f"📋 Resultados ({len(df_f)} colectivos)")
                        st.dataframe(df_f, use_container_width=True, hide_index=True)
                        csv = df_f.to_csv(index=False, encoding="utf-8-sig")
                        st.download_button("📥 Descargar CSV", csv,
                                           f"casos_colectivo_{datetime.now().strftime('%Y%m%d')}.csv",
                                           "text/csv", key="dl_casos_col")
                    else:
                        st.info("📭 No hay casos colectivos registrados")
                except Exception as e:
                    st.error(f"Error al cargar casos colectivos: {e}")

            with sub2:
                try:
                    datos_h = hoja_hechos.get_all_records()
                    if datos_h:
                        df_h = pd.DataFrame(datos_h)
                        c1, c2, c3 = st.columns(3)
                        c1.metric("Total Hechos",    len(df_h))
                        c2.metric("Tipos distintos",  df_h["Tipo de Hecho"].nunique() if "Tipo de Hecho" in df_h.columns else 0)
                        c3.metric("Casos con hechos", df_h["ID_Caso"].nunique()       if "ID_Caso"       in df_h.columns else 0)
                        tipo_f = st.selectbox("Filtrar por Tipo", ["Todos"] + sorted(df_h["Tipo de Hecho"].unique().tolist()) if "Tipo de Hecho" in df_h.columns else ["Todos"], key="vi_col_tipo_hecho")
                        df_hf  = df_h[df_h["Tipo de Hecho"] == tipo_f].copy() if tipo_f != "Todos" else df_h.copy()
                        st.dataframe(df_hf, use_container_width=True, hide_index=True)
                        csv_h = df_hf.to_csv(index=False, encoding="utf-8-sig")
                        st.download_button("📥 Descargar CSV Hechos", csv_h,
                                           f"hechos_colectivo_{datetime.now().strftime('%Y%m%d')}.csv",
                                           "text/csv", key="dl_hechos_col")
                    else:
                        st.info("📭 No hay hechos colectivos registrados")
                except Exception as e:
                    st.error(f"Error al cargar hechos colectivos: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# PANEL: GESTIÓN DE USUARIOS
# ══════════════════════════════════════════════════════════════════════════════

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
                nuevo_nombre   = st.text_input("Nombre Completo *", placeholder="Juan Pérez")
            with col2:
                password_default = st.text_input("Contraseña por Defecto *", value="ISMR2024")
                es_admin_nuevo   = st.checkbox("¿Es Administrador?", value=False)
            st.info("💡 El usuario deberá cambiar la contraseña en su primer acceso")
            if st.form_submit_button("✅ Crear Usuario", use_container_width=True, type="primary"):
                if nuevo_username and nuevo_nombre and password_default:
                    phash = hashlib.sha256(password_default.encode()).hexdigest()
                    if crear_usuario(nuevo_username, phash, nuevo_nombre, es_admin_nuevo, True):
                        st.success(f"✅ Usuario '{nuevo_username}' creado!")
                        st.info(f"Usuario: **{nuevo_username}** | Contraseña temporal: **{password_default}**")
                    else:
                        st.error("❌ El usuario ya existe o hubo un problema al crearlo")
                else:
                    st.warning("⚠️ Completa todos los campos")

    with tab2:
        st.subheader("📋 Lista de Usuarios")
        usuarios = listar_usuarios()
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
            for u in listar_usuarios():
                with st.expander(f"👤 {u.get('nombre_completo','?')} (@{u.get('username','?')})"):
                    st.code(u.get("password_hash", "N/A"), language=None)
                    st.caption(f"Debe cambiar: {u.get('debe_cambiar_password','N/A')}")


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

def main():
    if not st.session_state.autenticado:
        login_page()
        return

    if st.session_state.debe_cambiar_password:
        pantalla_cambiar_password()
        return

    # Administrador: sidebar con menú completo
    if st.session_state.es_admin:
        st.sidebar.title("📊 Sistema ISMR")
        st.sidebar.success(f"👤 {st.session_state.nombre_completo}")
        st.sidebar.markdown("---")
        opcion = st.sidebar.radio("Menú", [
            "🏠 Inicio",
            "👤 Individual",
            "👥 Colectivo",
            "📊 Ver Datos",
            "👥 Gestionar Usuarios"
        ])
        if st.sidebar.button("🚪 Cerrar Sesión", use_container_width=True):
            logout()

        if   opcion == "🏠 Inicio":             pantalla_selector()
        elif opcion == "👤 Individual":         formulario_individual()
        elif opcion == "👥 Colectivo":          formulario_colectivo()
        elif opcion == "📊 Ver Datos":          panel_visualizacion()
        else:                                   panel_gestion_usuarios()
        return

    # Analista: flujo por selector
    vista = st.session_state.vista
    if   vista is None:         pantalla_selector()
    elif vista == "individual": formulario_individual()
    elif vista == "colectivo":  formulario_colectivo()


if __name__ == "__main__":
    main()
