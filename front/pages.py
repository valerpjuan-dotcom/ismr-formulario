import streamlit as st
import hashlib
import time
import pandas as pd
from datetime import datetime

from configuration.settings import TAB_NOMBRES
from data.mongo.usuarios_repo import actualizar_password, crear_usuario, listar_usuarios
from data.mongo.casos_repo import conectar_sheet_casos
from service.auth_service import verificar_credenciales, logout, obtener_siguiente_id
from front.styles import inyectar_css_selector


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
                    st.session_state.hechos                = []
                    st.rerun()
                else: st.error("❌ Usuario o contraseña incorrectos")
            else: st.warning("⚠️ Por favor completa todos los campos")
    st.markdown("---")
    st.caption("🔒 Si tienes problemas, contacta al administrador")


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
            if not nueva: errores.append("La contraseña no puede estar vacía")
            elif len(nueva) < 8: errores.append("La contraseña debe tener mínimo 8 caracteres")
            if nueva != confirmar: errores.append("Las contraseñas no coinciden")
            if errores:
                for e in errores: st.error(f"❌ {e}")
            else:
                nuevo_hash = hashlib.sha256(nueva.encode()).hexdigest()
                if actualizar_password(st.session_state.username, nuevo_hash, False):
                    st.session_state.debe_cambiar_password = False
                    st.success("✅ ¡Contraseña actualizada!")
                    time.sleep(1); st.rerun()
                else: st.error("❌ Error al actualizar. Intenta de nuevo.")


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
            st.session_state.vista = "individual"; st.session_state.hechos = []; st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('<p style="text-align:center;font-size:11px;color:#444;margin-top:10px;">Un caso por registro</p>', unsafe_allow_html=True)

    with col2:
        st.markdown('<div style="text-align:center;margin-bottom:12px;"><span style="font-size:32px;">👥</span></div>', unsafe_allow_html=True)
        st.markdown('<div class="btn-colectivo">', unsafe_allow_html=True)
        if st.button("FORMULARIO\nCOLECTIVO", key="btn_colectivo", use_container_width=True):
            st.session_state.vista = "colectivo"; st.session_state.hechos = []; st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('<p style="text-align:center;font-size:11px;color:#444;margin-top:10px;">Múltiples personas afectadas</p>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    _, col_logout, _ = st.columns([2, 1, 2])
    with col_logout:
        if st.button("🚪 Cerrar sesión", use_container_width=True, type="secondary"): logout()


def formulario_casos(tipo="individual"):
    es_individual     = tipo == "individual"
    color             = "#4F8BFF" if es_individual else "#4ADE80"
    icono             = "👤"      if es_individual else "👥"
    label_badge       = "INDIVIDUAL" if es_individual else "COLECTIVO"
    titulo            = "Formulario Individual" if es_individual else "Formulario Colectivo"
    nombre_hoja_casos = TAB_NOMBRES[tipo]["casos"]   # FIX: accesible en todo el scope

    hoja_casos, hoja_hechos, hoja_perfiles, sheet_url = conectar_sheet_casos(tipo)
    if hoja_casos is None:
        st.error("⚠️ No se pudo conectar a Google Sheets"); return

    col_back, col_title = st.columns([1, 4])
    with col_back:
        if st.button("← Volver", type="secondary"):
            st.session_state.vista = None; st.session_state.hechos = []; st.rerun()
    with col_title:
        rgb = "79,139,255" if es_individual else "74,222,128"
        st.markdown(f"""
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:4px;">
            <span style="font-size:22px;">{icono}</span>
            <span style="font-size:22px;font-weight:600;color:#F0F0F0;">{titulo}</span>
            <span style="background:rgba({rgb},0.1);border:1px solid rgba({rgb},0.3);
                         color:{color};font-size:10px;letter-spacing:2px;
                         padding:3px 9px;border-radius:2px;">{label_badge}</span>
        </div>
        <p style="font-size:12px;color:#555;margin:0;">
            Registrando como: <strong style="color:#888;">{st.session_state.nombre_completo}</strong></p>
        """, unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("📝 Información del Caso")
    ot_te = st.text_input("OT-TE *", placeholder="Ejemplo: OT-2024-001")
    col1, col2 = st.columns(2)
    with col1:
        edad         = st.number_input("Edad *", min_value=0, max_value=120, value=None)
        sexo         = st.selectbox("Sexo *", ["Seleccione...", "Hombre", "Mujer", "Otro", "No Reporta"])
        departamento = st.text_input("Departamento *", placeholder="Ejemplo: Antioquia")
    with col2:
        municipio    = st.text_input("Municipio *", placeholder="Ejemplo: Medellín")
        solicitante  = st.selectbox("Entidad Solicitante *", ["Seleccione...", "ARN", "SESP", "OTRO"])
        nivel_riesgo = st.selectbox("Nivel de Riesgo *", ["Seleccione...", "EXTRAORDINARIO", "EXTREMO", "ORDINARIO"])
    observaciones = st.text_area("Observaciones (Opcional)", height=80)

    # ── Hechos de Riesgo ──────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("⚠️ Hechos de Riesgo")
    st.caption("Opcional. Agrega uno o varios hechos de riesgo asociados a este caso.")

    for i, hecho in enumerate(st.session_state.hechos):
        with st.container(border=True):
            col_tit, col_del = st.columns([5, 1])
            with col_tit: st.markdown(f"**Hecho #{i+1} — {hecho['tipo']}**")
            with col_del:
                if st.button("🗑️", key=f"del_{tipo}_{i}"):
                    st.session_state.hechos.pop(i); st.rerun()
            c1, c2 = st.columns(2)
            with c1:
                st.write(f"📅 **Fecha:** {hecho['fecha']}")
                st.write(f"📍 **Lugar:** {hecho['lugar']}")
            with c2:
                st.write(f"👤 **Autor:** {hecho['autor']}")
            st.write(f"📄 **Descripción:** {hecho['descripcion']}")

    with st.expander("➕ Agregar hecho de riesgo", expanded=len(st.session_state.hechos) == 0):
        with st.form(f"form_hecho_{tipo}", clear_on_submit=True):
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
                descripcion_hecho = st.text_area("Descripción *",
                                                 placeholder="Describe brevemente el hecho...", height=122)
            if st.form_submit_button("➕ Agregar este hecho", use_container_width=True):
                err_h = []
                if tipo_hecho == "Seleccione...": err_h.append("Selecciona el tipo de hecho")
                if not lugar_hecho.strip():        err_h.append("El lugar es obligatorio")
                if not autor_hecho.strip():        err_h.append("El autor es obligatorio")
                if not descripcion_hecho.strip():  err_h.append("La descripción es obligatoria")
                if err_h:
                    for e in err_h: st.error(f"• {e}")
                else:
                    st.session_state.hechos.append({
                        "tipo": tipo_hecho, "fecha": str(fecha_hecho),
                        "lugar": lugar_hecho.strip(), "autor": autor_hecho.strip(),
                        "descripcion": descripcion_hecho.strip()
                    })
                    st.success("✅ Hecho agregado"); st.rerun()

    # ── Perfil Antiguo ────────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("Perfil Antiguo")
    st.caption("Opcional. Agrega uno o varios perfiles FARC-EP asociados a este caso.")

    if "perfiles" not in st.session_state:
        st.session_state.perfiles = []

    # Mostrar perfiles ya agregados
    for i, perfil in enumerate(st.session_state.perfiles):
        with st.container(border=True):
            col_tit, col_del = st.columns([5, 1])
            with col_tit: st.markdown(f"**Perfil #{i+1} — {perfil.get('modo_participacion', '')}**")
            with col_del:
                if st.button("🗑️", key=f"del_perfil_{tipo}_{i}"):
                    st.session_state.perfiles.pop(i); st.rerun()
            c1, c2 = st.columns(2)
            with c1:
                st.write(f"📋 **Modo de Participación:** {perfil.get('modo_participacion','')}")
                st.write(f"📅 **Año Ingreso/Traslado/Captura:** {perfil.get('anio_ingreso','')}")
                st.write(f"🗺️ **Bloque:** {perfil.get('bloque','')}")
                st.write(f"🏗️ **Estructura:** {perfil.get('estructura','')}")
                st.write(f"📍 **Lugar de Acreditación:** {perfil.get('lugar_acreditacion','')}")
            with c2:
                st.write(f"🎭 **Rol/Actividades:** {perfil.get('rol','')}")
                if perfil.get('otro_rol'): st.write(f"❓ **Otro Rol:** {perfil.get('otro_rol','')}")
                if perfil.get('subpoblacion'): st.write(f"👥 **Subpoblación (Índice 1):** {perfil.get('subpoblacion','')}")
                if perfil.get('meses_privado'): st.write(f"⛓️ **Meses Privado de Libertad:** {perfil.get('meses_privado','')}")
                if perfil.get('tipo_institucion'): st.write(f"🏛️ **Tipo Institución:** {perfil.get('tipo_institucion','')}")
                if perfil.get('pabellon_alta_seguridad'): st.write(f"🔒 **Pabellón Alta Seguridad:** {perfil.get('pabellon_alta_seguridad','')}")

    # Mapeo bloque → opciones de estructura
    _ESTRUCTURAS = {
        "Bloque Caribe o Martín Caballero": [
            "Seleccione...", "Frente Urbano José Antequera", "Frente 59 Resistencia Guajira",
            "Frente 41 Cacique Upar", "Frente 37 Martín Caballero", "Frente 35 Benkos Biohó",
            "Frente 19 José Prudencio Padilla", "Compañía Móvil Efraín Guzmán"],
        "Bloque Central o Comando Conjunto Central Adán Izquierdo": [
            "Seleccione...", "Frente 50 Cacique Calarcá", "Frente 21 Cacica La Gaitana",
            "Escuela Hernán Murillo Toro", "Emisora Manuel Cepeda Vargas", "Compañía Tulio Varón",
            "Compañía Móvil Miler Salcedo", "Compañía Móvil Jacobo Prías Alape",
            "Compañía Móvil Héroes de Marquetalia", "Compañía Móvil Daniel Aldana",
            "Comisión Política René González", "Comisión de Finanzas Manuelita Sáenz",
            "Columna Alfredo González"],
        "Bloque Magdalena Medio": [
            "Seleccione...", "Unidad Iván Ríos", "Frente 46", "Frente 4 José Antonio Galán",
            "Frente 33 Mariscal Sucre", "Frente 23 Policarpa Salavarrieta",
            "Frente 20 Los Comuneros", "Frente 12 José Antonio Galán",
            "Compañía Móvil Salvador Díaz", "Compañía Móvil Resistencia Bari",
            "Compañía Móvil Gerardo Guevara", "Compañía Móvil Catatumbo",
            "Compañía Móvil 29 de Mayo", "Columna Móvil Gildardo Rodríguez",
            "Columna Móvil Arturo Ruiz Bari", "Frente 24 Héroes y Mártires de Santa Rosa",
            "Columna Móvil Raúl Eduardo Mahecha"],
        "Bloque Móvil Arturo Ruiz": [
            "Seleccione...", "Columna Móvil Miller Perdomo", "Columna Móvil Libardo García",
            "Columna Móvil Ismael Romero", "Columna Móvil Gabriel Galvis",
            "Columna Móvil Alirio Torres"],
        "Bloque Noroccidental José María Córdova o Iván Ríos": [
            "Seleccione...", "Frente Urbano Jacobo Arenas",
            "Frente o Columna Móvil Aurelio Rodríguez", "Frente 9 Atanasio Girardot",
            "Frente 58 Mártires de Las Cañas", "Frente 57 Efraín Ballesteros",
            "Frente 5 Antonio Nariño", "Frente 47 Rodrigo Gaitán o Leonardo Posada Pedraza",
            "Frente 36 Jair Aldana Baquero", "Frente 34 Alberto Martínez",
            "Frente 18 Cacique Coyara", "Compañía Héroes y Mártires del Cairo",
            "Columna Móvil Mario Vélez"],
        "Bloque Occidental Comandante Alfonso Cano": [
            "Seleccione...", "Frente Urbano Manuel Cepeda Vargas", "Frente 8 José Gonzalo Franco",
            "Frente 60 Jaime Pardo Leal", "Frente 6 Hernando González Acosta",
            "Frente 30 José Antonio Páez", "Frente 29 Alfonso Arteaga",
            "Compañía Víctor Saavedra", "Compañía Simón Rodríguez",
            "Compañía Móvil Mariscal Sucre", "Compañía Ambrosio González",
            "Compañía Alonso Cortés", "Columna Móvil Jacobo Arenas",
            "Columna Móvil Daniel Aldana"],
        "Bloque Oriental Comandante Jorge Briceño": [
            "Seleccione...", "Frente 16 José Antonio Páez", "Frente 11 José Antonio Anzoátegui",
            "Compañía Móvil Rigoberto Lozada", "Frente Vladimir Steven", "Frente Urias Rondón",
            "Frente Urbano Antonio Nariño (RUAN)", "Frente Reinaldo Cuellar",
            "Frente Felipe Rincón", "Frente Esteban Martínez", "Frente Acacio Medina",
            "Frente Abelardo Romero", "Frente 42 Manuel Cepeda Vargas",
            "Frente 40 Jacobo Arenas", "Frente 39 Ricaurte Jiménez",
            "Frente 38 Ciro Trujillo Castaño", "Compañía Móvil Yerminson Ruíz",
            "Compañía Móvil Xiomara Marín", "Compañía Móvil Urias Rondón",
            "Compañía Móvil Quino Méndez", "Compañía Móvil Octavio Suárez Briceño",
            "Compañía Móvil Martín Martínez","Compañía Móvil Marguetalia", "Compañía Móvil Marco Aurelio Buendía",
            "Compañía Móvil Judith Rondón", "Compañía Móvil Fuerzas Especiales",
            "Compañía Móvil Edwin Suárez", "Compañía Móvil Darío Bonilla",
            "Compañía Móvil Central", "Columna Móvil Urias Rondón",
            "Columna Móvil Reinel Mendez","Columna Móvil Luis Pardo","Columna Móvil Alfonso Castellanos",
            "Frente 62. Héroes del Yari", "Frente 56. Combatientes de Cusiana", "Frente 55. Teófilo Forero", 
            "Frente 54. Miguel Ángel Bonilla", "Frente 53. José Antonio Anzoátegui", "Frente 52. Juan de la Cruz Varela",
            "Frente 51. Jaime Pardo Leal", "Frente 45. Atanasio Girardot", "Frente 44. Antonio Ricaurte",
            "Frente 43. Joselo Lozada", "Columna Móvil Reinel Mendez", "Frente Vaupés",
            "Frente Policarpa Salavarrieta", "Frente Manuela Beltrán", "Frente Camilo Torres",
            "Frente 7.Jacobo Prías Alape", "Frente 31. Pedro Nel Jiménez Obando", "Frente 28. José María Carbonell",
            "Frente 27. Isaías Pardo", "Frente 26. Hermógenes Maza", "Frente 25. Armando Rios",
            "Frente 22. Simón Bolívar", "Frente 10. Guadalupe Salcedo", "Frente 1. Armando Ríos",
            "Compañía Móvil Julián Ramírez", "Compañía Móvil Juan Jose Rondon", "Compañía Móvil Héctor Ramírez",
            "Compañía Móvil Alfonso Castellanos"     
        ],
        "Bloque Sur": [
            "Seleccione...", "Unidad José Antonio Galán", "Guardia de Bloque Joaquín Gómez",
            "Guardia de Bloque Fabián Ramírez", "Frente 66 Joselo Losada", "Frente 64",
            "Frente 63 Rodolfo Tanas", "Frente 61 Cacique Timanco",
            "Frente 49 Héctor Ramírez", "Frente 48 Pedro Martínez o Antonio José de Sucre",
            "Frente 32 Ernesto Che Guevara", "Frente 3 José Antequera",
            "Frente 2 Antonio José de Sucre", "Frente 17 Angelino Godoy",
            "Frente 15 José Ignacio Mora", "Frente 14 José Antonio Galán",
            "Frente 13 Cacica Gaitana", "Compañía Móvil Mixta", "Comisión Taller",
            "Columna Móvil Yesid Ortiz", "Columna Móvil Teófilo Forero"],
        "No aplica": [
            "Seleccione...", "Secretariado Nacional", "Estado Mayor Central",
            "Comisión Internacional"],
    }

    with st.expander("➕ Agregar Perfil Antiguo", expanded=len(st.session_state.perfiles) == 0):

        # ── Campos 1, 2, 3: siempre visibles ─────────────────────────────────
        p_modo = st.selectbox("MODO DE PARTICIPACIÓN EN LAS FARC-EP *",
            ["Seleccione...", "Combatiente", "Miliciano/a", "Colaborador/a",
             "Privado de la libertad", "Otro"],
            key=f"p_modo_{tipo}")

        p_anio = st.number_input(
            "AÑO DE INGRESO, TRASLADO O CAPTURA *",
            min_value=1950,
            max_value=2026,
            step=1,
            key=f"p_anio_{tipo}"
            )

        p_bloque = st.selectbox("SELECCIONE EL BLOQUE DE OPERACIÓN *",
            ["Seleccione..."] + list(_ESTRUCTURAS.keys()),
            key=f"p_bloque_{tipo}")

        # ── Campo 4: estructura condicional según bloque ───────────────────────
        p_estructura = "Seleccione..."
        if p_bloque != "Seleccione...":
            opciones_estructura = _ESTRUCTURAS[p_bloque]
            p_estructura = st.selectbox("ESTRUCTURA *", opciones_estructura,
                key=f"p_estructura_{tipo}")

        # ── Campos 5 y 6: siempre visibles tras bloque ────────────────────────
        p_lugar_acreditacion = st.selectbox("LUGAR DE ACREDITACIÓN *",
            ["Seleccione...", "PONDORES, FONSECA",
            "SAN JOSÉ DE ORIENTE, LA PAZ",
            "CAÑO INDIO, TIBÚ",
            "FILIPINAS, ARAUQUITA",
            "LAS BRISAS DE TAMARINDO, VIDRÍ",
            "AGUA BONITA, LA MONTAÑITA",
            "MONTERREDONDO, MIRANDA",
            "LLANOGRANDE, DABEIBA",
            "LA FILA, ICONONZO",
            "EL ESTRECHO, PATÍA",
            "LAS COLINAS, SAN JOSÉ DEL GUAVIARE",
            "LA GUAJIRA, MESETAS",
            "LA PLANCHA, ANORÍ",
            "EL OSO, PLANADAS",
            "LA REFORMA, VISTAHERMOSA",
            "MIRAVALLE, SAN VICENTE DEL CAGUÁN",
            "LA VARIANTE, TUMACO",
            "LOS MONOS, CALDONO",
            "EL CERAL, BUENOS AIRES",
            "CARACOLÍ, CARMEN DEL DARIÉN",
            "CARRIZAL, REMEDIOS",
            "CHARRAS, SAN JOSÉ DEL GUAVIARE",
            "PLAYA RICA, LA MACARENA",
            "SANTA LUCIA, ITUANGO",
             "LA PRADERA, PUERTO ASÍS",
             "LA PALOMA, POLICARPA",
             "VAGAEZ, VIGÍA DEL FUERTE",
             "LAS BRISAS, RIOSUCIO",
             "GALLO, TIERRALTA",
             "INSTITUCIÓN PENITENCIARIA",
             "ACREDITADO POR LA JEP",
             "PLANADAS, TOLIMA",
             "OTRO",
             "NO REPORTA",            
            ],
            key=f"p_lugar_{tipo}")

        _ROLES = ["Seleccione...", "Base", "Radista", "Caletero/a",
                  "Enfermero/a", "Finanzas", "Organización de masas", "Comunicación propaganda",
                  "Inteligencia", "Logística", "Instrucción/Educación", "Correo Humano",
                  "Ayudante", "Explosivista", "Fuerzas especiales", "Francotirador", "Ametralladora"
                 "Artillería", "Comandante", "Reemplazante", "Mecanismo monitoreo y verificación"
                  "Delegación de paz La Habana", "Relaciones internacionales", "Otro"]
        p_rol = st.selectbox("ROL/ACTIVIDADES P_ANTIGUO *", _ROLES, key=f"p_rol_{tipo}")

        # ── Campo 7: texto libre si el rol requiere especificación ─────────────
        p_otro_rol = ""
        if p_rol == "Otro":
            p_otro_rol = st.text_input("¿QUÉ OTRO ROL?", key=f"p_otro_rol_{tipo}")

        # ── Campo 8: subpoblación Índice 1 ────────────────────────────────────
        p_otro_rol_libre = st.text_input(
            "¿QUÉ OTRO ROL?",
            key=f"p_otro_rol_libre_{tipo}"
        )

        # ── Campos 9 y 10: privación de libertad (condicional) ────────────────
        mostrar_libertad = (p_modo == "Privado de la libertad")

        p_meses_privado    = ""
        p_tipo_institucion = "Seleccione..."
        if mostrar_libertad:
            p_meses_privado = st.number_input("NO. MESES PRIVADO DE LA LIBERTAD",
                min_value=0, max_value=600, step=1, key=f"p_meses_{tipo}")
            _INSTITUCIONES = ["Seleccione...", 
                              "EPC - ESTABLECIMIENTO PENITENCIARIO Y CARCELARÍO",
                              "RM - RECLUSIÓN DE MUJERES",
                              "EPMS - ESTABLECIMIENTO PENITENCIARIO DE MEDIANA SEGURIDAD",
                              "CPMS - CÁRCEL Y PENITENCIARIA DE MEDIANA SEGURIDAD",
                              "CMS - CÁRCEL DE MEDIANA SEGURIDAD",
                              "EPAMS - ESTABLECIMIENTO PENITENCIARIO DE MEDIANA Y ALTA SEGURIDAD",
                              "CPAMS - CÁRCEL Y PENITENCIARIA DE ALTA Y MEDIANA SEGURIDAD",
                              "ERE - ESTABLECIMIENTO DE RECLUSIÓN ESPECIAL",
                              "CO -COMPLEJO CARCELARÍO",
                              "PRISIÓN DOMICILIARIA"]
            p_tipo_institucion = st.selectbox("TIPO DE INSTITUCIÓN PENITENCIARIA",
                _INSTITUCIONES, key=f"p_inst_{tipo}")

        # ── Campo 11: pabellón alta seguridad (solo si CO) ────────────────────
        p_pabellon = ""
        if mostrar_libertad and p_tipo_institucion == "CO -COMPLEJO CARCELARÍO":
            p_pabellon = st.selectbox("PABELLÓN DE ALTA SEGURIDAD",
                ["Seleccione...", "Sí", "No"], key=f"p_pabellon_{tipo}")

        # ── Botón agregar ─────────────────────────────────────────────────────
        st.markdown("")
        if st.button("➕ Agregar este perfil", use_container_width=True,
                     key=f"btn_add_perfil_{tipo}", type="secondary"):
            err_p = []
            if p_modo        == "Seleccione...": err_p.append("El modo de participación es obligatorio")
            if not p_anio:
                err_p.append("El año de ingreso es obligatorio")
            if p_bloque      == "Seleccione...": err_p.append("El bloque de operación es obligatorio")
            if p_estructura  == "Seleccione...": err_p.append("La estructura es obligatoria")
            if p_lugar_acreditacion == "Seleccione...": err_p.append("El lugar de acreditación es obligatorio")
            if p_rol         == "Seleccione...": err_p.append("El rol es obligatorio")
            if p_rol == "Otro" and not p_otro_rol.strip(): err_p.append("Especifica el otro rol")
            if err_p:
                for e in err_p: st.error(f"• {e}")
            else:
                st.session_state.perfiles.append({
                    "modo_participacion":  p_modo,
                    "anio_ingreso":        p_anio,
                    "bloque":              p_bloque,
                    "estructura":          p_estructura,
                    "lugar_acreditacion":  p_lugar_acreditacion,
                    "rol":                 p_rol,
                    "otro_rol":            p_otro_rol.strip() if p_otro_rol else "",
                    "subpoblacion": p_otro_rol_libre.strip(),
                    "meses_privado":       str(p_meses_privado) if mostrar_libertad else "",
                    "tipo_institucion":    p_tipo_institucion if p_tipo_institucion != "Seleccione..." else "",
                    "pabellon_alta_seguridad": p_pabellon if p_pabellon != "Seleccione..." else "",
                })
                st.success("✅ Perfil Antiguo agregado"); st.rerun()
    st.markdown("---")
    if st.button(f"✅ REGISTRAR CASO {label_badge}", use_container_width=True, type="primary"):
        errores = []
        if not ot_te or ot_te.strip() == "":            errores.append("El campo OT-TE es obligatorio")
        if edad is None or edad == 0:                   errores.append("La edad es obligatoria")
        if sexo == "Seleccione...":                     errores.append("Debe seleccionar un sexo")
        if not departamento or departamento.strip() == "": errores.append("El departamento es obligatorio")
        if not municipio or municipio.strip() == "":    errores.append("El municipio es obligatorio")
        if solicitante == "Seleccione...":              errores.append("Debe seleccionar una entidad solicitante")
        if nivel_riesgo == "Seleccione...":             errores.append("Debe seleccionar un nivel de riesgo")

        if errores:
            st.error("❌ Por favor corrija los siguientes errores:")
            for e in errores: st.write(f"   • {e}")
        else:
            try:
                todas_filas   = hoja_casos.get_all_values()
                ot_existentes = [fila[2] for fila in todas_filas[1:]]
                if ot_te.strip() in ot_existentes:
                    st.error(f"❌ El caso '{ot_te}' ya existe en esta hoja")
                else:
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    id_caso   = obtener_siguiente_id(hoja_casos)
                    hoja_casos.append_row([
                        id_caso, timestamp, ot_te.strip(), edad, sexo,
                        departamento.strip(), municipio.strip(), solicitante, nivel_riesgo,
                        observaciones.strip() if observaciones else "",
                        st.session_state.nombre_completo, st.session_state.username
                    ])
                    hechos_guardados = 0
                    for hecho in st.session_state.hechos:
                        id_hecho = obtener_siguiente_id(hoja_hechos)
                        hoja_hechos.append_row([
                            id_hecho, id_caso, ot_te.strip(),
                            hecho["tipo"], hecho["fecha"], hecho["lugar"],
                            hecho["autor"], hecho["descripcion"],
                            st.session_state.nombre_completo, st.session_state.username
                        ])
                        hechos_guardados += 1
                    perfiles_guardados = 0
                    for perfil in st.session_state.perfiles:
                        id_perfil = obtener_siguiente_id(hoja_perfiles)
                        hoja_perfiles.append_row([
                            id_perfil, id_caso, ot_te.strip(),
                            perfil.get("modo_participacion", ""),
                            perfil.get("anio_ingreso", ""),
                            perfil.get("bloque", ""),
                            perfil.get("estructura", ""),
                            perfil.get("lugar_acreditacion", ""),
                            perfil.get("rol", ""),
                            perfil.get("otro_rol", ""),
                            perfil.get("subpoblacion", ""),
                            perfil.get("meses_privado", ""),
                            perfil.get("tipo_institucion", ""),
                            perfil.get("pabellon_alta_seguridad", ""),
                            st.session_state.nombre_completo, st.session_state.username
                        ])
                        perfiles_guardados += 1
                    st.session_state.hechos = []
                    st.session_state.perfiles = []
                    st.success(f"✅ Caso **{ot_te}** registrado en {label_badge}!")
                    if hechos_guardados   > 0: st.info(f"⚠️ {hechos_guardados} hecho(s) de riesgo registrados")
                    if perfiles_guardados > 0: st.info(f"🧑‍🤝‍🧑 {perfiles_guardados} perfil(es) registrados")
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
                st.error(f"❌ Error al guardar: {str(e)}")

    st.markdown("---")
    st.caption(f"🔒 Los datos se guardan en la hoja '{nombre_hoja_casos}' de Google Sheets")


def panel_visualizacion():
    import io
    st.title("📊 Casos Registrados"); st.markdown("---")
    tab_ind, tab_col = st.tabs(["👤 Individual", "👥 Colectivo"])
    for tab, tipo in [(tab_ind, "individual"), (tab_col, "colectivo")]:
        with tab:
            hoja_casos, hoja_hechos, hoja_perfiles, sheet_url = conectar_sheet_casos(tipo)
            if hoja_casos is None: st.error(f"No se pudo conectar a la hoja {tipo}"); continue

            sub1, sub2, sub3 = st.tabs(["📋 Casos", "⚠️ Hechos de Riesgo", "🧑‍🤝‍🧑 Perfil Antiguo"])

            # ── Cargar datos una sola vez por tab ─────────────────────────────
            try: datos   = hoja_casos.get_all_records()
            except: datos = []
            try: datos_h = hoja_hechos.get_all_records()
            except: datos_h = []
            try: datos_p = hoja_perfiles.get_all_records()
            except: datos_p = []

            df   = pd.DataFrame(datos)   if datos   else pd.DataFrame()
            df_h = pd.DataFrame(datos_h) if datos_h else pd.DataFrame()
            df_p = pd.DataFrame(datos_p) if datos_p else pd.DataFrame()

            with sub1:
                if not df.empty:
                    c1,c2,c3,c4 = st.columns(4)
                    c1.metric("Total Casos",   len(df))
                    c2.metric("Departamentos", df["Departamento"].nunique() if "Departamento" in df.columns else 0)
                    c3.metric("Municipios",    df["Municipio"].nunique()    if "Municipio"    in df.columns else 0)
                    c4.metric("Riesgo Alto",   df["Nivel de Riesgo"].isin(["EXTREMO","EXTRAORDINARIO"]).sum() if "Nivel de Riesgo" in df.columns else 0)
                    col1,col2,col3 = st.columns(3)
                    with col1: depto      = st.selectbox("Departamento",    ["Todos"]+sorted(df["Departamento"].unique().tolist())   if "Departamento"  in df.columns else ["Todos"], key=f"depto_{tipo}")
                    with col2: riesgo     = st.selectbox("Nivel de Riesgo", ["Todos"]+sorted(df["Nivel de Riesgo"].unique().tolist()) if "Nivel de Riesgo" in df.columns else ["Todos"], key=f"riesgo_{tipo}")
                    with col3: analista_f = st.selectbox("Analista",        ["Todos"]+sorted(df["Analista"].unique().tolist())       if "Analista"      in df.columns else ["Todos"], key=f"analista_{tipo}")
                    df_f = df.copy()
                    if depto      != "Todos" and "Departamento"    in df.columns: df_f = df_f[df_f["Departamento"]    == depto]
                    if riesgo     != "Todos" and "Nivel de Riesgo" in df.columns: df_f = df_f[df_f["Nivel de Riesgo"] == riesgo]
                    if analista_f != "Todos" and "Analista"        in df.columns: df_f = df_f[df_f["Analista"]        == analista_f]
                    st.subheader(f"📋 Resultados ({len(df_f)} casos)")
                    st.dataframe(df_f, use_container_width=True, hide_index=True)
                else: st.info(f"📭 No hay casos {tipo}s registrados")

            with sub2:
                if not df_h.empty:
                    c1,c2,c3 = st.columns(3)
                    c1.metric("Total Hechos",    len(df_h))
                    c2.metric("Tipos distintos",  df_h["Tipo de Hecho"].nunique() if "Tipo de Hecho" in df_h.columns else 0)
                    c3.metric("Casos con hechos", df_h["ID_Caso"].nunique()       if "ID_Caso"       in df_h.columns else 0)
                    tipo_f = st.selectbox("Filtrar por Tipo", ["Todos"]+sorted(df_h["Tipo de Hecho"].unique().tolist()) if "Tipo de Hecho" in df_h.columns else ["Todos"], key=f"tipo_hecho_{tipo}")
                    df_hf = df_h[df_h["Tipo de Hecho"] == tipo_f].copy() if tipo_f != "Todos" else df_h.copy()
                    st.dataframe(df_hf, use_container_width=True, hide_index=True)
                else: st.info("📭 No hay hechos de riesgo registrados")

            with sub3:
                if not df_p.empty:
                    c1,c2,c3 = st.columns(3)
                    c1.metric("Total Perfiles",    len(df_p))
                    c2.metric("Casos con perfiles", df_p["ID_Caso"].nunique() if "ID_Caso" in df_p.columns else 0)
                    st.dataframe(df_p, use_container_width=True, hide_index=True)
                else: st.info("📭 No hay perfiles registrados")

            # ── Botón descarga XLSX unificado (fuera de los subtabs) ──────────
            st.markdown("---")
            if not df.empty or not df_h.empty or not df_p.empty:
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                    (df_f   if not df.empty   else df).to_excel(writer, sheet_name="Casos",           index=False)
                    (df_hf  if not df_h.empty else df_h).to_excel(writer, sheet_name="Hechos de Riesgo", index=False)
                    df_p.to_excel(writer, sheet_name="Perfiles",         index=False)
                buffer.seek(0)
                nombre_archivo = f"ISMR_{tipo}_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
                st.download_button(
                    label="📥 Descargar reporte completo (.xlsx)",
                    data=buffer,
                    file_name=nombre_archivo,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key=f"dl_xlsx_{tipo}",
                    use_container_width=True,
                    type="primary"
                )


def panel_gestion_usuarios():
    st.title("👥 Gestión de Usuarios"); st.markdown("---")
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
                    else: st.error("❌ El usuario ya existe o hubo un problema al crearlo")
                else: st.warning("⚠️ Completa todos los campos")
    with tab2:
        st.subheader("📋 Lista de Usuarios")
        usuarios = listar_usuarios()
        if usuarios:
            df = pd.DataFrame(usuarios)
            c1,c2,c3 = st.columns(3)
            c1.metric("Total", len(df))
            admins = df[df["es_admin"].astype(str).str.upper() == "TRUE"].shape[0] if "es_admin" in df.columns else 0
            c2.metric("Admins", admins); c3.metric("Analistas", len(df)-admins)
            st.dataframe(df[["username","nombre_completo","es_admin","debe_cambiar_password"]], use_container_width=True)
        else: st.info("📭 No hay usuarios")
    with tab3:
        st.subheader("🔑 Hashes de Contraseñas")
        st.warning("⚠️ Información sensible — solo visible para administradores")
        if st.checkbox("Mostrar hashes"):
            for u in listar_usuarios():
                with st.expander(f"👤 {u.get('nombre_completo','?')} (@{u.get('username','?')})"):
                    st.code(u.get('password_hash','N/A'), language=None)
                    st.caption(f"Debe cambiar: {u.get('debe_cambiar_password','N/A')}")
