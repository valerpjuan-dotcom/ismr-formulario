import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import pandas as pd
import json

# ============================================================================
# CONFIGURACIÓN
# ============================================================================

st.set_page_config(
    page_title="Formulario ISMR",
    page_icon="📋",
    layout="centered"
)

# Configurar conexión con Google Sheets
def conectar_google_sheets():
    """Conecta con Google Sheets usando credenciales"""
    try:
        # Cargar credenciales desde Streamlit secrets
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
        
        # Nombre de tu hoja de cálculo en Google Sheets
        sheet_name = st.secrets.get("sheet_name", "ISMR_Casos")
        
        try:
            # Intentar abrir hoja existente
            spreadsheet = client.open(sheet_name)
        except:
            # Si no existe, crearla
            spreadsheet = client.create(sheet_name)
            # Compartir con tu email para que puedas verla
            spreadsheet.share(
                st.secrets.get("admin_email", ""),
                perm_type='user',
                role='writer'
            )
        
        # Obtener la primera hoja
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
            "Analista"
        ]
        
        # Obtener primera fila actual
        current_headers = worksheet.row_values(1)
        
        # Si la hoja está vacía → agregar encabezados
        if not current_headers:
            worksheet.append_row(headers)
        
        # Si ya existe pero falta alguna columna → actualizar
        else:
            if current_headers != headers:
                worksheet.update('A1', [headers])

        
        return worksheet, spreadsheet.url
        
    except Exception as e:
        st.error(f"Error al conectar con Google Sheets: {str(e)}")
        return None, None

# ============================================================================
# FORMULARIO PÚBLICO
# ============================================================================

def formulario_publico():
    """Formulario tipo KoBoToolbox"""
    
    # Conectar a Google Sheets
    worksheet, sheet_url = conectar_google_sheets()
    
    if worksheet is None:
        st.error("⚠️ No se pudo conectar a Google Sheets. Verifica la configuración.")
        with st.expander("ℹ️ Ver instrucciones de configuración"):
            st.markdown("""
            ### Pasos para configurar:
            
            1. Ve a la **GUIA_GOOGLE_SHEETS.md** 
            2. Sigue los pasos para obtener credenciales
            3. Configura los secrets en Streamlit
            """)
        return
    
    # Header del formulario
    st.title("📋 Formulario de Registro de Casos ISMR")
    st.markdown("---")
    
    st.info("👋 Complete el siguiente formulario para registrar un nuevo caso")
    
    # Formulario
    with st.form("formulario_casos", clear_on_submit=True):
        
        st.subheader("📝 Información del Caso")
        
        # Campo OT-TE
        ot_te = st.text_input(
            "OT-TE *",
            placeholder="Ejemplo: OT-2024-001",
            help="Código único del caso"
        )

        # Analista
        analista = st.text_area(
            "Analista",
            placeholder="Escriba su nombre",
            height=100
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
                    ot_existentes = [fila[1] for fila in todas_filas[1:]]  # Skip header
                    
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
                            analista.strip()
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
                        - **Fecha:** {timestamp}
                        """)
                        
                except Exception as e:
                    st.error(f"❌ Error al guardar: {str(e)}")
    
    # Footer con información
    st.markdown("---")
    st.caption("🔒 Tus datos están seguros y se almacenan de forma automática")

# ============================================================================
# PANEL DE VISUALIZACIÓN (OPCIONAL)
# ============================================================================

def panel_visualizacion():
    """Panel para ver los datos registrados"""
    
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
            
            col1, col2 = st.columns(2)
            
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
            
            # Aplicar filtros
            df_filtrado = df.copy()
            
            if depto != "Todos" and 'Departamento' in df.columns:
                df_filtrado = df_filtrado[df_filtrado['Departamento'] == depto]
            
            if riesgo != "Todos" and 'Nivel de Riesgo' in df.columns:
                df_filtrado = df_filtrado[df_filtrado['Nivel de Riesgo'] == riesgo]
            
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
    
    # MODO PÚBLICO (por defecto)
    if 'admin' not in query_params:
        formulario_publico()
    else:
        # MODO ADMINISTRADOR
        # Menú lateral
        st.sidebar.title("📊 Sistema ISMR")
        st.sidebar.markdown("---")
        
        opcion = st.sidebar.radio(
            "Menú",
            ["📋 Formulario", "📊 Ver Datos"]
        )
        
        st.sidebar.markdown("---")
        st.sidebar.subheader("🔗 Enlace Público")
        
        # Generar URL pública
        url_base = st.sidebar.text_input(
            "URL de tu app",
            value="https://tu-app.streamlit.app",
            help="Cambia esto por tu URL real"
        )
        
        st.sidebar.code(url_base, language=None)
        st.sidebar.info("👆 Comparte este enlace para que registren casos")
        
        # Mostrar sección
        if opcion == "📋 Formulario":
            formulario_publico()
        else:
            panel_visualizacion()

if __name__ == "__main__":
    main()
