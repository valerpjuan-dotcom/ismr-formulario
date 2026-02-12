import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import pandas as pd
import json
import hashlib

# ============================================================================
# CONFIGURACIÓN DE SEGURIDAD
# ============================================================================

def verificar_credenciales_analista(username, password):
    """Verifica las credenciales de un analista"""
    try:
        analistas = st.secrets.get("analistas", {})
        
        if username not in analistas:
            return False, None
        
        # Hash de la contraseña ingresada
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        # Comparar con el hash almacenado
        if password_hash == analistas[username]["password_hash"]:
            return True, analistas[username]["nombre_completo"]
        return False, None
        
    except Exception as e:
        st.error(f"Error en autenticación: {str(e)}")
        return False, None

def verificar_credenciales_admin(username, password):
    """Verifica las credenciales de un administrador"""
    try:
        admins = st.secrets.get("administradores", {})
        
        if username not in admins:
            return False
        
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        return password_hash == admins[username]["password_hash"]
        
    except Exception as e:
        st.error(f"Error en autenticación: {str(e)}")
        return False

def login_analista():
    """Página de login para analistas antes de llenar el formulario"""
    st.title("🔐 Acceso de Analistas")
    st.markdown("---")
    
    st.info("👋 Identifícate para registrar casos")
    
    with st.form("login_analista_form"):
        col1, col2 = st.columns([2, 1])
        
        with col1:
            username = st.text_input("Usuario", placeholder="tu.usuario")
            password = st.text_input("Contraseña", type="password")
        
        submit = st.form_submit_button("🔓 Iniciar Sesión", use_container_width=True, type="primary")
        
        if submit:
            if username and password:
                es_valido, nombre_completo = verificar_credenciales_analista(username, password)
                if es_valido:
                    st.session_state.analista_autenticado = True
                    st.session_state.analista_username = username
                    st.session_state.analista_nombre = nombre_completo
                    st.success(f"✅ Bienvenido, {nombre_completo}")
                    st.rerun()
                else:
                    st.error("❌ Usuario o contraseña incorrectos")
            else:
                st.warning("⚠️ Por favor completa todos los campos")
    
    st.markdown("---")
    st.caption("🔒 Si olvidaste tu contraseña, contacta al administrador del sistema")

def login_admin():
    """Página de login para administradores"""
    st.title("🔐 Acceso Administrativo")
    st.markdown("---")
    
    with st.form("login_admin_form"):
        username = st.text_input("Usuario Administrador")
        password = st.text_input("Contraseña", type="password")
        submit = st.form_submit_button("Iniciar Sesión", use_container_width=True)
        
        if submit:
            if verificar_credenciales_admin(username, password):
                st.session_state.admin_autenticado = True
                st.session_state.admin_username = username
                st.rerun()
            else:
                st.error("❌ Usuario o contraseña incorrectos")
    
    st.markdown("---")
    st.info("💡 Si olvidaste tu contraseña, contacta al administrador del sistema")

def logout_analista():
    """Cierra la sesión del analista"""
    st.session_state.analista_autenticado = False
    st.session_state.analista_username = None
    st.session_state.analista_nombre = None
    st.rerun()

def logout_admin():
    """Cierra la sesión del administrador"""
    st.session_state.admin_autenticado = False
    st.session_state.admin_username = None
    st.rerun()

def require_admin(func):
    """Decorador para requerir autenticación de admin"""
    def wrapper(*args, **kwargs):
        if not st.session_state.get("admin_autenticado", False):
            login_admin()
            return
        return func(*args, **kwargs)
    return wrapper

# ============================================================================
# CONFIGURACIÓN DE STREAMLIT
# ============================================================================

st.set_page_config(
    page_title="Formulario ISMR",
    page_icon="📋",
    layout="centered"
)

# Inicializar session state
if "analista_autenticado" not in st.session_state:
    st.session_state.analista_autenticado = False
if "analista_username" not in st.session_state:
    st.session_state.analista_username = None
if "analista_nombre" not in st.session_state:
    st.session_state.analista_nombre = None
if "admin_autenticado" not in st.session_state:
    st.session_state.admin_autenticado = False
if "admin_username" not in st.session_state:
    st.session_state.admin_username = None

# ============================================================================
# CONEXIÓN A GOOGLE SHEETS
# ============================================================================

def conectar_google_sheets():
    """Conecta con Google Sheets usando credenciales"""
    try:
        credentials_dict = st.secrets["gcp_service_account"]
        
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        
        credentials = Credentials.from_service_account_info(
            credentials_dict,
            scopes=scopes
        )
        
        client = gspread.authorize(credentials)
        sheet_name = st.secrets.get("sheet_name", "ISMR_Casos")
        spreadsheet = client.open(sheet_name)
        worksheet = spreadsheet.sheet1
        
        # Encabezados esperados
        headers = [
            "Timestamp",
            "OT-TE",
            "Edad",
            "Sexo",
            "Departamento",
            "Municipio",
            "Solicitante",
            "Nivel de Riesgo",
            "Observaciones",
            "Analista",
            "Usuario Analista"  # ← NUEVO: Para saber el usuario que llenó
        ]
        
        current_headers = worksheet.row_values(1)
        
        if not current_headers:
            worksheet.append_row(headers)
        else:
            if current_headers != headers:
                worksheet.update('A1', [headers])
        
        return worksheet, spreadsheet.url
        
    except Exception as e:
        st.error(f"Error al conectar con Google Sheets: {str(e)}")
        return None, None

# ============================================================================
# FORMULARIO PÚBLICO (AHORA REQUIERE LOGIN DE ANALISTA)
# ============================================================================

def formulario_publico():
    """Formulario tipo KoBoToolbox"""
    
    # VERIFICAR SI EL ANALISTA ESTÁ AUTENTICADO
    if not st.session_state.get("analista_autenticado", False):
        login_analista()
        return
    
    # Conectar a Google Sheets
    worksheet, sheet_url = conectar_google_sheets()
    
    if worksheet is None:
        st.error("⚠️ No se pudo conectar a Google Sheets. Verifica la configuración.")
        return
    
    # Header del formulario con información del analista
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.title("📋 Formulario de Registro de Casos ISMR")
    
    with col2:
        st.success(f"👤 {st.session_state.analista_nombre}")
        if st.button("🚪 Salir", use_container_width=True):
            logout_analista()
    
    st.markdown("---")
    
    st.info(f"📝 Registrando como: **{st.session_state.analista_nombre}**")
    
    # Formulario
    with st.form("formulario_casos", clear_on_submit=True):
        
        st.subheader("📝 Información del Caso")
        
        # Campo OT-TE
        ot_te = st.text_input(
            "OT-TE *",
            placeholder="Ejemplo: OT-2024-001",
            help="Código único del caso"
        )
        
        col1, col2 = st.columns(2)
        
        with col1:
            edad = st.number_input(
                "Edad *",
                min_value=0,
                max_value=120,
                value=None,
                help="Edad de la persona"
            )
            
            sexo = st.selectbox(
                "Sexo *",
                ["Seleccione...", "Hombre", "Mujer", "Otro", "No Reporta"]
            )
            
            departamento = st.text_input(
                "Departamento de Residencia *",
                placeholder="Ejemplo: Antioquia"
            )
        
        with col2:
            municipio = st.text_input(
                "Municipio de Residencia *",
                placeholder="Ejemplo: Medellín"
            )
            
            solicitante = st.selectbox(
                "Entidad Solicitante *",
                ["Seleccione...", "ARN", "SESP", "OTRO"]
            )
            
            nivel_riesgo = st.selectbox(
                "Nivel de Riesgo *",
                ["Seleccione...", "EXTRAORDINARIO", "EXTREMO", "ORDINARIO"]
            )
        
        # Observaciones
        observaciones = st.text_area(
            "Observaciones (Opcional)",
            placeholder="Información adicional relevante...",
            height=100
        )
        
        st.markdown("---")
        
        # Botón de envío
        submitted = st.form_submit_button(
            "✅ REGISTRAR CASO",
            use_container_width=True,
            type="primary"
        )
        
        if submitted:
            # Validaciones
            errores = []
            
            if not ot_te or ot_te.strip() == "":
                errores.append("El campo OT-TE es obligatorio")
            if edad is None or edad == 0:
                errores.append("La edad es obligatoria")
            if sexo == "Seleccione...":
                errores.append("Debe seleccionar un sexo")
            if not departamento or departamento.strip() == "":
                errores.append("El departamento es obligatorio")
            if not municipio or municipio.strip() == "":
                errores.append("El municipio es obligatorio")
            if solicitante == "Seleccione...":
                errores.append("Debe seleccionar una entidad solicitante")
            if nivel_riesgo == "Seleccione...":
                errores.append("Debe seleccionar un nivel de riesgo")
            
            if errores:
                st.error("❌ Por favor corrija los siguientes errores:")
                for error in errores:
                    st.write(f"   • {error}")
            else:
                try:
                    # Verificar duplicados
                    todas_filas = worksheet.get_all_values()
                    ot_existentes = [fila[1] for fila in todas_filas[1:]]
                    
                    if ot_te.strip() in ot_existentes:
                        st.error(f"❌ El caso con OT-TE '{ot_te}' ya existe en el sistema")
                    else:
                        # Preparar datos
                        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        nueva_fila = [
                            timestamp,
                            ot_te.strip(),
                            edad,
                            sexo,
                            departamento.strip(),
                            municipio.strip(),
                            solicitante,
                            nivel_riesgo,
                            observaciones.strip() if observaciones else "",
                            st.session_state.analista_nombre,  # ← Nombre completo del analista
                            st.session_state.analista_username  # ← Usuario del analista
                        ]
                        
                        # Guardar en Google Sheets
                        worksheet.append_row(nueva_fila)
                        
                        # Mensaje de éxito
                        st.success(f"✅ Caso {ot_te} registrado exitosamente!")
                        st.balloons()
                        
                        # Mostrar resumen
                        st.info(f"""
                        **Resumen del registro:**
                        - **OT-TE:** {ot_te}
                        - **Municipio:** {municipio}, {departamento}
                        - **Nivel de Riesgo:** {nivel_riesgo}
                        - **Registrado por:** {st.session_state.analista_nombre}
                        - **Fecha:** {timestamp}
                        """)
                        
                except Exception as e:
                    st.error(f"❌ Error al guardar: {str(e)}")
    
    # Footer
    st.markdown("---")
    st.caption("🔒 Tus datos están seguros y se almacenan de forma automática")

# ============================================================================
# PANEL DE VISUALIZACIÓN (PROTEGIDO PARA ADMINS)
# ============================================================================

@require_admin
def panel_visualizacion():
    """Panel para ver los datos registrados - REQUIERE AUTENTICACIÓN ADMIN"""
    
    # Botón de cerrar sesión en el sidebar
    with st.sidebar:
        st.success(f"👤 Admin: {st.session_state.admin_username}")
        if st.button("🚪 Cerrar Sesión", use_container_width=True):
            logout_admin()
    
    worksheet, sheet_url = conectar_google_sheets()
    
    if worksheet is None:
        st.error("No se pudo conectar a Google Sheets")
        return
    
    st.title("📊 Casos Registrados")
    st.markdown("---")
    
    # Botón para abrir Google Sheets
    if sheet_url:
        st.markdown(f"[📝 Abrir en Google Sheets]({sheet_url})")
    
    # Obtener datos
    try:
        datos = worksheet.get_all_records()
        
        if datos:
            df = pd.DataFrame(datos)
            
            # Métricas
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total Casos", len(df))
            
            with col2:
                if 'Departamento' in df.columns:
                    st.metric("Departamentos", df['Departamento'].nunique())
            
            with col3:
                if 'Municipio' in df.columns:
                    st.metric("Municipios", df['Municipio'].nunique())
            
            with col4:
                if 'Nivel de Riesgo' in df.columns:
                    riesgo_alto = df['Nivel de Riesgo'].isin(['EXTREMO', 'EXTRAORDINARIO']).sum()
                    st.metric("Riesgo Alto", riesgo_alto)
            
            # Filtros
            st.subheader("🔍 Filtrar datos")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if 'Departamento' in df.columns:
                    depto = st.selectbox(
                        "Departamento",
                        ["Todos"] + sorted(df['Departamento'].unique().tolist())
                    )
                else:
                    depto = "Todos"
            
            with col2:
                if 'Nivel de Riesgo' in df.columns:
                    riesgo = st.selectbox(
                        "Nivel de Riesgo",
                        ["Todos"] + sorted(df['Nivel de Riesgo'].unique().tolist())
                    )
                else:
                    riesgo = "Todos"
            
            with col3:
                if 'Analista' in df.columns:
                    analista_filtro = st.selectbox(
                        "Analista",
                        ["Todos"] + sorted(df['Analista'].unique().tolist())
                    )
                else:
                    analista_filtro = "Todos"
            
            # Aplicar filtros
            df_filtrado = df.copy()
            
            if depto != "Todos" and 'Departamento' in df.columns:
                df_filtrado = df_filtrado[df_filtrado['Departamento'] == depto]
            
            if riesgo != "Todos" and 'Nivel de Riesgo' in df.columns:
                df_filtrado = df_filtrado[df_filtrado['Nivel de Riesgo'] == riesgo]
            
            if analista_filtro != "Todos" and 'Analista' in df.columns:
                df_filtrado = df_filtrado[df_filtrado['Analista'] == analista_filtro]
            
            # Mostrar tabla
            st.subheader(f"📋 Resultados ({len(df_filtrado)} casos)")
            st.dataframe(df_filtrado, use_container_width=True)
            
            # Descargar CSV
            csv = df_filtrado.to_csv(index=False, encoding='utf-8-sig')
            st.download_button(
                label="📥 Descargar CSV",
                data=csv,
                file_name=f"casos_ismr_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
            
        else:
            st.info("📭 No hay casos registrados todavía")
            
    except Exception as e:
        st.error(f"Error al cargar datos: {str(e)}")

# ============================================================================
# APLICACIÓN PRINCIPAL
# ============================================================================

def main():
    
    # Detectar modo
    query_params = st.query_params
    
    # MODO PÚBLICO (FORMULARIO CON LOGIN DE ANALISTA)
    if 'admin' not in query_params:
        formulario_publico()
    else:
        # MODO ADMINISTRADOR
        if not st.session_state.get("admin_autenticado", False):
            login_admin()
        else:
            # Menú lateral
            st.sidebar.title("📊 Sistema ISMR")
            st.sidebar.markdown("---")
            
            opcion = st.sidebar.radio(
                "Menú",
                ["📋 Formulario", "📊 Ver Datos"]
            )
            
            # Mostrar sección
            if opcion == "📋 Formulario":
                formulario_publico()
            else:
                panel_visualizacion()

if __name__ == "__main__":
    main()
