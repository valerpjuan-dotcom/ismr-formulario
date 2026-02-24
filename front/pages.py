import streamlit as st
import hashlib
import time
import calendar
import pandas as pd
from datetime import datetime, date
from zoneinfo import ZoneInfo

_BOGOTA = ZoneInfo("America/Bogota")
from data.diccionarios import (
    _ESTRUCTURAS, _ROLES, _LUGAR_ACREDITACION, _INSTITUCIONES, _PARTICIPACION,
    _MUNICIPIOS, _TIPOS_POBLACION, _SUBPOBLACIONES, _GENEROS, _ORIENTACIONES_SEXUALES,
    _JEFATURA_HOGAR, _SI_NO_REPORTA, _SI_NO, _DISCAPACIDAD, _ETNIA, _CUIDADOR,
    _VICTIMA_CONFLICTO_ARMADO, _LIDER_SOCIAL_DDHH,
    # Perfil Actual
    _PA_NIVEL_EDUCATIVO, _PA_FUENTE_INGRESOS, _PA_ESTADO_PROYECTO_ARN, _PA_ACTIVIDAD_ECONOMICA,
    _PA_MACROCASOS_JEP, _PA_INSTANCIAS_PARTIDO, _PA_ROLES_PARTIDO,
    _PA_CONSEJERIA_NACIONAL, _PA_TIPO_ORG, _PA_AMBITO_ORG, _PA_ESCALA_ORG,
    _PA_CARGO_ELECCION,
    # Hechos de Riesgo
    _TIPOS_HECHO, _TIPOS_ACTOR_GENERADOR, _MEDIOS_HECHO, _VICTIMAS_SITUACION_HECHO, _TIPOS_AMENAZA,
    # Desplazamientos
    _DESP_MOTIVOS, _DESP_MEDIOS_TRANSPORTE, _DESP_FRECUENCIAS,
    _DESP_TIPOS_VIA, _DESP_DEPARTAMENTOS,
    # Verificaciones
    _FUENTES_VERIFICACION, _VER_OPCIONES,
    # Impacto Consecuencial
    _IMPACTO_SI_NR,
)

from configuration.settings import TAB_NOMBRES
from data.mongo.usuarios_repo import actualizar_password, crear_usuario, listar_usuarios, usuario_existe, hashear_password
from data.mongo.casos_repo import conectar_sheet_casos, guardar_borrador, cargar_borrador, eliminar_borrador
from service.auth_service import verificar_credenciales, logout, obtener_siguiente_id
from front.styles import inyectar_css_selector


def login_page():
    st.title("🔐 Acceso al Sistema ISMR")
    st.markdown("---")
    st.info("👋 Identifícate para acceder al sistema")
    with st.form("login_form"):
        username = st.text_input("Usuario", placeholder="nombre.apellido")
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

    # ── Link de recuperación ──────────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    _, col_rec = st.columns([3, 2])
    with col_rec:
        if st.button("¿Olvidaste tu contraseña?", type="secondary", use_container_width=True):
            st.session_state.vista_recovery = "solicitar"
            st.rerun()

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
                nuevo_hash = hashear_password(nueva)
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
            st.session_state.vista = "individual"
            st.session_state.hechos = []
            st.session_state.perfiles = []
            st.session_state.antecedentes = []
            st.session_state["borrador_cargado_individual"] = False
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('<p style="text-align:center;font-size:11px;color:#444;margin-top:10px;">Un caso por registro</p>', unsafe_allow_html=True)

    with col2:
        st.markdown('<div style="text-align:center;margin-bottom:12px;"><span style="font-size:32px;">👥</span></div>', unsafe_allow_html=True)
        st.markdown('<div class="btn-colectivo">', unsafe_allow_html=True)
        if st.button("FORMULARIO\nCOLECTIVO", key="btn_colectivo", use_container_width=True):
            st.session_state.vista = "colectivo"
            st.session_state.hechos = []
            st.session_state.perfiles = []
            st.session_state.antecedentes = []
            st.session_state["borrador_cargado_colectivo"] = False
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('<p style="text-align:center;font-size:11px;color:#444;margin-top:10px;">Múltiples personas afectadas</p>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    _, col_logout, _ = st.columns([2, 1, 2])
    with col_logout:
        if st.button("🚪 Cerrar sesión", use_container_width=True, type="secondary"): logout()


def _render_pa_form(pa, tipo, idx, es_reincorporado, es_familiar_reincorporado,
                    es_familiar_comunes, mostrar_cargo_comunes):
    """
    Renderiza los campos de Perfil Actual según tipo de población.

    Lógica de visibilidad:
    - REINCORPORADO/A            → es_reincorporado=True
    - FAMILIAR DE REINCORPORADO/A → es_familiar_reincorporado=True
    - INTEGRANTE DEL PARTIDO     → mostrar_cargo_comunes=True
    - FAMILIAR DE INTEGRANTE     → es_familiar_comunes=True, mostrar_cargo_comunes=True

    Sección de perfil completa (educación, ARN, JEP, TOAR, organizaciones):
      visible si es_reincorporado OR es_familiar_reincorporado OR es_familiar_comunes
    ARN y Actividad Económica:
      visible solo si es_reincorporado OR es_familiar_reincorporado
    Concejo Comunes:
      visible si mostrar_cargo_comunes OR (es_familiar_reincorporado AND familiar_parte_comunes==SI)
    """
    sfx = f"{tipo}_{idx}"

    def _v(campo, defecto="Seleccione..."):
        return pa.get(campo, defecto) if pa else defecto

    _mostrar_perfil = es_reincorporado or es_familiar_reincorporado or es_familiar_comunes
    _mostrar_arn    = es_reincorporado or es_familiar_reincorporado
    _opts_si_no_rep = ["Seleccione...", "SI", "NO REPORTA"]

    # ── FAMILIAR HACE PARTE DEL PARTIDO COMUNES ───────────────────────────────
    # Solo visible cuando es_familiar_reincorporado
    _familiar_parte_comunes = ""
    if es_familiar_reincorporado:
        st.selectbox(
            "FAMILIAR HACE PARTE DEL PARTIDO COMUNES",
            ["Seleccione...", "SI", "NO REPORTA"],
            index=["Seleccione...", "SI", "NO REPORTA"].index(_v("familiar_parte_comunes"))
                  if _v("familiar_parte_comunes") in ["Seleccione...", "SI", "NO REPORTA"] else 0,
            key=f"pa_familiar_parte_{sfx}"
        )
        _familiar_parte_comunes = st.session_state.get(f"pa_familiar_parte_{sfx}", "Seleccione...")

    # ── Sección de perfil (condicionada) ─────────────────────────────────────
    if _mostrar_perfil:
        st.markdown("---")
        st.markdown("**PERFIL DE REINCORPORACIÓN / PARTICIPACIÓN**")

        # Educación e Ingresos
        col1, col2 = st.columns(2)
        with col1:
            _opts_edu = _PA_NIVEL_EDUCATIVO
            st.selectbox("NIVEL DE ESCOLARIDAD", _opts_edu,
                         index=_opts_edu.index(_v("nivel_educativo")) if _v("nivel_educativo") in _opts_edu else 0,
                         key=f"pa_edu_{sfx}")
        with col2:
            st.selectbox("FUENTE PRINCIPAL DE INGRESOS", _PA_FUENTE_INGRESOS,
                         index=_PA_FUENTE_INGRESOS.index(_v("fuente_ingresos")) if _v("fuente_ingresos") in _PA_FUENTE_INGRESOS else 0,
                         key=f"pa_ingresos_{sfx}")

        # ARN y Actividad Económica — solo reincorporados
        if _mostrar_arn:
            col3, col4 = st.columns(2)
            with col3:
                st.selectbox("PROYECTO PRODUCTIVO REINCORPORACIÓN ARN",
                             _PA_ESTADO_PROYECTO_ARN,
                             index=_PA_ESTADO_PROYECTO_ARN.index(_v("estado_proyecto_arn"))
                                   if _v("estado_proyecto_arn") in _PA_ESTADO_PROYECTO_ARN else 0,
                             key=f"pa_arn_{sfx}")
            with col4:
                st.selectbox("ACTIVIDAD ECONÓMICA REINCORPORACIÓN",
                             _PA_ACTIVIDAD_ECONOMICA,
                             index=_PA_ACTIVIDAD_ECONOMICA.index(_v("actividad_economica"))
                                   if _v("actividad_economica") in _PA_ACTIVIDAD_ECONOMICA else 0,
                             key=f"pa_act_eco_{sfx}")

        # JEP — Comparecencia
        st.selectbox("COMPARECENCIA ANTE LA JEP", _opts_si_no_rep,
                     index=_opts_si_no_rep.index(_v("comparecencia_jep"))
                           if _v("comparecencia_jep") in _opts_si_no_rep else 0,
                     key=f"pa_jep_comp_{sfx}")
        if st.session_state.get(f"pa_jep_comp_{sfx}", "Seleccione...") == "SI":
            _mcc_prev = [m.strip() for m in _v("macrocasos_jep", "").split("|") if m.strip()] if pa else []
            st.markdown("**MACROCASO COMPARECIENTE**")
            _cols_mcc = st.columns(2)
            for _j, _mc in enumerate(_PA_MACROCASOS_JEP):
                _cols_mcc[_j % 2].checkbox(_mc, value=(_mc in _mcc_prev), key=f"pa_mcc_{_j}_{sfx}")

        # JEP — Víctima
        st.selectbox("ES VÍCTIMA ANTE LA JEP", _SI_NO_REPORTA,
                     index=_SI_NO_REPORTA.index(_v("victima_jep"))
                           if _v("victima_jep") in _SI_NO_REPORTA else 0,
                     key=f"pa_jep_vic_{sfx}")
        if st.session_state.get(f"pa_jep_vic_{sfx}", "Seleccione...") == "SI":
            _mcv_prev = [m.strip() for m in _v("macrocaso_victima", "").split("|") if m.strip()] if pa else []
            st.markdown("**MACROCASO VÍCTIMA**")
            _cols_mcv = st.columns(2)
            for _j, _mc in enumerate(_PA_MACROCASOS_JEP):
                _cols_mcv[_j % 2].checkbox(_mc, value=(_mc in _mcv_prev), key=f"pa_mcv_{_j}_{sfx}")

        # Compromisos del proceso de paz
        col7, col8 = st.columns(2)
        with col7:
            st.selectbox("PARTICIPA EN TRABAJOS, OBRAS Y ACTIVIDADES REPARADORAS - TOAR",
                         _SI_NO_REPORTA,
                         index=_SI_NO_REPORTA.index(_v("participacion_toar"))
                               if _v("participacion_toar") in _SI_NO_REPORTA else 0,
                         key=f"pa_toar_{sfx}")
            st.selectbox("PARTICIPA EN ACTIVIDADES DEL PROGRAMA PNIS", _SI_NO_REPORTA,
                         index=_SI_NO_REPORTA.index(_v("participacion_pnis"))
                               if _v("participacion_pnis") in _SI_NO_REPORTA else 0,
                         key=f"pa_pnis_{sfx}")
        with col8:
            st.selectbox("PARTICIPA EN ACTIVIDADES DE BÚSQUEDA DE PERSONAS DADAS POR DESAPARECIDAS",
                         _SI_NO_REPORTA,
                         index=_SI_NO_REPORTA.index(_v("busqueda_desaparecidos"))
                               if _v("busqueda_desaparecidos") in _SI_NO_REPORTA else 0,
                         key=f"pa_busq_{sfx}")
            st.selectbox("PARTICIPA EN ACTIVIDADES DE DESMINADO HUMANITARIO", _SI_NO_REPORTA,
                         index=_SI_NO_REPORTA.index(_v("desminado"))
                               if _v("desminado") in _SI_NO_REPORTA else 0,
                         key=f"pa_desminado_{sfx}")

        # Otras organizaciones (multiregistro)
        st.selectbox(
            "¿PARTICIPA DE ALGÚN TIPO DE ORGANIZACIÓN SOCIAL, POLÍTICA O INSTANCIA INSTITUCIONAL DIFERENTE A COMUNES?",
            _SI_NO,
            index=_SI_NO.index(_v("participa_otras_org")) if _v("participa_otras_org") in _SI_NO else 0,
            key=f"pa_otras_org_{sfx}"
        )
        _participa_otras = st.session_state.get(f"pa_otras_org_{sfx}", "Seleccione...")
        if _participa_otras == "SI":
            _oo_key = f"otras_orgs_temp_{sfx}"
            if _oo_key not in st.session_state:
                st.session_state[_oo_key] = list(_v("otras_orgs", []) or [])

            st.markdown("**ORGANIZACIONES / INSTANCIAS REGISTRADAS**")
            for _oo_i, _oo_reg in enumerate(st.session_state[_oo_key]):
                with st.container(border=True):
                    _oo_col_t, _oo_col_d = st.columns([5, 1])
                    with _oo_col_t:
                        st.markdown(
                            f"**Org #{_oo_i+1}:** {_oo_reg.get('nombre_org','—')}  |  "
                            f"**Tipo:** {_oo_reg.get('tipo_org','—')}  |  "
                            f"**Rol:** {_oo_reg.get('rol_org','—')}  |  "
                            f"**Ámbito:** {_oo_reg.get('ambito_org','—')}"
                        )
                    with _oo_col_d:
                        if st.button("🗑️", key=f"del_oo_{sfx}_{_oo_i}", help="Eliminar esta organización"):
                            st.session_state[_oo_key].pop(_oo_i)
                            st.rerun()

            _oo_show_key = f"show_oo_form_{sfx}"
            if _oo_show_key not in st.session_state:
                st.session_state[_oo_show_key] = len(st.session_state[_oo_key]) == 0
            _oo_btn_label = "🔼 Ocultar formulario de organización" if st.session_state[_oo_show_key] else "➕ Agregar organización / instancia"
            if st.button(_oo_btn_label, key=f"toggle_oo_{sfx}", use_container_width=True, type="secondary"):
                st.session_state[_oo_show_key] = not st.session_state[_oo_show_key]
                st.rerun()

            if st.session_state[_oo_show_key]:
                with st.container(border=True):
                    col_ot1_n, col_ot2_n = st.columns(2)
                    with col_ot1_n:
                        st.selectbox("TIPO DE ORGANIZACIÓN", _PA_TIPO_ORG, index=0, key=f"pa_tipo_org_{sfx}_new")
                        st.text_input("NOMBRE ORGANIZACIÓN", value="", key=f"pa_nombre_org_{sfx}_new")
                    with col_ot2_n:
                        st.selectbox("ESCALA", _PA_ESCALA_ORG, index=0, key=f"pa_escala_org_{sfx}_new")
                        st.text_input("¿QUÉ ROL EJERCE EN DICHA INSTANCIA?", value="", key=f"pa_rol_org_{sfx}_new")
                    col_dep_on, col_mun_on = st.columns(2)
                    _dep_org_opts_n = ["Seleccione..."] + list(_MUNICIPIOS.keys())
                    with col_dep_on:
                        st.selectbox("DEPARTAMENTO", _dep_org_opts_n, index=0, key=f"pa_dep_org_{sfx}_new")
                    with col_mun_on:
                        _dep_sel_n  = st.session_state.get(f"pa_dep_org_{sfx}_new", "Seleccione...")
                        _mun_opts_n = _MUNICIPIOS.get(_dep_sel_n, ["Seleccione..."])
                        st.selectbox("MUNICIPIO", _mun_opts_n, index=0, key=f"pa_mun_org_{sfx}_new")
                    col_ai_n, col_af_n = st.columns(2)
                    with col_ai_n:
                        st.number_input("AÑO INICIO ACTIVIDAD", min_value=1990, max_value=2099,
                                        value=None, step=1, key=f"pa_anio_ini_org_{sfx}_new")
                    with col_af_n:
                        st.text_input("AÑO FINALIZACIÓN DE LA ACTIVIDAD (año finalizado, presente o no reporta)",
                                      value="", key=f"pa_anio_fin_org_{sfx}_new")
                    _opts_amb_n = ["Seleccione..."] + _PA_AMBITO_ORG
                    st.selectbox("**ÁMBITO DE LA ORGANIZACIÓN**", _opts_amb_n, index=0, key=f"pa_amb_{sfx}_new")
                    if st.button("✅ Guardar organización", key=f"add_oo_{sfx}", use_container_width=True, type="primary"):
                        _oo_tipo   = st.session_state.get(f"pa_tipo_org_{sfx}_new", "Seleccione...")
                        _oo_nombre = st.session_state.get(f"pa_nombre_org_{sfx}_new", "")
                        _oo_escala = st.session_state.get(f"pa_escala_org_{sfx}_new", "Seleccione...")
                        _oo_rol    = st.session_state.get(f"pa_rol_org_{sfx}_new", "")
                        _oo_dep    = st.session_state.get(f"pa_dep_org_{sfx}_new", "Seleccione...")
                        _oo_mun    = st.session_state.get(f"pa_mun_org_{sfx}_new", "Seleccione...")
                        _oo_ai     = st.session_state.get(f"pa_anio_ini_org_{sfx}_new")
                        _oo_af     = st.session_state.get(f"pa_anio_fin_org_{sfx}_new", "")
                        _oo_amb    = st.session_state.get(f"pa_amb_{sfx}_new", "Seleccione...")
                        st.session_state[_oo_key].append({
                            "tipo_org":         _oo_tipo   if _oo_tipo   != "Seleccione..." else "",
                            "nombre_org":       _oo_nombre,
                            "escala_org":       _oo_escala if _oo_escala != "Seleccione..." else "",
                            "rol_org":          _oo_rol,
                            "departamento_org": _oo_dep    if _oo_dep    != "Seleccione..." else "",
                            "municipio_org":    _oo_mun    if _oo_mun    != "Seleccione..." else "",
                            "anio_inicio_org":  str(int(_oo_ai)) if _oo_ai is not None else "",
                            "anio_fin_org":     str(_oo_af),
                            "ambito_org":       _oo_amb    if _oo_amb    != "Seleccione..." else "",
                        })
                        st.session_state[_oo_show_key] = False
                        st.rerun()

    # ── Partido Comunes ───────────────────────────────────────────────────────
    # Concejo visible si: tipo comunes/familiar_comunes, O si familiar_reincorporado
    # marcó familiar_parte_comunes == SI
    _mostrar_concejo = mostrar_cargo_comunes or (
        es_familiar_reincorporado and _familiar_parte_comunes == "SI"
    )

    if _mostrar_concejo:
        st.markdown("---")
        st.markdown("**PARTIDO COMUNES**")
        st.text_input("¿A QUÉ CONSEJO LOCAL-MUNICIPAL ESTÁ VINCULADO?",
                      value=_v("concejo_comunes", ""), key=f"pa_concejo_{sfx}")

    if mostrar_cargo_comunes:
        # Multiregistro instancias del partido
        _ic_key = f"instancias_comunes_temp_{sfx}"
        if _ic_key not in st.session_state:
            st.session_state[_ic_key] = list(_v("instancias_comunes", []) or [])

        st.markdown("**PARTICIPACIÓN EN INSTANCIAS POLÍTICAS, SOCIALES O INSTITUCIONALES — PARTIDO COMUNES**")
        for _ic_i, _ic_reg in enumerate(st.session_state[_ic_key]):
            with st.container(border=True):
                _ic_col_t, _ic_col_d = st.columns([5, 1])
                with _ic_col_t:
                    st.markdown(
                        f"**Instancia #{_ic_i+1}:** {_ic_reg.get('instancias_partido','—')}  |  "
                        f"**Rol:** {_ic_reg.get('roles_partido','—')}  |  "
                        f"**Consejería:** {_ic_reg.get('consejeria_nacional','—')}"
                    )
                with _ic_col_d:
                    if st.button("🗑️", key=f"del_ic_{sfx}_{_ic_i}", help="Eliminar esta instancia"):
                        st.session_state[_ic_key].pop(_ic_i)
                        st.rerun()

        _ic_show_key = f"show_ic_form_{sfx}"
        if _ic_show_key not in st.session_state:
            st.session_state[_ic_show_key] = len(st.session_state[_ic_key]) == 0
        _ic_btn_label = "🔼 Ocultar formulario de instancia" if st.session_state[_ic_show_key] else "➕ Agregar instancia en Partido Comunes"
        if st.button(_ic_btn_label, key=f"toggle_ic_{sfx}", use_container_width=True, type="secondary"):
            st.session_state[_ic_show_key] = not st.session_state[_ic_show_key]
            st.rerun()

        if st.session_state[_ic_show_key]:
            with st.container(border=True):
                _idx_no_reporta_new = len(_PA_INSTANCIAS_PARTIDO) - 2
                st.markdown("**¿DE CUÁL INSTANCIA DE DIRECCIÓN O VIGILANCIA DEL PARTIDO COMUNES ES INTEGRANTE?**")
                cols_inst_new = st.columns(2)
                for _j, _inst_n in enumerate(_PA_INSTANCIAS_PARTIDO[1:]):
                    cols_inst_new[_j % 2].checkbox(_inst_n, value=False, key=f"pa_inst_{_j}_{sfx}_new")
                _no_reporta_new = st.session_state.get(f"pa_inst_{_idx_no_reporta_new}_{sfx}_new", False)
                if not _no_reporta_new:
                    st.markdown("**ROL QUE EJERCE EN DICHA INSTANCIA**")
                    cols_rp_new = st.columns(2)
                    for _j, _rol_n in enumerate(_PA_ROLES_PARTIDO[1:]):
                        cols_rp_new[_j % 2].checkbox(_rol_n, value=False, key=f"pa_rol_{_j}_{sfx}_new")
                col11_n, col12_n = st.columns(2)
                with col11_n:
                    st.selectbox("ES INTEGRANTE DE CONSEJERÍA NACIONAL", _SI_NO,
                                 index=0, key=f"pa_cons_nac_{sfx}_new")
                _tiene_cons_new = st.session_state.get(f"pa_cons_nac_{sfx}_new", "Seleccione...")
                if _tiene_cons_new == "SI":
                    with col12_n:
                        st.selectbox("¿CUÁL CONSEJERÍA?", _PA_CONSEJERIA_NACIONAL,
                                     index=0, key=f"pa_tipo_cons_{sfx}_new")
                if st.button("✅ Guardar instancia", key=f"add_ic_{sfx}", use_container_width=True, type="primary"):
                    _new_insts = " | ".join([
                        _inst_n for _j, _inst_n in enumerate(_PA_INSTANCIAS_PARTIDO[1:])
                        if st.session_state.get(f"pa_inst_{_j}_{sfx}_new", False)
                    ])
                    _new_roles = " | ".join([
                        _rol_n for _j, _rol_n in enumerate(_PA_ROLES_PARTIDO[1:])
                        if st.session_state.get(f"pa_rol_{_j}_{sfx}_new", False)
                    ])
                    _new_cons_nac  = st.session_state.get(f"pa_cons_nac_{sfx}_new", "Seleccione...")
                    _new_tipo_cons = st.session_state.get(f"pa_tipo_cons_{sfx}_new", "") if _new_cons_nac == "SI" else ""
                    st.session_state[_ic_key].append({
                        "instancias_partido":  _new_insts,
                        "roles_partido":       _new_roles,
                        "consejeria_nacional": _new_cons_nac if _new_cons_nac != "Seleccione..." else "",
                        "tipo_consejeria":     _new_tipo_cons if _new_tipo_cons != "Seleccione..." else "",
                    })
                    st.session_state[_ic_show_key] = False
                    st.rerun()

    # ── Cargo de elección popular (siempre visible) ───────────────────────────
    st.markdown("---")
    st.markdown("**Cargo de Elección Popular**")
    st.selectbox("¿Ocupa o ha ocupado cargo de elección popular?", _PA_CARGO_ELECCION,
                 index=_PA_CARGO_ELECCION.index(_v("cargo_eleccion"))
                       if _v("cargo_eleccion") in _PA_CARGO_ELECCION else 0,
                 key=f"pa_cargo_{sfx}")


def _recoger_pa(tipo, idx, es_reincorporado, es_familiar_reincorporado,
                es_familiar_comunes, mostrar_cargo_comunes):
    """
    Lee el estado de los widgets del Perfil Actual y retorna un dict,
    o None si hay errores de validación.
    """
    sfx = f"{tipo}_{idx}"
    _mostrar_perfil = es_reincorporado or es_familiar_reincorporado or es_familiar_comunes
    _mostrar_arn    = es_reincorporado or es_familiar_reincorporado

    # Familiar parte comunes
    familiar_parte_comunes = ""
    if es_familiar_reincorporado:
        familiar_parte_comunes = st.session_state.get(f"pa_familiar_parte_{sfx}", "Seleccione...")
        if familiar_parte_comunes == "Seleccione...":
            familiar_parte_comunes = ""

    # Validación obligatoria: nivel educativo solo si aplica sección
    nivel_edu = ""
    fuente_ingresos = ""
    estado_arn = ""
    actividad_eco = ""
    if _mostrar_perfil:
        nivel_edu = st.session_state.get(f"pa_edu_{sfx}", "Seleccione...")
        if nivel_edu == "Seleccione...":
            st.error("• El Nivel Educativo es obligatorio")
            return None
        fuente_ingresos = st.session_state.get(f"pa_ingresos_{sfx}", "Seleccione...")
        if fuente_ingresos == "Seleccione...":
            fuente_ingresos = ""
        if _mostrar_arn:
            estado_arn  = st.session_state.get(f"pa_arn_{sfx}", "Seleccione...")
            actividad_eco = st.session_state.get(f"pa_act_eco_{sfx}", "Seleccione...")
            if estado_arn    == "Seleccione...": estado_arn    = ""
            if actividad_eco == "Seleccione...": actividad_eco = ""

    # Macrocasos JEP
    comparecencia_jep = macrocaso_comp = ""
    victima_jep = macrocaso_vic = ""
    participacion_toar = busqueda_desaparecidos = participacion_pnis = desminado = ""
    participa_otras = ""
    otras_orgs = []

    if _mostrar_perfil:
        comparecencia_jep = st.session_state.get(f"pa_jep_comp_{sfx}", "Seleccione...")
        if comparecencia_jep == "SI":
            macrocaso_comp = " | ".join([
                mc for j, mc in enumerate(_PA_MACROCASOS_JEP)
                if st.session_state.get(f"pa_mcc_{j}_{sfx}", False)
            ])
        victima_jep = st.session_state.get(f"pa_jep_vic_{sfx}", "Seleccione...")
        if victima_jep == "SI":
            macrocaso_vic = " | ".join([
                mc for j, mc in enumerate(_PA_MACROCASOS_JEP)
                if st.session_state.get(f"pa_mcv_{j}_{sfx}", False)
            ])
        participacion_toar       = st.session_state.get(f"pa_toar_{sfx}", "Seleccione...")
        busqueda_desaparecidos   = st.session_state.get(f"pa_busq_{sfx}", "Seleccione...")
        participacion_pnis       = st.session_state.get(f"pa_pnis_{sfx}", "Seleccione...")
        desminado                = st.session_state.get(f"pa_desminado_{sfx}", "Seleccione...")
        participa_otras          = st.session_state.get(f"pa_otras_org_{sfx}", "Seleccione...")
        if participa_otras == "SI":
            otras_orgs = list(st.session_state.get(f"otras_orgs_temp_{sfx}", []))

    # Partido Comunes
    instancias_comunes = []
    participa_comunes  = "SI" if mostrar_cargo_comunes else ""
    concejo_comunes    = ""
    _familiar_parte_si = es_familiar_reincorporado and familiar_parte_comunes == "SI"
    if mostrar_cargo_comunes or _familiar_parte_si:
        concejo_comunes = st.session_state.get(f"pa_concejo_{sfx}", "")
    if mostrar_cargo_comunes:
        instancias_comunes = list(st.session_state.get(f"instancias_comunes_temp_{sfx}", []))

    _ic0 = instancias_comunes[0] if instancias_comunes else {}
    _oo0 = otras_orgs[0]         if otras_orgs         else {}

    def _clean(v): return v if v and v != "Seleccione..." else ""

    return {
        "familiar_parte_comunes": familiar_parte_comunes,
        "nivel_educativo":        nivel_edu,
        "fuente_ingresos":        _clean(fuente_ingresos),
        "estado_proyecto_arn":    _clean(estado_arn),
        "actividad_economica":    _clean(actividad_eco),
        "comparecencia_jep":      _clean(comparecencia_jep),
        "macrocasos_jep":         macrocaso_comp,
        "victima_jep":            _clean(victima_jep),
        "macrocaso_victima":      macrocaso_vic,
        "participacion_toar":     _clean(participacion_toar),
        "busqueda_desaparecidos": _clean(busqueda_desaparecidos),
        "participacion_pnis":     _clean(participacion_pnis),
        "desminado":              _clean(desminado),
        "participa_comunes":      participa_comunes,
        "concejo_comunes":        concejo_comunes,
        "instancias_comunes":     instancias_comunes,
        "instancias_partido":     _ic0.get("instancias_partido", ""),
        "roles_partido":          _ic0.get("roles_partido", ""),
        "consejeria_nacional":    _ic0.get("consejeria_nacional", ""),
        "tipo_consejeria":        _ic0.get("tipo_consejeria", ""),
        "participa_otras_org":    _clean(participa_otras),
        "otras_orgs":             otras_orgs,
        "tipo_org":               _oo0.get("tipo_org", ""),
        "nombre_org":             _oo0.get("nombre_org", ""),
        "ambito_org":             _oo0.get("ambito_org", ""),
        "escala_org":             _oo0.get("escala_org", ""),
        "departamento_org":       _oo0.get("departamento_org", ""),
        "municipio_org":          _oo0.get("municipio_org", ""),
        "rol_org":                _oo0.get("rol_org", ""),
        "anio_inicio_org":        _oo0.get("anio_inicio_org", ""),
        "anio_fin_org":           _oo0.get("anio_fin_org", ""),
        "cargo_eleccion":         _clean(st.session_state.get(f"pa_cargo_{sfx}", "Seleccione...")),
    }




def formulario_casos(tipo="individual"):
    es_individual     = tipo == "individual"
    color             = "#4F8BFF" if es_individual else "#4ADE80"
    icono             = "👤"      if es_individual else "👥"
    label_badge       = "INDIVIDUAL" if es_individual else "COLECTIVO"
    titulo            = "Formulario Individual" if es_individual else "Formulario Colectivo"
    nombre_hoja_casos = TAB_NOMBRES[tipo]["casos"]

    (hoja_casos, hoja_hechos, hoja_perfiles, hoja_antecedentes,
     hoja_perfiles_actuales, hoja_desplazamientos, hoja_verificaciones,
     hoja_instancias_comunes, hoja_otras_orgs, sheet_url) = conectar_sheet_casos(tipo)
    if hoja_casos is None:
        st.error("⚠️ No se pudo conectar a Google Sheets"); return

    # ── Retomar borrador ──────────────────────────────────────────────────────
    _borrador_key = f"borrador_cargado_{tipo}"
    if not st.session_state.get(_borrador_key):
        borrador = cargar_borrador(st.session_state.username, tipo)
        if not borrador:
            # Sin borrador previo: marcar como revisado para evitar consultas repetidas
            st.session_state[_borrador_key] = True
        if borrador:
            st.warning(
                f"📝 Tienes un borrador guardado el **{borrador.get('_guardado_en', '—')}**. "
                "¿Deseas retomarlo?"
            )
            col_ret, col_des = st.columns(2)
            with col_ret:
                if st.button("↩️ Retomar borrador", use_container_width=True, type="primary", key=f"btn_retomar_{tipo}"):
                    _campos_fecha = {f"caso_fecha_nacimiento_{tipo}", f"caso_fecha_expedicion_{tipo}"}
                    _todos_campos = [
                        f"caso_tipo_estudio_{tipo}",
                        f"caso_ot_anio_{tipo}", f"caso_ot_numero_{tipo}",
                        f"caso_solicitante_{tipo}", f"caso_fecha_expedicion_{tipo}",
                        f"caso_tipo_poblacion_{tipo}",
                        *[f"subpob_{i}_{tipo}" for i in range(len(_SUBPOBLACIONES))],
                        f"caso_fecha_nacimiento_{tipo}", f"caso_sexo_{tipo}",
                        f"caso_genero_{tipo}", f"caso_orientacion_{tipo}", f"caso_jefatura_{tipo}",
                        f"p_departamento_{tipo}", f"p_municipio_{tipo}",
                        f"caso_zona_rural_{tipo}", f"caso_zona_reserva_{tipo}",
                        f"caso_nivel_riesgo_{tipo}", f"caso_observaciones_{tipo}",
                        f"caso_num_personas_{tipo}", f"caso_companero_{tipo}",
                        f"caso_hijos_menores_{tipo}", f"caso_menores_otros_{tipo}",
                        f"caso_adultos_mayores_{tipo}", f"caso_discapacidad_{tipo}",
                        f"caso_osiegd_{tipo}",
                        f"caso_factor_discapacidad_{tipo}", f"caso_factor_etnia_{tipo}",
                        f"caso_factor_campesino_{tipo}", f"caso_factor_cuidador_{tipo}",
                        *[f"victima_{i}_{tipo}" for i in range(len(_VICTIMA_CONFLICTO_ARMADO))],
                        *[f"lider_{i}_{tipo}" for i in range(len(_LIDER_SOCIAL_DDHH))],
                    ]
                    for campo in _todos_campos:
                        if campo in borrador:
                            valor = borrador[campo]
                            if campo in _campos_fecha and isinstance(valor, str) and valor:
                                try:
                                    valor = date.fromisoformat(valor)
                                except ValueError:
                                    valor = None
                            st.session_state[campo] = valor
                    st.session_state.hechos        = borrador.get("hechos", [])
                    st.session_state.perfiles      = borrador.get("perfiles", [])
                    st.session_state.antecedentes  = borrador.get("antecedentes", [])
                    st.session_state.perfiles_actuales = borrador.get("perfiles_actuales", [])
                    st.session_state.desplazamientos   = borrador.get("desplazamientos", [])
                    st.session_state.verificaciones    = borrador.get("verificaciones", [])
                    st.session_state[_borrador_key] = True
                    st.rerun()
            with col_des:
                if st.button("🗑️ Descartar borrador", use_container_width=True, type="secondary", key=f"btn_descartar_{tipo}"):
                    eliminar_borrador(st.session_state.username, tipo)
                    for _campo in [
                        f"caso_tipo_estudio_{tipo}",
                        f"caso_ot_anio_{tipo}", f"caso_ot_numero_{tipo}",
                        f"caso_solicitante_{tipo}", f"caso_fecha_expedicion_{tipo}",
                        f"caso_tipo_poblacion_{tipo}",
                        *[f"subpob_{i}_{tipo}" for i in range(len(_SUBPOBLACIONES))],
                        f"caso_fecha_nacimiento_{tipo}", f"caso_sexo_{tipo}",
                        f"caso_genero_{tipo}", f"caso_orientacion_{tipo}", f"caso_jefatura_{tipo}",
                        f"p_departamento_{tipo}", f"p_municipio_{tipo}",
                        f"caso_zona_rural_{tipo}", f"caso_zona_reserva_{tipo}",
                        f"caso_nivel_riesgo_{tipo}", f"caso_observaciones_{tipo}",
                        f"caso_num_personas_{tipo}", f"caso_companero_{tipo}",
                        f"caso_hijos_menores_{tipo}", f"caso_menores_otros_{tipo}",
                        f"caso_adultos_mayores_{tipo}", f"caso_discapacidad_{tipo}",
                        f"caso_osiegd_{tipo}",
                        f"caso_factor_discapacidad_{tipo}", f"caso_factor_etnia_{tipo}",
                        f"caso_factor_campesino_{tipo}", f"caso_factor_cuidador_{tipo}",
                        *[f"victima_{i}_{tipo}" for i in range(len(_VICTIMA_CONFLICTO_ARMADO))],
                        *[f"lider_{i}_{tipo}" for i in range(len(_LIDER_SOCIAL_DDHH))],
                    ]:
                        st.session_state.pop(_campo, None)
                    desp_guardados = 0
                    for desp in st.session_state.desplazamientos:
                        id_desp = obtener_siguiente_id(hoja_desplazamientos)
                        hoja_desplazamientos.append_row([
                            id_desp, id_caso, ot_te.strip(),
                            desp.get("motivo", ""),
                            desp.get("medios_transporte", ""),
                            desp.get("dep_origen", ""),
                            desp.get("mun_origen", ""),
                            desp.get("dep_destino", ""),
                            desp.get("mun_destino", ""),
                            desp.get("frecuencia", ""),
                            desp.get("tipo_via", ""),
                            st.session_state.nombre_completo, st.session_state.username
                        ])
                        desp_guardados += 1
                    ver_guardados = 0
                    for ver in st.session_state.verificaciones:
                        id_ver = obtener_siguiente_id(hoja_verificaciones)
                        hoja_verificaciones.append_row([
                            id_ver, id_caso, ot_te.strip(),
                            ver.get("fuente", ""),
                            ver.get("nombre_fuente", ""),
                            ver.get("v_hechos_riesgo", ""),
                            ver.get("v_lugar_hechos", ""),
                            ver.get("v_actor_hechos", ""),
                            ver.get("v_motivacion_amenaza", ""),
                            ver.get("v_perfil_antiguo", ""),
                            ver.get("v_modo_participacion", ""),
                            ver.get("v_rol_perfil_antiguo", ""),
                            ver.get("v_frente_columna", ""),
                            ver.get("v_perfil_actual", ""),
                            ver.get("v_organizacion", ""),
                            ver.get("v_rol_perfil_actual", ""),
                            st.session_state.nombre_completo, st.session_state.username
                        ])
                        ver_guardados += 1
                    st.session_state.hechos = []
                    st.session_state.perfiles = []
                    st.session_state.antecedentes = []
                    st.session_state.perfiles_actuales = []
                    st.session_state.desplazamientos = []
                    st.session_state.verificaciones = []
                    st.session_state[_borrador_key] = True
                    st.rerun()
            st.stop()

    col_back, col_title = st.columns([1, 4])
    with col_back:
        if st.button("← Volver", type="secondary"):
            st.session_state.vista = None
            st.session_state.hechos = []
            st.session_state.perfiles = []
            st.session_state.antecedentes = []
            st.session_state[f"borrador_cargado_{tipo}"] = False
            st.rerun()
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
    st.subheader("📝 DATOS DE OT/TE")

    # ── Tipo de estudio (ancho completo) ─────────────────────────────────────
    tipo_estudio = st.selectbox(
        "Tipo de Estudio *",
        ["Seleccione...", "Tipo de Orden de Trabajo", "Trámite de Emergencia"],
        key=f"caso_tipo_estudio_{tipo}"
    )

    es_emergencia = tipo_estudio == "Trámite de Emergencia"

    # ── Fila: Año OT | Número OT ──────────────────────────────────────────────
    col_anio, col_num = st.columns(2)
    with col_anio:
        label_anio = "Año OT" if es_emergencia else "Año OT *"
        ot_anio = st.number_input(label_anio, min_value=2000, max_value=2026, value=None,
                                  step=1, key=f"caso_ot_anio_{tipo}")
    with col_num:
        label_num = "Número OT" if es_emergencia else "Número OT *"
        ot_numero = st.number_input(label_num, min_value=0, max_value=9999, value=None,
                                    step=1, key=f"caso_ot_numero_{tipo}")

    ot_te = f"OT-{int(ot_anio)}-{str(int(ot_numero)).zfill(3)}" if (ot_anio is not None and ot_numero is not None) else ""

    # ── Fila: Entidad Solicitante | Fecha Expedición OT ──────────────────────
    col_sol, col_fecha_ot = st.columns(2)
    with col_sol:
        solicitante = st.selectbox("Entidad Solicitante *", ["Seleccione...", "ARN", "SESP", "OTRO"],
                                   key=f"caso_solicitante_{tipo}")
    with col_fecha_ot:
        fecha_expedicion_ot = st.date_input("Fecha de Expedición OT *", value=None,
                                            key=f"caso_fecha_expedicion_{tipo}")

    # ── Tipo de Población (fila propia) ──────────────────────────────────────
    tipo_poblacion = st.selectbox("Tipo de Población *", _TIPOS_POBLACION,
                                  key=f"caso_tipo_poblacion_{tipo}")

    # ── Subpoblación: checkboxes en cuadrícula de 2 columnas ─────────────────
    st.markdown("**Subpoblación \\***")
    cols_chk = st.columns(2)
    subpoblacion = [
        opcion for i, opcion in enumerate(_SUBPOBLACIONES)
        if cols_chk[i % 2].checkbox(opcion, key=f"subpob_{i}_{tipo}")
    ]

    # Controla si se muestra la sección Perfil Antiguo
    _mostrar_perfil_antiguo = tipo_poblacion in ("REINCORPORADO/A", "FAMILIAR DE REINCORPORADO/A")

    st.markdown("---")
    st.subheader("👤 CARACTERÍSTICAS DEMOGRÁFICAS")

    # ── Fila: Fecha de Nacimiento | Sexo (solo individual) ───────────────────
    if es_individual:
        col_fnac, col_sexo = st.columns(2)
        with col_fnac:
            fecha_nacimiento = st.date_input("Fecha de Nacimiento *", value=None,
                                             min_value=date(1900, 1, 1),
                                             max_value=date.today(),
                                             key=f"caso_fecha_nacimiento_{tipo}")
        with col_sexo:
            sexo = st.selectbox("Sexo *", ["Seleccione...", "Hombre", "Mujer", "Intersexual"],
                                key=f"caso_sexo_{tipo}")
    else:
        fecha_nacimiento = None
        sexo = ""
        genero = None
        orientacion_sexual = None
        jefatura_hogar = None

    # ── Fila: Género | Orientación Sexual | Jefatura del Hogar (solo individual)
    if es_individual:
        col_gen, col_ori, col_jef = st.columns(3)
        with col_gen:
            genero = st.selectbox("Género *", _GENEROS, key=f"caso_genero_{tipo}")
        with col_ori:
            orientacion_sexual = st.selectbox("Orientación Sexual *", _ORIENTACIONES_SEXUALES,
                                              key=f"caso_orientacion_{tipo}")
        with col_jef:
            jefatura_hogar = st.selectbox("Jefatura del Hogar *", _JEFATURA_HOGAR,
                                          key=f"caso_jefatura_{tipo}")

    # ── Fila: Departamento | Municipio ────────────────────────────────────────
    col_dep, col_mun = st.columns(2)
    with col_dep:
        departamento = st.selectbox("SELECCIONE EL DEPARTAMENTO *",
                                    ["Seleccione..."] + list(_MUNICIPIOS.keys()),
                                    key=f"p_departamento_{tipo}")
    with col_mun:
        municipio = st.selectbox("SELECCIONE EL MUNICIPIO *",
                                 _MUNICIPIOS.get(departamento, ["Seleccione..."]),
                                 key=f"p_municipio_{tipo}")

    # ── Fila: Zona Rural | Zona de Reserva Campesina (solo individual) ─────────
    if es_individual:
        col_rural, col_reserva = st.columns(2)
        with col_rural:
            zona_rural = st.selectbox("¿Vive en zona rural? *", _SI_NO_REPORTA,
                                      key=f"caso_zona_rural_{tipo}")
        with col_reserva:
            zona_reserva = st.selectbox("¿Vive en zona de reserva campesina? *", _SI_NO_REPORTA,
                                        key=f"caso_zona_reserva_{tipo}")
    else:
        zona_rural = ""
        zona_reserva = ""

    # ── Composición Núcleo Familiar (solo individual) ─────────────────────────
    if es_individual:
        st.markdown("---")
        st.subheader("👨‍👩‍👧‍👦 COMPOSICIÓN NÚCLEO FAMILIAR")

        col_np, col_cp = st.columns(2)
        with col_np:
            num_personas = st.number_input("Número de personas en el núcleo familiar *",
                                           min_value=0, step=1, value=None,
                                           key=f"caso_num_personas_{tipo}")
        with col_cp:
            companero = st.selectbox("¿Tiene compañero(a) permanente? *", _SI_NO,
                                     key=f"caso_companero_{tipo}")

        col_hm, col_md = st.columns(2)
        with col_hm:
            num_hijos_menores = st.number_input("Número de hijos menores de edad *",
                                                min_value=0, step=1, value=None,
                                                key=f"caso_hijos_menores_{tipo}")
        with col_md:
            num_menores_otros = st.number_input("Número de menores de edad distintos a hijos *",
                                                min_value=0, step=1, value=None,
                                                key=f"caso_menores_otros_{tipo}")

        col_am, col_di = st.columns(2)
        with col_am:
            num_adultos_mayores = st.number_input("Número de adultos mayores (60 años en adelante) *",
                                                  min_value=0, step=1, value=None,
                                                  key=f"caso_adultos_mayores_{tipo}")
        with col_di:
            num_discapacidad = st.number_input("Número de personas en situación de discapacidad *",
                                               min_value=0, step=1, value=None,
                                               key=f"caso_discapacidad_{tipo}")
    else:
        num_personas = None
        companero = ""
        num_hijos_menores = None
        num_menores_otros = None
        num_adultos_mayores = None
        num_discapacidad = None
        osiegd = ""
        factor_discapacidad = ""
        factor_etnia = ""
        factor_campesino = ""
        factor_cuidador = ""
        victima_conflicto = []
        lider_social = []

    # ── Factores Diferenciales (solo individual) ───────────────────────────────
    if es_individual:
        st.markdown("---")
        st.subheader("🏷️ FACTORES DIFERENCIALES")

        osiegd = st.text_input(
            "F. Orientación Sexual, Identidad y Expresión de Género Diversa (OSIEGD)",
            key=f"caso_osiegd_{tipo}"
        )

        col_fd, col_fe = st.columns(2)
        with col_fd:
            factor_discapacidad = st.selectbox("F. Discapacidad *", _DISCAPACIDAD,
                                               key=f"caso_factor_discapacidad_{tipo}")
        with col_fe:
            factor_etnia = st.selectbox("F. Étnico *", _ETNIA,
                                        key=f"caso_factor_etnia_{tipo}")

        col_fc, col_fcuid = st.columns(2)
        with col_fc:
            factor_campesino = st.selectbox("F. Campesino *", _SI_NO_REPORTA,
                                            key=f"caso_factor_campesino_{tipo}")
        with col_fcuid:
            factor_cuidador = st.selectbox("F. Cuidador *", _CUIDADOR,
                                           key=f"caso_factor_cuidador_{tipo}")

        st.markdown("**F. Víctima de Conflicto Armado \\***")
        cols_vic = st.columns(2)
        victima_conflicto = [
            opcion for i, opcion in enumerate(_VICTIMA_CONFLICTO_ARMADO)
            if cols_vic[i % 2].checkbox(opcion, key=f"victima_{i}_{tipo}")
        ]

        st.markdown("**F. Líder Social y Defensor de DDHH \\***")
        cols_lid = st.columns(2)
        lider_social = [
            opcion for i, opcion in enumerate(_LIDER_SOCIAL_DDHH)
            if cols_lid[i % 2].checkbox(opcion, key=f"lider_{i}_{tipo}")
        ]

    # ── Antecedentes ──────────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("📁 ANTECEDENTES")
    st.caption("Opcional. Agrega uno o varios antecedentes asociados a este caso.")

    if "antecedentes" not in st.session_state:
        st.session_state.antecedentes = []

    _edit_ant_key = f"editando_antecedente_{tipo}"
    _REGISTRA_RES = ["Seleccione...", "SI", "NO", "SI MEDIDAS COLECTIVAS"]

    for i, ant in enumerate(st.session_state.antecedentes):
        with st.container(border=True):
            if st.session_state.get(_edit_ant_key) == i:
                # ── Modo edición ──────────────────────────────────────────────
                st.markdown(f"**✏️ Editando Antecedente #{i+1}**")
                _anio_val_e = int(ant.get("anio_resolucion")) if str(ant.get("anio_resolucion","")).isdigit() else None
                _mes_val_e  = int(ant.get("mes_resolucion"))  if str(ant.get("mes_resolucion","")).isdigit()  else None
                _dia_val_e  = int(ant.get("dia_resolucion"))  if str(ant.get("dia_resolucion","")).isdigit()  else None

                _reg_ot_opts = ["Seleccione...", "SI", "NO"]
                ea_reg_ot = st.selectbox(
                    "¿REGISTRA OT ANTECEDENTES? *", _reg_ot_opts,
                    index=_reg_ot_opts.index(ant.get("registra_ot","Seleccione..."))
                          if ant.get("registra_ot","") in _reg_ot_opts else 0,
                    key=f"ea_reg_ot_{tipo}_{i}"
                )
                ea_reg_res = st.selectbox(
                    "¿REGISTRA RESOLUCIONES O MEDIDAS VIGENTES? *", _REGISTRA_RES,
                    index=_REGISTRA_RES.index(ant.get("registra_resoluciones","Seleccione..."))
                          if ant.get("registra_resoluciones","") in _REGISTRA_RES else 0,
                    key=f"ea_reg_res_{tipo}_{i}"
                )
                col_a1, col_a2, col_a3 = st.columns(3)
                with col_a1:
                    ea_anio = st.number_input(
                        "AÑO RESOLUCIÓN MTSP", min_value=2000, max_value=2099,
                        value=_anio_val_e, step=1, key=f"ea_anio_{tipo}_{i}"
                    )
                with col_a2:
                    ea_mes = st.number_input(
                        "MES RESOLUCIÓN MTSP", min_value=1, max_value=12,
                        value=_mes_val_e, step=1, key=f"ea_mes_{tipo}_{i}"
                    )
                _e_max_dia = 31
                _e_dia_key = f"ea_dia_{tipo}_{i}"
                if ea_anio is not None and ea_mes is not None:
                    try:
                        _e_max_dia = calendar.monthrange(int(ea_anio), int(ea_mes))[1]
                        _e_dia_cur = st.session_state.get(_e_dia_key)
                        if _e_dia_cur is not None and _e_dia_cur > _e_max_dia:
                            st.session_state[_e_dia_key] = _e_max_dia
                    except Exception:
                        _e_max_dia = 31
                with col_a3:
                    ea_dia = st.number_input(
                        "DÍA RESOLUCIÓN MTSP", min_value=1, max_value=_e_max_dia,
                        value=_dia_val_e, step=1, key=_e_dia_key
                    )
                col_save_a, col_cancel_a = st.columns(2)
                with col_save_a:
                    if st.button("💾 Guardar cambios", key=f"ea_save_{tipo}_{i}",
                                 type="primary", use_container_width=True):
                        err_ea = []
                        if ea_reg_ot  == "Seleccione...": err_ea.append("Debe indicar si registra OT antecedentes")
                        if ea_reg_res == "Seleccione...": err_ea.append("Debe indicar si registra resoluciones o medidas vigentes")
                        if err_ea:
                            for e in err_ea: st.error(f"• {e}")
                        else:
                            st.session_state.antecedentes[i] = {
                                "registra_ot":            ea_reg_ot,
                                "registra_resoluciones":  ea_reg_res,
                                "anio_resolucion":        str(int(ea_anio)) if ea_anio is not None else "",
                                "mes_resolucion":         str(int(ea_mes))  if ea_mes  is not None else "",
                                "dia_resolucion":         str(int(ea_dia))  if ea_dia  is not None else "",
                            }
                            st.session_state[_edit_ant_key] = None
                            st.rerun()
                with col_cancel_a:
                    if st.button("✖ Cancelar", key=f"ea_cancel_{tipo}_{i}",
                                 type="secondary", use_container_width=True):
                        st.session_state[_edit_ant_key] = None
                        st.rerun()
            else:
                # ── Modo lectura ──────────────────────────────────────────────
                col_tit_a, col_edit_a, col_del_a = st.columns([4, 1, 1])
                with col_tit_a:
                    st.markdown(f"**Antecedente #{i+1}**")
                with col_edit_a:
                    if st.button("✏️", key=f"edit_a_{tipo}_{i}", help="Editar este antecedente"):
                        st.session_state[_edit_ant_key] = i
                        st.rerun()
                with col_del_a:
                    if st.button("🗑️", key=f"del_a_{tipo}_{i}", help="Eliminar este antecedente"):
                        st.session_state.antecedentes.pop(i)
                        st.session_state[_edit_ant_key] = None
                        st.rerun()
                ca1, ca2 = st.columns(2)
                with ca1:
                    st.write(f"📋 **¿Registra OT Antecedentes?:** {ant.get('registra_ot','')}")
                    st.write(f"📋 **¿Registra Resoluciones?:** {ant.get('registra_resoluciones','')}")
                with ca2:
                    _fecha_ant = " / ".join(filter(None, [
                        ant.get("dia_resolucion",""),
                        ant.get("mes_resolucion",""),
                        ant.get("anio_resolucion","")
                    ]))
                    if _fecha_ant:
                        st.write(f"📅 **Fecha Resolución MTSP (D/M/A):** {_fecha_ant}")

    with st.expander("➕ Agregar Antecedente", expanded=len(st.session_state.antecedentes) == 0):
        ant_reg_ot = st.selectbox(
            "¿REGISTRA OT ANTECEDENTES? *",
            ["Seleccione...", "SI", "NO"],
            key=f"ant_reg_ot_{tipo}"
        )
        ant_reg_res = st.selectbox(
            "¿REGISTRA RESOLUCIONES O MEDIDAS VIGENTES? *",
            _REGISTRA_RES,
            key=f"ant_reg_res_{tipo}"
        )
        col_anio_ant, col_mes_ant, col_dia_ant = st.columns(3)
        with col_anio_ant:
            ant_anio = st.number_input(
                "AÑO RESOLUCIÓN MTSP", min_value=2000, max_value=2099,
                value=None, step=1, key=f"ant_anio_{tipo}"
            )
        with col_mes_ant:
            ant_mes = st.number_input(
                "MES RESOLUCIÓN MTSP", min_value=1, max_value=12,
                value=None, step=1, key=f"ant_mes_{tipo}"
            )
        _max_dia_ant = 31
        _dia_ant_key = f"ant_dia_{tipo}"
        if ant_anio is not None and ant_mes is not None:
            try:
                _max_dia_ant = calendar.monthrange(int(ant_anio), int(ant_mes))[1]
                _dia_cur_ant = st.session_state.get(_dia_ant_key)
                if _dia_cur_ant is not None and _dia_cur_ant > _max_dia_ant:
                    st.session_state[_dia_ant_key] = _max_dia_ant
            except Exception:
                _max_dia_ant = 31
        with col_dia_ant:
            ant_dia = st.number_input(
                "DÍA RESOLUCIÓN MTSP", min_value=1, max_value=_max_dia_ant,
                value=None, step=1, key=_dia_ant_key
            )
        st.markdown("")
        if st.button("➕ Agregar este antecedente", use_container_width=True,
                     key=f"btn_add_ant_{tipo}", type="secondary"):
            err_ant = []
            if ant_reg_ot  == "Seleccione...": err_ant.append("Debe indicar si registra OT antecedentes")
            if ant_reg_res == "Seleccione...": err_ant.append("Debe indicar si registra resoluciones o medidas vigentes")
            if err_ant:
                for e in err_ant: st.error(f"• {e}")
            else:
                st.session_state.antecedentes.append({
                    "registra_ot":           ant_reg_ot,
                    "registra_resoluciones": ant_reg_res,
                    "anio_resolucion":       str(int(ant_anio)) if ant_anio is not None else "",
                    "mes_resolucion":        str(int(ant_mes))  if ant_mes  is not None else "",
                    "dia_resolucion":        str(int(ant_dia))  if ant_dia  is not None else "",
                })
                st.success("✅ Antecedente agregado"); st.rerun()

    # ── Perfil Antiguo (solo si aplica según tipo de población) ─────────────
    if _mostrar_perfil_antiguo:
        # ── Perfil Antiguo ────────────────────────────────────────────────────────
        st.markdown("---")
        st.subheader("Perfil Antiguo")
        st.caption("Opcional. Agrega uno o varios perfiles FARC-EP asociados a este caso.")

        if "perfiles" not in st.session_state:
            st.session_state.perfiles = []

        _edit_perfil_key = f"editando_perfil_{tipo}"
        _MODOS_PART = ["Seleccione...", "Combatiente", "Miliciano/a", "Colaborador/a",
                       "Privado de la libertad", "Otro"]

        for i, perfil in enumerate(st.session_state.perfiles):
            with st.container(border=True):
                if st.session_state.get(_edit_perfil_key) == i:
                    # ── Modo edición ──────────────────────────────────────────────
                    st.markdown(f"**✏️ Editando Perfil #{i+1}**")
                    pc1, pc2 = st.columns(2)
                    with pc1:
                        ep_modo = st.selectbox("MODO DE PARTICIPACIÓN EN LAS FARC-EP *", _MODOS_PART,
                            index=_MODOS_PART.index(perfil.get("modo_participacion","Seleccione..."))
                                  if perfil.get("modo_participacion","") in _MODOS_PART else 0,
                            key=f"ep_modo_{tipo}_{i}")
                        ep_anio = st.number_input("AÑO DE INGRESO, TRASLADO O CAPTURA *",
                            min_value=1950, max_value=2026, step=1,
                            value=int(perfil["anio_ingreso"]) if str(perfil.get("anio_ingreso","")).isdigit() else 2000,
                            key=f"ep_anio_{tipo}_{i}")
                        _bloques = ["Seleccione..."] + list(_ESTRUCTURAS.keys())
                        ep_bloque = st.selectbox("SELECCIONE EL BLOQUE DE OPERACIÓN *", _bloques,
                            index=_bloques.index(perfil.get("bloque","Seleccione..."))
                                  if perfil.get("bloque","") in _bloques else 0,
                            key=f"ep_bloque_{tipo}_{i}")
                    with pc2:
                        ep_estructura = "Seleccione..."
                        if ep_bloque != "Seleccione...":
                            _ops_est = _ESTRUCTURAS[ep_bloque]
                            ep_estructura = st.selectbox("ESTRUCTURA *", _ops_est,
                                index=_ops_est.index(perfil.get("estructura",""))
                                      if perfil.get("estructura","") in _ops_est else 0,
                                key=f"ep_estructura_{tipo}_{i}")
                        ep_lugar = st.selectbox("LUGAR DE ACREDITACIÓN *", _LUGAR_ACREDITACION,
                            index=_LUGAR_ACREDITACION.index(perfil.get("lugar_acreditacion","Seleccione..."))
                                  if perfil.get("lugar_acreditacion","") in _LUGAR_ACREDITACION else 0,
                            key=f"ep_lugar_{tipo}_{i}")

                    _rol_actual = [r.strip() for r in perfil.get("rol","").split("|")
                                   if r.strip() in _ROLES[1:]]
                    st.markdown("**ROL/ACTIVIDADES P_ANTIGUO \\***")
                    cols_rol_ep = st.columns(2)
                    ep_rol = [
                        opcion for j, opcion in enumerate(_ROLES[1:])
                        if cols_rol_ep[j % 2].checkbox(opcion, value=(opcion in _rol_actual),
                                                        key=f"ep_rol_{j}_{tipo}_{i}")
                    ]

                    ep_otro_rol = ""
                    if "Otro" in ep_rol:
                        ep_otro_rol = st.text_input("¿QUÉ OTRO ROL?",
                            value=perfil.get("otro_rol",""), key=f"ep_otro_rol_{tipo}_{i}")

                    ep_mostrar_libertad = (ep_modo == "Privado de la libertad")
                    ep_meses = ""
                    ep_inst  = "Seleccione..."
                    if ep_mostrar_libertad:
                        ep_meses = st.number_input("NO. MESES PRIVADO DE LA LIBERTAD",
                            min_value=0, max_value=600, step=1,
                            value=int(perfil["meses_privado"]) if str(perfil.get("meses_privado","")).isdigit() else 0,
                            key=f"ep_meses_{tipo}_{i}")
                        ep_inst = st.selectbox("TIPO DE INSTITUCIÓN PENITENCIARIA", _INSTITUCIONES,
                            index=_INSTITUCIONES.index(perfil.get("tipo_institucion","Seleccione..."))
                                  if perfil.get("tipo_institucion","") in _INSTITUCIONES else 0,
                            key=f"ep_inst_{tipo}_{i}")

                    ep_pabellon = ""
                    if ep_mostrar_libertad and ep_inst == "CO -COMPLEJO CARCELARÍO":
                        _pab = ["Seleccione...", "Sí", "No"]
                        ep_pabellon = st.selectbox("PABELLÓN DE ALTA SEGURIDAD", _pab,
                            index=_pab.index(perfil.get("pabellon_alta_seguridad","Seleccione..."))
                                  if perfil.get("pabellon_alta_seguridad","") in _pab else 0,
                            key=f"ep_pabellon_{tipo}_{i}")

                    col_save, col_cancel = st.columns(2)
                    with col_save:
                        if st.button("💾 Guardar cambios", key=f"ep_save_{tipo}_{i}",
                                     type="primary", use_container_width=True):
                            err_ep = []
                            if ep_modo      == "Seleccione...": err_ep.append("El modo de participación es obligatorio")
                            if ep_bloque    == "Seleccione...": err_ep.append("El bloque es obligatorio")
                            if ep_estructura== "Seleccione...": err_ep.append("La estructura es obligatoria")
                            if ep_lugar     == "Seleccione...": err_ep.append("El lugar de acreditación es obligatorio")
                            if len(ep_rol)  == 0:               err_ep.append("El rol es obligatorio")
                            if "Otro" in ep_rol and not ep_otro_rol.strip(): err_ep.append("Especifica el otro rol")
                            if err_ep:
                                for e in err_ep: st.error(f"• {e}")
                            else:
                                st.session_state.perfiles[i] = {
                                    "modo_participacion": ep_modo,
                                    "anio_ingreso":       ep_anio,
                                    "bloque":             ep_bloque,
                                    "estructura":         ep_estructura,
                                    "lugar_acreditacion": ep_lugar,
                                    "rol":                " | ".join(ep_rol),
                                    "otro_rol":           ep_otro_rol.strip(),
                                    "meses_privado":      str(ep_meses) if ep_mostrar_libertad else "",
                                    "tipo_institucion":   ep_inst if ep_inst != "Seleccione..." else "",
                                    "pabellon_alta_seguridad": ep_pabellon if ep_pabellon != "Seleccione..." else "",
                                }
                                st.session_state[_edit_perfil_key] = None
                                st.rerun()
                    with col_cancel:
                        if st.button("✖ Cancelar", key=f"ep_cancel_{tipo}_{i}",
                                     type="secondary", use_container_width=True):
                            st.session_state[_edit_perfil_key] = None
                            st.rerun()
                else:
                    # ── Modo lectura ──────────────────────────────────────────────
                    col_tit, col_edit, col_del = st.columns([4, 1, 1])
                    with col_tit: st.markdown(f"**Perfil #{i+1} — {perfil.get('modo_participacion', '')}**")
                    with col_edit:
                        if st.button("✏️", key=f"edit_p_{tipo}_{i}", help="Editar este perfil"):
                            st.session_state[_edit_perfil_key] = i
                            st.rerun()
                    with col_del:
                        if st.button("🗑️", key=f"del_perfil_{tipo}_{i}", help="Eliminar este perfil"):
                            st.session_state.perfiles.pop(i)
                            st.session_state[_edit_perfil_key] = None
                            st.rerun()
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

        with st.expander("➕ Agregar Perfil Antiguo", expanded=len(st.session_state.perfiles) == 0):

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

            p_estructura = "Seleccione..."
            if p_bloque != "Seleccione...":
                opciones_estructura = _ESTRUCTURAS[p_bloque]
                p_estructura = st.selectbox("ESTRUCTURA *", opciones_estructura,
                    key=f"p_estructura_{tipo}")

            p_lugar_acreditacion = st.selectbox("LUGAR DE ACREDITACIÓN *",
            _LUGAR_ACREDITACION,
                key=f"p_lugar_{tipo}")

            st.markdown("**ROL/ACTIVIDADES P_ANTIGUO \\***")
            cols_rol = st.columns(2)
            p_rol = [
                opcion for j, opcion in enumerate(_ROLES[1:])
                if cols_rol[j % 2].checkbox(opcion, key=f"p_rol_{j}_{tipo}")
            ]

            p_otro_rol = ""
            p_otro_rol_libre = ""
            if "Otro" in p_rol:
                p_otro_rol = st.text_input("¿QUÉ OTRO ROL?", key=f"p_otro_rol_{tipo}")
                p_otro_rol_libre = p_otro_rol

            mostrar_libertad = (p_modo == "Privado de la libertad")

            p_meses_privado    = ""
            p_tipo_institucion = "Seleccione..."
            if mostrar_libertad:
                p_meses_privado = st.number_input("NO. MESES PRIVADO DE LA LIBERTAD",
                    min_value=0, max_value=600, step=1, key=f"p_meses_{tipo}")

                p_tipo_institucion = st.selectbox("TIPO DE INSTITUCIÓN PENITENCIARIA",
                    _INSTITUCIONES, key=f"p_inst_{tipo}")

            p_pabellon = ""
            if mostrar_libertad and p_tipo_institucion == "CO -COMPLEJO CARCELARÍO":
                p_pabellon = st.selectbox("PABELLÓN DE ALTA SEGURIDAD",
                    ["Seleccione...", "Sí", "No"], key=f"p_pabellon_{tipo}")

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
                if len(p_rol) == 0:                              err_p.append("El rol es obligatorio")
                if "Otro" in p_rol and not p_otro_rol.strip():  err_p.append("Especifica el otro rol")
                if err_p:
                    for e in err_p: st.error(f"• {e}")
                else:
                    st.session_state.perfiles.append({
                        "modo_participacion":  p_modo,
                        "anio_ingreso":        p_anio,
                        "bloque":              p_bloque,
                        "estructura":          p_estructura,
                        "lugar_acreditacion":  p_lugar_acreditacion,
                        "rol":                 " | ".join(p_rol),
                        "otro_rol":            p_otro_rol.strip() if p_otro_rol else "",
                        "meses_privado":       str(p_meses_privado) if mostrar_libertad else "",
                        "tipo_institucion":    p_tipo_institucion if p_tipo_institucion != "Seleccione..." else "",
                        "pabellon_alta_seguridad": p_pabellon if p_pabellon != "Seleccione..." else "",
                    })
                    st.success("✅ Perfil Antiguo agregado"); st.rerun()

    # ══════════════════════════════════════════════════════════════════════════
    # 7. PERFIL ACTUAL
    # ══════════════════════════════════════════════════════════════════════════
    st.markdown("---")
    st.subheader("🎯 PERFIL ACTUAL")
    st.caption("Opcional. Agrega uno o varios perfiles del estado actual de reincorporación.")

    if "perfiles_actuales" not in st.session_state:
        st.session_state.perfiles_actuales = []

    # Banderas de condicionales basadas en tipo de población
    _es_reincorporado           = tipo_poblacion == "REINCORPORADO/A"
    _es_familiar_reincorporado  = tipo_poblacion == "FAMILIAR DE REINCORPORADO/A"
    _es_comunes            = tipo_poblacion in (
        "INTEGRANTE DEL PARTIDO COMUNES",
        "FAMILIAR DE INTEGRANTE DEL PARTIDO COMUNES",
    )
    _es_familiar_comunes   = tipo_poblacion == "FAMILIAR DE INTEGRANTE DEL PARTIDO COMUNES"
    _mostrar_cargo_comunes = tipo_poblacion in (
        "INTEGRANTE DEL PARTIDO COMUNES",
        "FAMILIAR DE INTEGRANTE DEL PARTIDO COMUNES",
    )

    _edit_pa_key = f"editando_pa_{tipo}"

    # ── Listado de perfiles actuales ya agregados ─────────────────────────────
    for i, pa in enumerate(st.session_state.perfiles_actuales):
        with st.container(border=True):
            col_tit_pa, col_edit_pa, col_del_pa = st.columns([4, 1, 1])
            with col_tit_pa:
                st.markdown(f"**Perfil Actual #{i+1}**")
            with col_edit_pa:
                if st.button("✏️", key=f"edit_pa_{tipo}_{i}", help="Editar"):
                    st.session_state[_edit_pa_key] = i
                    # Reset listas temporales para que se carguen desde el perfil editado
                    _sfx_edit = f"{tipo}_{i}"
                    st.session_state[f"instancias_comunes_temp_{_sfx_edit}"] = list(pa.get("instancias_comunes", []))
                    st.session_state[f"otras_orgs_temp_{_sfx_edit}"] = list(pa.get("otras_orgs", []))
                    st.rerun()
            with col_del_pa:
                if st.button("🗑️", key=f"del_pa_{tipo}_{i}", help="Eliminar"):
                    st.session_state.perfiles_actuales.pop(i)
                    st.session_state[_edit_pa_key] = None
                    st.rerun()

            if st.session_state.get(_edit_pa_key) == i:
                # ── Modo edición ──────────────────────────────────────────────
                st.markdown(f"**✏️ Editando Perfil Actual #{i+1}**")
                _render_pa_form(pa, tipo, i, _es_reincorporado, _es_familiar_reincorporado, _es_familiar_comunes, _mostrar_cargo_comunes)
                col_sv, col_cx = st.columns(2)
                with col_sv:
                    if st.button("💾 Guardar cambios", key=f"pa_save_{tipo}_{i}",
                                 type="primary", use_container_width=True):
                        nuevo = _recoger_pa(tipo, i, _es_reincorporado, _es_familiar_reincorporado, _es_familiar_comunes, _mostrar_cargo_comunes)
                        if nuevo is not None:
                            st.session_state.perfiles_actuales[i] = nuevo
                            st.session_state[_edit_pa_key] = None
                            st.rerun()
                with col_cx:
                    if st.button("✖ Cancelar", key=f"pa_cancel_{tipo}_{i}",
                                 type="secondary", use_container_width=True):
                        st.session_state[_edit_pa_key] = None
                        st.rerun()
            else:
                # ── Modo lectura ──────────────────────────────────────────────
                c1, c2 = st.columns(2)
                with c1:
                    st.write(f"📚 **Nivel Educativo:** {pa.get('nivel_educativo','')}")
                    st.write(f"💰 **Fuente Principal de Ingresos:** {pa.get('fuente_ingresos','')}")
                    if pa.get('estado_proyecto_arn'):
                        st.write(f"🏗️ **Estado Proyecto ARN:** {pa.get('estado_proyecto_arn','')}")
                    if pa.get('actividad_economica'):
                        st.write(f"📦 **Actividad Económica:** {pa.get('actividad_economica','')}")
                    # Instancias Comunes (multiregistro)
                    _ic_lista = pa.get('instancias_comunes', [])
                    if _ic_lista:
                        st.markdown("🏛️ **Instancias Partido Comunes:**")
                        for _ic_item in _ic_lista:
                            st.write(
                                f"  • {_ic_item.get('instancias_partido','—')} | "
                                f"Rol: {_ic_item.get('roles_partido','—')} | "
                                f"Consejería: {_ic_item.get('consejeria_nacional','—')}"
                            )
                with c2:
                    st.write(f"⚖️ **Comparecencia JEP:** {pa.get('comparecencia_jep','')}")
                    if pa.get('macrocasos_jep'):
                        st.write(f"📋 **Macrocasos JEP:** {pa.get('macrocasos_jep','')}")
                    st.write(f"🕊️ **Participación TOAR:** {pa.get('participacion_toar','')}")
                    st.write(f"🔍 **Búsqueda Personas Desaparecidas:** {pa.get('busqueda_desaparecidos','')}")
                    if pa.get('cargo_eleccion'):
                        st.write(f"🗳️ **Cargo Elección Popular:** {pa.get('cargo_eleccion','')}")
                    # Otras Organizaciones (multiregistro)
                    _oo_lista = pa.get('otras_orgs', [])
                    if _oo_lista:
                        st.markdown("🤝 **Otras Organizaciones:**")
                        for _oo_item in _oo_lista:
                            st.write(
                                f"  • {_oo_item.get('nombre_org','—')} | "
                                f"Tipo: {_oo_item.get('tipo_org','—')} | "
                                f"Rol: {_oo_item.get('rol_org','—')}"
                            )

    # ── Perfil Actual — solo se permite uno ─────────────────────────────────
    if len(st.session_state.perfiles_actuales) == 0:
        with st.expander("➕ Agregar Perfil Actual", expanded=True):
            _render_pa_form(None, tipo, "new", _es_reincorporado, _es_familiar_reincorporado, _es_familiar_comunes, _mostrar_cargo_comunes)
            st.markdown("")
            if st.button("✅ Guardar Perfil Actual", use_container_width=True,
                         key=f"btn_add_pa_{tipo}", type="primary"):
                nuevo = _recoger_pa(tipo, "new", _es_reincorporado, _es_familiar_reincorporado, _es_familiar_comunes, _mostrar_cargo_comunes)
                if nuevo is not None:
                    st.session_state.perfiles_actuales.append(nuevo)
                    # Limpiar listas temporales del formulario "new"
                    _sfx_new = f"{tipo}_new"
                    st.session_state.pop(f"instancias_comunes_temp_{_sfx_new}", None)
                    st.session_state.pop(f"otras_orgs_temp_{_sfx_new}", None)
                    st.session_state.pop(f"show_ic_form_{_sfx_new}", None)
                    st.session_state.pop(f"show_oo_form_{_sfx_new}", None)
                    st.success("✅ Perfil Actual guardado")
                    st.rerun()
    else:
        st.info("ℹ️ Ya existe un Perfil Actual registrado. Edítalo o elimínalo con los botones de arriba.")


    # 8. DESPLAZAMIENTOS
    # ══════════════════════════════════════════════════════════════════════════
    st.markdown("---")
    st.subheader("🚗 DESPLAZAMIENTOS")
    st.caption("Opcional. Agrega uno o varios desplazamientos asociados a este caso.")

    if "desplazamientos" not in st.session_state:
        st.session_state.desplazamientos = []

    def _render_desp_form(desp, tipo, idx):
        """Renderiza el formulario de un desplazamiento."""
        sfx = f"{tipo}_{idx}"
        def _dv(campo, defecto="Seleccione..."):
            return desp.get(campo, defecto) if desp else defecto

        # Motivo (siempre visible)
        motivo = st.selectbox(
            "MOTIVO DESPLAZAMIENTO *", _DESP_MOTIVOS,
            index=_DESP_MOTIVOS.index(_dv("motivo")) if _dv("motivo") in _DESP_MOTIVOS else 0,
            key=f"desp_motivo_{sfx}"
        )

        _es_no_reporta = motivo == "NO REPORTA"

        if not _es_no_reporta and motivo != "Seleccione...":
            # ── Medios de transporte (checkboxes multi) ───────────────────────
            _medios_prev = [x.strip() for x in _dv("medios_transporte", "").split("|") if x.strip()] if desp else []
            st.markdown("**MEDIO DE TRANSPORTE UTILIZADO EN LOS DESPLAZAMIENTOS**")
            cols_med = st.columns(3)
            for j, medio in enumerate(_DESP_MEDIOS_TRANSPORTE):
                cols_med[j % 3].checkbox(medio, value=(medio in _medios_prev), key=f"desp_medio_{j}_{sfx}")

            # ── Origen ────────────────────────────────────────────────────────
            col_do, col_mo = st.columns(2)
            with col_do:
                dep_origen = st.selectbox(
                    "DEPARTAMENTO ORIGEN", _DESP_DEPARTAMENTOS,
                    index=_DESP_DEPARTAMENTOS.index(_dv("dep_origen")) if _dv("dep_origen") in _DESP_DEPARTAMENTOS else 0,
                    key=f"desp_dep_origen_{sfx}"
                )
            with col_mo:
                _muns_origen = _MUNICIPIOS.get(dep_origen, ["Seleccione..."])
                if "Seleccione..." not in _muns_origen:
                    _muns_origen = ["Seleccione..."] + _muns_origen
                mun_origen_cur = _dv("mun_origen")
                st.selectbox(
                    "MUNICIPIO ORIGEN",
                    _muns_origen,
                    index=_muns_origen.index(mun_origen_cur) if mun_origen_cur in _muns_origen else 0,
                    key=f"desp_mun_origen_{sfx}"
                )

            # ── Destino ───────────────────────────────────────────────────────
            col_dd, col_md = st.columns(2)
            with col_dd:
                dep_destino = st.selectbox(
                    "DEPARTAMENTO DESTINO", _DESP_DEPARTAMENTOS,
                    index=_DESP_DEPARTAMENTOS.index(_dv("dep_destino")) if _dv("dep_destino") in _DESP_DEPARTAMENTOS else 0,
                    key=f"desp_dep_destino_{sfx}"
                )
            with col_md:
                _muns_destino = _MUNICIPIOS.get(dep_destino, ["Seleccione..."])
                if "Seleccione..." not in _muns_destino:
                    _muns_destino = ["Seleccione..."] + _muns_destino
                mun_destino_cur = _dv("mun_destino")
                st.selectbox(
                    "MUNICIPIO DESTINO",
                    _muns_destino,
                    index=_muns_destino.index(mun_destino_cur) if mun_destino_cur in _muns_destino else 0,
                    key=f"desp_mun_destino_{sfx}"
                )

            # ── Frecuencia y Tipo de vía ──────────────────────────────────────
            col_fr, col_via = st.columns(2)
            with col_fr:
                st.selectbox(
                    "FRECUENCIA DE DESPLAZAMIENTOS", _DESP_FRECUENCIAS,
                    index=_DESP_FRECUENCIAS.index(_dv("frecuencia")) if _dv("frecuencia") in _DESP_FRECUENCIAS else 0,
                    key=f"desp_frecuencia_{sfx}"
                )
            with col_via:
                st.selectbox(
                    "TIPO DE VÍA CON MAYOR DURACIÓN EN EL DESPLAZAMIENTO", _DESP_TIPOS_VIA,
                    index=_DESP_TIPOS_VIA.index(_dv("tipo_via")) if _dv("tipo_via") in _DESP_TIPOS_VIA else 0,
                    key=f"desp_tipo_via_{sfx}"
                )

    def _recoger_desp(tipo, idx):
        """Lee el estado de los widgets de Desplazamiento y retorna un dict."""
        sfx = f"{tipo}_{idx}"
        motivo = st.session_state.get(f"desp_motivo_{sfx}", "Seleccione...")
        if motivo == "Seleccione...":
            st.error("• El motivo del desplazamiento es obligatorio")
            return None

        _es_no_reporta = motivo == "NO REPORTA"

        medios = ""
        dep_origen = mun_origen = dep_destino = mun_destino = ""
        frecuencia = tipo_via = ""

        if not _es_no_reporta:
            medios = " | ".join([
                medio for j, medio in enumerate(_DESP_MEDIOS_TRANSPORTE)
                if st.session_state.get(f"desp_medio_{j}_{sfx}", False)
            ])
            dep_origen  = st.session_state.get(f"desp_dep_origen_{sfx}", "Seleccione...")
            mun_origen  = st.session_state.get(f"desp_mun_origen_{sfx}", "Seleccione...")
            dep_destino = st.session_state.get(f"desp_dep_destino_{sfx}", "Seleccione...")
            mun_destino = st.session_state.get(f"desp_mun_destino_{sfx}", "Seleccione...")
            frecuencia  = st.session_state.get(f"desp_frecuencia_{sfx}", "Seleccione...")
            tipo_via    = st.session_state.get(f"desp_tipo_via_{sfx}", "Seleccione...")

        return {
            "motivo":           motivo,
            "medios_transporte": medios,
            "dep_origen":       dep_origen  if dep_origen  != "Seleccione..." else "",
            "mun_origen":       mun_origen  if mun_origen  != "Seleccione..." else "",
            "dep_destino":      dep_destino if dep_destino != "Seleccione..." else "",
            "mun_destino":      mun_destino if mun_destino != "Seleccione..." else "",
            "frecuencia":       frecuencia  if frecuencia  != "Seleccione..." else "",
            "tipo_via":         tipo_via    if tipo_via    != "Seleccione..." else "",
        }

    _edit_desp_key = f"editando_desp_{tipo}"

    # ── Listado de desplazamientos ya agregados ───────────────────────────────
    for i, desp in enumerate(st.session_state.desplazamientos):
        with st.container(border=True):
            col_tit_d, col_edit_d, col_del_d = st.columns([4, 1, 1])
            with col_tit_d:
                st.markdown(f"**Desplazamiento #{i+1} — {desp.get('motivo','')}**")
            with col_edit_d:
                if st.button("✏️", key=f"edit_desp_{tipo}_{i}", help="Editar"):
                    st.session_state[_edit_desp_key] = i
                    st.rerun()
            with col_del_d:
                if st.button("🗑️", key=f"del_desp_{tipo}_{i}", help="Eliminar"):
                    st.session_state.desplazamientos.pop(i)
                    st.session_state[_edit_desp_key] = None
                    st.rerun()

            if st.session_state.get(_edit_desp_key) == i:
                st.markdown(f"**✏️ Editando Desplazamiento #{i+1}**")
                _render_desp_form(desp, tipo, i)
                col_sv, col_cx = st.columns(2)
                with col_sv:
                    if st.button("💾 Guardar cambios", key=f"desp_save_{tipo}_{i}",
                                 type="primary", use_container_width=True):
                        nuevo = _recoger_desp(tipo, i)
                        if nuevo is not None:
                            st.session_state.desplazamientos[i] = nuevo
                            st.session_state[_edit_desp_key] = None
                            st.rerun()
                with col_cx:
                    if st.button("✖ Cancelar", key=f"desp_cancel_{tipo}_{i}",
                                 type="secondary", use_container_width=True):
                        st.session_state[_edit_desp_key] = None
                        st.rerun()
            else:
                c1, c2 = st.columns(2)
                with c1:
                    st.write(f"🎯 **Motivo:** {desp.get('motivo','')}")
                    if desp.get('dep_origen'):
                        st.write(f"📍 **Origen:** {desp.get('mun_origen','')} — {desp.get('dep_origen','')}")
                    if desp.get('dep_destino'):
                        st.write(f"🏁 **Destino:** {desp.get('mun_destino','')} — {desp.get('dep_destino','')}")
                with c2:
                    if desp.get('medios_transporte'):
                        st.write(f"🚌 **Medios:** {desp.get('medios_transporte','')}")
                    if desp.get('frecuencia'):
                        st.write(f"🔁 **Frecuencia:** {desp.get('frecuencia','')}")
                    if desp.get('tipo_via'):
                        st.write(f"🛣️ **Tipo de Vía:** {desp.get('tipo_via','')}")

    # ── Formulario para agregar nuevo desplazamiento ──────────────────────────
    with st.expander("➕ Agregar Desplazamiento", expanded=len(st.session_state.desplazamientos) == 0):
        _render_desp_form(None, tipo, "new")
        st.markdown("")
        if st.button("➕ Agregar este Desplazamiento", use_container_width=True,
                     key=f"btn_add_desp_{tipo}", type="secondary"):
            nuevo = _recoger_desp(tipo, "new")
            if nuevo is not None:
                st.session_state.desplazamientos.append(nuevo)
                st.success("✅ Desplazamiento agregado")
                st.rerun()

    # ── Hechos de Riesgo ──────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("⚠️ Hechos de Riesgo")
    st.caption("Opcional. Agrega uno o varios hechos de riesgo asociados a este caso.")

    _edit_hecho_key = f"editando_hecho_{tipo}"

    for i, hecho in enumerate(st.session_state.hechos):
        with st.container(border=True):
            if st.session_state.get(_edit_hecho_key) == i:
                # ── Modo edición ──────────────────────────────────────────────
                st.markdown(f"**✏️ Editando Hecho #{i+1}**")
                try:
                    _eh_fecha_parts = datetime.strptime(hecho["fecha"], "%Y-%m-%d")
                    _eh_anio_val = _eh_fecha_parts.year
                    _eh_mes_val  = _eh_fecha_parts.month
                    _eh_dia_val  = _eh_fecha_parts.day
                except Exception:
                    _eh_anio_val = None
                    _eh_mes_val  = None
                    _eh_dia_val  = None
                _eh_anio_key = f"eh_anio_{tipo}_{i}"
                _eh_mes_key  = f"eh_mes_{tipo}_{i}"
                _eh_dia_key  = f"eh_dia_{tipo}_{i}"
                ec_anio, ec_mes, ec_dia = st.columns(3)
                with ec_anio:
                    eh_anio = st.number_input(
                        "AÑO DEL HECHO", min_value=1900, max_value=2099,
                        value=_eh_anio_val, step=1, key=_eh_anio_key
                    )
                with ec_mes:
                    eh_mes = st.number_input(
                        "MES DEL HECHO", min_value=1, max_value=12,
                        value=_eh_mes_val, step=1, key=_eh_mes_key
                    )
                _eh_max_dia = 31
                if eh_anio is not None and eh_mes is not None:
                    try:
                        _eh_max_dia = calendar.monthrange(int(eh_anio), int(eh_mes))[1]
                        _eh_dia_cur = st.session_state.get(_eh_dia_key)
                        if _eh_dia_cur is not None and _eh_dia_cur > _eh_max_dia:
                            st.session_state[_eh_dia_key] = _eh_max_dia
                    except Exception:
                        _eh_max_dia = 31
                with ec_dia:
                    eh_dia = st.number_input(
                        "DÍA DEL HECHO", min_value=1, max_value=_eh_max_dia,
                        value=_eh_dia_val, step=1, key=_eh_dia_key
                    )
                _eh_dep_opts = ["Seleccione..."] + list(_MUNICIPIOS.keys())
                _eh_dep_val  = hecho.get("departamento", "Seleccione...")
                _eh_dep_idx  = _eh_dep_opts.index(_eh_dep_val) if _eh_dep_val in _eh_dep_opts else 0
                ec_dep, ec_mun = st.columns(2)
                with ec_dep:
                    eh_departamento = st.selectbox(
                        "DEPARTAMENTO DEL HECHO", _eh_dep_opts,
                        index=_eh_dep_idx, key=f"eh_departamento_{tipo}_{i}"
                    )
                _eh_mun_opts = _MUNICIPIOS.get(eh_departamento, ["Seleccione..."])
                _eh_mun_val  = hecho.get("municipio", "Seleccione...")
                _eh_mun_idx  = _eh_mun_opts.index(_eh_mun_val) if _eh_mun_val in _eh_mun_opts else 0
                with ec_mun:
                    eh_municipio = st.selectbox(
                        "MUNICIPIO DEL HECHO", _eh_mun_opts,
                        index=_eh_mun_idx, key=f"eh_municipio_{tipo}_{i}"
                    )
                _eh_tipo_actor_opts = ["Seleccione..."] + _TIPOS_ACTOR_GENERADOR
                _eh_tipo_actor_val  = hecho.get("tipo_actor", "Seleccione...")
                _eh_tipo_actor_idx  = _eh_tipo_actor_opts.index(_eh_tipo_actor_val) if _eh_tipo_actor_val in _eh_tipo_actor_opts else 0
                ec_tipo_actor, ec_actor_gen = st.columns(2)
                with ec_tipo_actor:
                    eh_tipo_actor = st.selectbox(
                        "TIPO ACTOR GENERADOR HECHO DE RIESGO",
                        _eh_tipo_actor_opts,
                        index=_eh_tipo_actor_idx,
                        key=f"eh_tipo_actor_{tipo}_{i}"
                    )
                with ec_actor_gen:
                    eh_actor_generador = st.text_input(
                        "ACTOR GENERADOR HECHO RIESGO",
                        value=hecho.get("actor_generador", ""),
                        key=f"eh_actor_gen_{tipo}_{i}"
                    )
                ec_medio, ec_victima, ec_amenaza = st.columns(3)
                with ec_medio:
                    _eh_medio_val = hecho.get("medio", "Seleccione...")
                    eh_medio = st.selectbox(
                        "MEDIO HECHO DE RIESGO",
                        _MEDIOS_HECHO,
                        index=_MEDIOS_HECHO.index(_eh_medio_val) if _eh_medio_val in _MEDIOS_HECHO else 0,
                        key=f"eh_medio_{tipo}_{i}"
                    )
                with ec_victima:
                    _eh_victima_val = hecho.get("victima_situacion", "Seleccione...")
                    eh_victima_situacion = st.selectbox(
                        "VÍCTIMA DE LA SITUACIÓN HECHO DE RIESGO",
                        _VICTIMAS_SITUACION_HECHO,
                        index=_VICTIMAS_SITUACION_HECHO.index(_eh_victima_val) if _eh_victima_val in _VICTIMAS_SITUACION_HECHO else 0,
                        key=f"eh_victima_{tipo}_{i}"
                    )
                with ec_amenaza:
                    _eh_amenaza_val = hecho.get("tipo_amenaza", "Seleccione...")
                    eh_tipo_amenaza = st.selectbox(
                        "TIPO DE AMENAZA",
                        _TIPOS_AMENAZA,
                        index=_TIPOS_AMENAZA.index(_eh_amenaza_val) if _eh_amenaza_val in _TIPOS_AMENAZA else 0,
                        key=f"eh_tipo_amenaza_{tipo}_{i}"
                    )
                ec_tipo, ec_motivacion = st.columns(2)
                with ec_tipo:
                    eh_tipo = st.selectbox("Tipo de Hecho *", _TIPOS_HECHO,
                        index=_TIPOS_HECHO.index(hecho["tipo"]) if hecho["tipo"] in _TIPOS_HECHO else 0,
                        key=f"eh_tipo_{tipo}_{i}")
                with ec_motivacion:
                    eh_motivacion = st.text_input(
                        "MOTIVACIÓN AMENAZA HECHO DE RIESGO",
                        value=hecho.get("motivacion_amenaza", ""),
                        placeholder="Máximo en 10 palabras",
                        key=f"eh_motivacion_{tipo}_{i}"
                    )
                ec_nexo, ec_desc = st.columns(2)
                with ec_nexo:
                    _eh_nexo_opts = ["Seleccione...", "SI", "NO"]
                    _eh_nexo_val  = hecho.get("nexo_causal", "Seleccione...")
                    _eh_nexo_idx  = _eh_nexo_opts.index(_eh_nexo_val) if _eh_nexo_val in _eh_nexo_opts else 0
                    eh_nexo_causal = st.selectbox(
                        "NEXO CAUSAL",
                        _eh_nexo_opts,
                        index=_eh_nexo_idx,
                        key=f"eh_nexo_{tipo}_{i}"
                    )
                with ec_desc:
                    eh_desc = st.text_area("Descripción", value=hecho["descripcion"], height=122, key=f"eh_desc_{tipo}_{i}")
                col_save, col_cancel = st.columns(2)
                with col_save:
                    if st.button("💾 Guardar cambios", key=f"eh_save_{tipo}_{i}", type="primary", use_container_width=True):
                        err_e = []
                        if eh_tipo == "Seleccione...": err_e.append("Selecciona el tipo de hecho")
                        if err_e:
                            for e in err_e: st.error(f"• {e}")
                        else:
                            _fecha_eh = ""
                            if eh_anio is not None and eh_mes is not None and eh_dia is not None:
                                try:
                                    _fecha_eh = f"{int(eh_anio):04d}-{int(eh_mes):02d}-{int(eh_dia):02d}"
                                except Exception:
                                    _fecha_eh = ""
                            st.session_state.hechos[i] = {
                                "tipo": eh_tipo, "fecha": _fecha_eh,
                                "departamento": eh_departamento if eh_departamento != "Seleccione..." else "",
                                "municipio": eh_municipio if eh_municipio != "Seleccione..." else "",
                                "tipo_actor": eh_tipo_actor if eh_tipo_actor != "Seleccione..." else "",
                                "actor_generador": eh_actor_generador.strip(),
                                "medio": eh_medio if eh_medio != "Seleccione..." else "",
                                "victima_situacion": eh_victima_situacion if eh_victima_situacion != "Seleccione..." else "",
                                "tipo_amenaza": eh_tipo_amenaza if eh_tipo_amenaza != "Seleccione..." else "",
                                "motivacion_amenaza": eh_motivacion.strip(),
                                "nexo_causal": eh_nexo_causal if eh_nexo_causal != "Seleccione..." else "",
                                "descripcion": eh_desc.strip()
                            }
                            st.session_state[_edit_hecho_key] = None
                            st.rerun()
                with col_cancel:
                    if st.button("✖ Cancelar", key=f"eh_cancel_{tipo}_{i}", type="secondary", use_container_width=True):
                        st.session_state[_edit_hecho_key] = None
                        st.rerun()
            else:
                # ── Modo lectura ──────────────────────────────────────────────
                col_tit, col_edit, col_del = st.columns([4, 1, 1])
                with col_tit: st.markdown(f"**Hecho #{i+1} — {hecho['tipo']}**")
                with col_edit:
                    if st.button("✏️", key=f"edit_h_{tipo}_{i}", help="Editar este hecho"):
                        st.session_state[_edit_hecho_key] = i
                        st.rerun()
                with col_del:
                    if st.button("🗑️", key=f"del_{tipo}_{i}", help="Eliminar este hecho"):
                        st.session_state.hechos.pop(i)
                        st.session_state[_edit_hecho_key] = None
                        st.rerun()
                c1, c2 = st.columns(2)
                with c1:
                    st.write(f"📅 **Fecha:** {hecho['fecha']}")
                    st.write(f"🗺️ **Departamento:** {hecho.get('departamento', '')}")
                    st.write(f"🏙️ **Municipio:** {hecho.get('municipio', '')}")
                    st.write(f"💬 **Motivación Amenaza:** {hecho.get('motivacion_amenaza', '')}")
                    st.write(f"🔗 **Nexo Causal:** {hecho.get('nexo_causal', '')}")
                with c2:
                    st.write(f"⚡ **Tipo Actor:** {hecho.get('tipo_actor', '')}")
                    st.write(f"🔫 **Actor Generador:** {hecho.get('actor_generador', '')}")
                    st.write(f"📡 **Medio:** {hecho.get('medio', '')}")
                    st.write(f"🎯 **Víctima Situación:** {hecho.get('victima_situacion', '')}")
                    st.write(f"⚠️ **Tipo Amenaza:** {hecho.get('tipo_amenaza', '')}")
                st.write(f"📄 **Descripción:** {hecho['descripcion']}")

    with st.expander("➕ Agregar hecho de riesgo", expanded=len(st.session_state.hechos) == 0):
        _hf_anio_key = f"hecho_anio_{tipo}"
        _hf_mes_key  = f"hecho_mes_{tipo}"
        _hf_dia_key  = f"hecho_dia_{tipo}"
        col_hf_anio, col_hf_mes, col_hf_dia = st.columns(3)
        with col_hf_anio:
            hecho_anio = st.number_input(
                "AÑO DEL HECHO", min_value=1900, max_value=2099,
                value=None, step=1, key=_hf_anio_key
            )
        with col_hf_mes:
            hecho_mes = st.number_input(
                "MES DEL HECHO", min_value=1, max_value=12,
                value=None, step=1, key=_hf_mes_key
            )
        _max_dia_hf = 31
        if hecho_anio is not None and hecho_mes is not None:
            try:
                _max_dia_hf = calendar.monthrange(int(hecho_anio), int(hecho_mes))[1]
                _dia_cur_hf = st.session_state.get(_hf_dia_key)
                if _dia_cur_hf is not None and _dia_cur_hf > _max_dia_hf:
                    st.session_state[_hf_dia_key] = _max_dia_hf
            except Exception:
                _max_dia_hf = 31
        with col_hf_dia:
            hecho_dia = st.number_input(
                "DÍA DEL HECHO", min_value=1, max_value=_max_dia_hf,
                value=None, step=1, key=_hf_dia_key
            )
        col_hf_dep, col_hf_mun = st.columns(2)
        with col_hf_dep:
            hecho_departamento = st.selectbox(
                "DEPARTAMENTO DEL HECHO",
                ["Seleccione..."] + list(_MUNICIPIOS.keys()),
                key=f"hf_departamento_{tipo}"
            )
        with col_hf_mun:
            hecho_municipio = st.selectbox(
                "MUNICIPIO DEL HECHO",
                _MUNICIPIOS.get(hecho_departamento, ["Seleccione..."]),
                key=f"hf_municipio_{tipo}"
            )
        col_hf_tipo_actor, col_hf_actor_gen = st.columns(2)
        with col_hf_tipo_actor:
            hecho_tipo_actor = st.selectbox(
                "TIPO ACTOR GENERADOR HECHO DE RIESGO",
                ["Seleccione..."] + _TIPOS_ACTOR_GENERADOR,
                key=f"hf_tipo_actor_{tipo}"
            )
        with col_hf_actor_gen:
            hecho_actor_generador = st.text_input(
                "ACTOR GENERADOR HECHO RIESGO",
                key=f"hf_actor_gen_{tipo}"
            )
        col_hf_medio, col_hf_victima, col_hf_amenaza = st.columns(3)
        with col_hf_medio:
            hecho_medio = st.selectbox(
                "MEDIO HECHO DE RIESGO",
                _MEDIOS_HECHO,
                key=f"hf_medio_{tipo}"
            )
        with col_hf_victima:
            hecho_victima_situacion = st.selectbox(
                "VÍCTIMA DE LA SITUACIÓN HECHO DE RIESGO",
                _VICTIMAS_SITUACION_HECHO,
                key=f"hf_victima_{tipo}"
            )
        with col_hf_amenaza:
            hecho_tipo_amenaza = st.selectbox(
                "TIPO DE AMENAZA",
                _TIPOS_AMENAZA,
                key=f"hf_tipo_amenaza_{tipo}"
            )
        col_tipo, col_motivacion = st.columns(2)
        with col_tipo:
            tipo_hecho = st.selectbox("Tipo de Hecho *", _TIPOS_HECHO,
                key=f"hf_tipo_{tipo}")
        with col_motivacion:
            motivacion_hecho = st.text_input(
                "MOTIVACIÓN AMENAZA HECHO DE RIESGO",
                placeholder="Máximo en 10 palabras",
                key=f"hf_motivacion_{tipo}"
            )
        col_nexo, col_desc = st.columns(2)
        with col_nexo:
            nexo_causal_hecho = st.selectbox(
                "NEXO CAUSAL",
                ["Seleccione...", "SI", "NO"],
                key=f"hf_nexo_{tipo}"
            )
        with col_desc:
            descripcion_hecho = st.text_area("Descripción",
                                             placeholder="Describe brevemente el hecho...", height=122,
                                             key=f"hf_desc_{tipo}")
        st.markdown("")
        if st.button("➕ Agregar este hecho", use_container_width=True, key=f"btn_add_hecho_{tipo}", type="secondary"):
            err_h = []
            if tipo_hecho == "Seleccione...": err_h.append("Selecciona el tipo de hecho")
            if err_h:
                for e in err_h: st.error(f"• {e}")
            else:
                _fecha_hf = ""
                if hecho_anio is not None and hecho_mes is not None and hecho_dia is not None:
                    try:
                        _fecha_hf = f"{int(hecho_anio):04d}-{int(hecho_mes):02d}-{int(hecho_dia):02d}"
                    except Exception:
                        _fecha_hf = ""
                st.session_state.hechos.append({
                    "tipo": tipo_hecho, "fecha": _fecha_hf,
                    "departamento": hecho_departamento if hecho_departamento != "Seleccione..." else "",
                    "municipio": hecho_municipio if hecho_municipio != "Seleccione..." else "",
                    "tipo_actor": hecho_tipo_actor if hecho_tipo_actor != "Seleccione..." else "",
                    "actor_generador": hecho_actor_generador.strip(),
                    "medio": hecho_medio if hecho_medio != "Seleccione..." else "",
                    "victima_situacion": hecho_victima_situacion if hecho_victima_situacion != "Seleccione..." else "",
                    "tipo_amenaza": hecho_tipo_amenaza if hecho_tipo_amenaza != "Seleccione..." else "",
                    "motivacion_amenaza": motivacion_hecho.strip(),
                    "nexo_causal": nexo_causal_hecho if nexo_causal_hecho != "Seleccione..." else "",
                    "descripcion": descripcion_hecho.strip()
                })
                st.success("✅ Hecho agregado"); st.rerun()

    # ── Verificaciones ────────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("✅ Verificaciones")
    st.caption("Opcional. Agrega una o varias verificaciones asociadas a este caso.")

    _edit_ver_key = f"editando_verificacion_{tipo}"

    for i, ver in enumerate(st.session_state.verificaciones):
        with st.container(border=True):
            if st.session_state.get(_edit_ver_key) == i:
                # ── Modo edición ──────────────────────────────────────────────
                st.markdown(f"**✏️ Editando Verificación #{i+1}**")
                # Fila 1: Fuente de verificación
                _ev_fuente_val = ver.get("fuente", "Seleccione...")
                _ev_fuente_idx = _FUENTES_VERIFICACION.index(_ev_fuente_val) if _ev_fuente_val in _FUENTES_VERIFICACION else 0
                ev_fuente = st.selectbox(
                    "FUENTE DE VERIFICACIÓN",
                    _FUENTES_VERIFICACION,
                    index=_ev_fuente_idx,
                    key=f"ev_fuente_{tipo}_{i}"
                )
                # Fila 2: Nombre fuente
                ev_nombre_fuente = st.text_input(
                    "SEÑALAR NOMBRE COMPLETO FUENTE DE VERIFICACIÓN",
                    value=ver.get("nombre_fuente", ""),
                    key=f"ev_nombre_{tipo}_{i}"
                )
                # Fila 3: Verificación Hechos de Riesgo | Motivación Amenaza
                ev_col1, ev_col2 = st.columns(2)
                with ev_col1:
                    _ev_vhr_val = ver.get("v_hechos_riesgo", "Seleccione...")
                    ev_v_hechos = st.selectbox(
                        "VERIFICACIÓN HECHOS DE RIESGO",
                        _VER_OPCIONES,
                        index=_VER_OPCIONES.index(_ev_vhr_val) if _ev_vhr_val in _VER_OPCIONES else 0,
                        key=f"ev_vhr_{tipo}_{i}"
                    )
                with ev_col2:
                    _ev_vma_val = ver.get("v_motivacion_amenaza", "Seleccione...")
                    ev_v_motivacion = st.selectbox(
                        "VERIFICACIÓN MOTIVACIÓN AMENAZA",
                        _VER_OPCIONES,
                        index=_VER_OPCIONES.index(_ev_vma_val) if _ev_vma_val in _VER_OPCIONES else 0,
                        key=f"ev_vma_{tipo}_{i}"
                    )
                # Subcampos condicionales de Verificación Hechos de Riesgo
                if ev_v_hechos == "SI":
                    ev_lugar_col, ev_actor_col = st.columns(2)
                    with ev_lugar_col:
                        _ev_vlhr_val = ver.get("v_lugar_hechos", "Seleccione...")
                        ev_v_lugar = st.selectbox(
                            "V. LUGAR HECHOS DE RIESGO",
                            _VER_OPCIONES,
                            index=_VER_OPCIONES.index(_ev_vlhr_val) if _ev_vlhr_val in _VER_OPCIONES else 0,
                            key=f"ev_vlhr_{tipo}_{i}"
                        )
                    with ev_actor_col:
                        _ev_vahr_val = ver.get("v_actor_hechos", "Seleccione...")
                        ev_v_actor = st.selectbox(
                            "V. ACTOR HECHOS DE RIESGO",
                            _VER_OPCIONES,
                            index=_VER_OPCIONES.index(_ev_vahr_val) if _ev_vahr_val in _VER_OPCIONES else 0,
                            key=f"ev_vahr_{tipo}_{i}"
                        )
                else:
                    ev_v_lugar = ""
                    ev_v_actor = ""
                # Fila 4: Verificación Perfil Antiguo | Verificación Perfil Actual
                ev_col3, ev_col4 = st.columns(2)
                with ev_col3:
                    _ev_vpa_val = ver.get("v_perfil_antiguo", "Seleccione...")
                    ev_v_perfil_antiguo = st.selectbox(
                        "VERIFICACIÓN PERFIL ANTIGUO",
                        _VER_OPCIONES,
                        index=_VER_OPCIONES.index(_ev_vpa_val) if _ev_vpa_val in _VER_OPCIONES else 0,
                        key=f"ev_vpa_{tipo}_{i}"
                    )
                with ev_col4:
                    _ev_vpac_val = ver.get("v_perfil_actual", "Seleccione...")
                    ev_v_perfil_actual = st.selectbox(
                        "VERIFICACIÓN PERFIL ACTUAL",
                        _VER_OPCIONES,
                        index=_VER_OPCIONES.index(_ev_vpac_val) if _ev_vpac_val in _VER_OPCIONES else 0,
                        key=f"ev_vpac_{tipo}_{i}"
                    )
                # Subcampos condicionales de Verificación Perfil Antiguo
                if ev_v_perfil_antiguo == "SI":
                    ev_pa_col1, ev_pa_col2, ev_pa_col3 = st.columns(3)
                    with ev_pa_col1:
                        _ev_vmp_val = ver.get("v_modo_participacion", "Seleccione...")
                        ev_v_modo_participacion = st.selectbox(
                            "V. MODO DE PARTICIPACIÓN",
                            _VER_OPCIONES,
                            index=_VER_OPCIONES.index(_ev_vmp_val) if _ev_vmp_val in _VER_OPCIONES else 0,
                            key=f"ev_vmp_{tipo}_{i}"
                        )
                    with ev_pa_col2:
                        _ev_vrpa_val = ver.get("v_rol_perfil_antiguo", "Seleccione...")
                        ev_v_rol_perfil_antiguo = st.selectbox(
                            "V. ROL - PERFIL ANTIGUO",
                            _VER_OPCIONES,
                            index=_VER_OPCIONES.index(_ev_vrpa_val) if _ev_vrpa_val in _VER_OPCIONES else 0,
                            key=f"ev_vrpa_{tipo}_{i}"
                        )
                    with ev_pa_col3:
                        _ev_vfc_val = ver.get("v_frente_columna", "Seleccione...")
                        ev_v_frente_columna = st.selectbox(
                            "V. FRENTE/COMPAÑÍA/COLUMNA",
                            _VER_OPCIONES,
                            index=_VER_OPCIONES.index(_ev_vfc_val) if _ev_vfc_val in _VER_OPCIONES else 0,
                            key=f"ev_vfc_{tipo}_{i}"
                        )
                else:
                    ev_v_modo_participacion = ""
                    ev_v_rol_perfil_antiguo = ""
                    ev_v_frente_columna = ""
                # Subcampos condicionales de Verificación Perfil Actual
                if ev_v_perfil_actual == "SI":
                    ev_pac_col1, ev_pac_col2 = st.columns(2)
                    with ev_pac_col1:
                        _ev_vorg_val = ver.get("v_organizacion", "Seleccione...")
                        ev_v_organizacion = st.selectbox(
                            "V. ORGANIZACIÓN",
                            _VER_OPCIONES,
                            index=_VER_OPCIONES.index(_ev_vorg_val) if _ev_vorg_val in _VER_OPCIONES else 0,
                            key=f"ev_vorg_{tipo}_{i}"
                        )
                    with ev_pac_col2:
                        _ev_vrol_val = ver.get("v_rol_perfil_actual", "Seleccione...")
                        ev_v_rol_perfil_actual = st.selectbox(
                            "V. ROL",
                            _VER_OPCIONES,
                            index=_VER_OPCIONES.index(_ev_vrol_val) if _ev_vrol_val in _VER_OPCIONES else 0,
                            key=f"ev_vrol_{tipo}_{i}"
                        )
                else:
                    ev_v_organizacion = ""
                    ev_v_rol_perfil_actual = ""
                col_sv, col_cv = st.columns(2)
                with col_sv:
                    if st.button("💾 Guardar cambios", key=f"ev_save_{tipo}_{i}", type="primary", use_container_width=True):
                        st.session_state.verificaciones[i] = {
                            "fuente": ev_fuente if ev_fuente != "Seleccione..." else "",
                            "nombre_fuente": ev_nombre_fuente.strip(),
                            "v_hechos_riesgo": ev_v_hechos if ev_v_hechos != "Seleccione..." else "",
                            "v_lugar_hechos": ev_v_lugar if ev_v_lugar != "Seleccione..." else "",
                            "v_actor_hechos": ev_v_actor if ev_v_actor != "Seleccione..." else "",
                            "v_motivacion_amenaza": ev_v_motivacion if ev_v_motivacion != "Seleccione..." else "",
                            "v_perfil_antiguo": ev_v_perfil_antiguo if ev_v_perfil_antiguo != "Seleccione..." else "",
                            "v_modo_participacion": ev_v_modo_participacion if ev_v_modo_participacion != "Seleccione..." else "",
                            "v_rol_perfil_antiguo": ev_v_rol_perfil_antiguo if ev_v_rol_perfil_antiguo != "Seleccione..." else "",
                            "v_frente_columna": ev_v_frente_columna if ev_v_frente_columna != "Seleccione..." else "",
                            "v_perfil_actual": ev_v_perfil_actual if ev_v_perfil_actual != "Seleccione..." else "",
                            "v_organizacion": ev_v_organizacion if ev_v_organizacion != "Seleccione..." else "",
                            "v_rol_perfil_actual": ev_v_rol_perfil_actual if ev_v_rol_perfil_actual != "Seleccione..." else "",
                        }
                        st.session_state[_edit_ver_key] = None
                        st.rerun()
                with col_cv:
                    if st.button("✖ Cancelar", key=f"ev_cancel_{tipo}_{i}", type="secondary", use_container_width=True):
                        st.session_state[_edit_ver_key] = None
                        st.rerun()
            else:
                # ── Modo lectura ──────────────────────────────────────────────
                col_vt, col_ve, col_vd = st.columns([4, 1, 1])
                with col_vt: st.markdown(f"**Verificación #{i+1} — {ver.get('fuente', '')}**")
                with col_ve:
                    if st.button("✏️", key=f"edit_v_{tipo}_{i}", help="Editar"):
                        st.session_state[_edit_ver_key] = i
                        st.rerun()
                with col_vd:
                    if st.button("🗑️", key=f"del_v_{tipo}_{i}", help="Eliminar"):
                        st.session_state.verificaciones.pop(i)
                        st.session_state[_edit_ver_key] = None
                        st.rerun()
                vc1, vc2 = st.columns(2)
                with vc1:
                    st.write(f"🏢 **Fuente:** {ver.get('fuente', '')}")
                    st.write(f"👤 **Nombre Fuente:** {ver.get('nombre_fuente', '')}")
                    st.write(f"⚠️ **V. Hechos Riesgo:** {ver.get('v_hechos_riesgo', '')}")
                    if ver.get("v_hechos_riesgo") == "SI":
                        st.write(f"📍 **V. Lugar Hechos Riesgo:** {ver.get('v_lugar_hechos', '')}")
                        st.write(f"🎭 **V. Actor Hechos Riesgo:** {ver.get('v_actor_hechos', '')}")
                    st.write(f"💬 **V. Motivación Amenaza:** {ver.get('v_motivacion_amenaza', '')}")
                with vc2:
                    st.write(f"📋 **V. Perfil Antiguo:** {ver.get('v_perfil_antiguo', '')}")
                    if ver.get("v_perfil_antiguo") == "SI":
                        st.write(f"🤝 **V. Modo Participación:** {ver.get('v_modo_participacion', '')}")
                        st.write(f"🏷️ **V. Rol Perfil Antiguo:** {ver.get('v_rol_perfil_antiguo', '')}")
                        st.write(f"🪖 **V. Frente/Compañía/Columna:** {ver.get('v_frente_columna', '')}")
                    st.write(f"🎯 **V. Perfil Actual:** {ver.get('v_perfil_actual', '')}")
                    if ver.get("v_perfil_actual") == "SI":
                        st.write(f"🏢 **V. Organización:** {ver.get('v_organizacion', '')}")
                        st.write(f"🏷️ **V. Rol:** {ver.get('v_rol_perfil_actual', '')}")

    with st.expander("➕ Agregar verificación", expanded=len(st.session_state.verificaciones) == 0):
        # Fila 1
        nv_fuente = st.selectbox(
            "FUENTE DE VERIFICACIÓN",
            _FUENTES_VERIFICACION,
            key=f"nv_fuente_{tipo}"
        )
        # Fila 2
        nv_nombre_fuente = st.text_input(
            "SEÑALAR NOMBRE COMPLETO FUENTE DE VERIFICACIÓN",
            key=f"nv_nombre_{tipo}"
        )
        # Fila 3
        nv_col1, nv_col2 = st.columns(2)
        with nv_col1:
            nv_v_hechos = st.selectbox(
                "VERIFICACIÓN HECHOS DE RIESGO",
                _VER_OPCIONES,
                key=f"nv_vhr_{tipo}"
            )
        with nv_col2:
            nv_v_motivacion = st.selectbox(
                "VERIFICACIÓN MOTIVACIÓN AMENAZA",
                _VER_OPCIONES,
                key=f"nv_vma_{tipo}"
            )
        # Subcampos condicionales de Verificación Hechos de Riesgo
        if nv_v_hechos == "SI":
            nv_lugar_col, nv_actor_col = st.columns(2)
            with nv_lugar_col:
                nv_v_lugar = st.selectbox(
                    "V. LUGAR HECHOS DE RIESGO",
                    _VER_OPCIONES,
                    key=f"nv_vlhr_{tipo}"
                )
            with nv_actor_col:
                nv_v_actor = st.selectbox(
                    "V. ACTOR HECHOS DE RIESGO",
                    _VER_OPCIONES,
                    key=f"nv_vahr_{tipo}"
                )
        else:
            nv_v_lugar = ""
            nv_v_actor = ""
        # Fila 4
        nv_col3, nv_col4 = st.columns(2)
        with nv_col3:
            nv_v_perfil_antiguo = st.selectbox(
                "VERIFICACIÓN PERFIL ANTIGUO",
                _VER_OPCIONES,
                key=f"nv_vpa_{tipo}"
            )
        with nv_col4:
            nv_v_perfil_actual = st.selectbox(
                "VERIFICACIÓN PERFIL ACTUAL",
                _VER_OPCIONES,
                key=f"nv_vpac_{tipo}"
            )
        # Subcampos condicionales de Verificación Perfil Antiguo
        if nv_v_perfil_antiguo == "SI":
            nv_pa_col1, nv_pa_col2, nv_pa_col3 = st.columns(3)
            with nv_pa_col1:
                nv_v_modo_participacion = st.selectbox(
                    "V. MODO DE PARTICIPACIÓN",
                    _VER_OPCIONES,
                    key=f"nv_vmp_{tipo}"
                )
            with nv_pa_col2:
                nv_v_rol_perfil_antiguo = st.selectbox(
                    "V. ROL - PERFIL ANTIGUO",
                    _VER_OPCIONES,
                    key=f"nv_vrpa_{tipo}"
                )
            with nv_pa_col3:
                nv_v_frente_columna = st.selectbox(
                    "V. FRENTE/COMPAÑÍA/COLUMNA",
                    _VER_OPCIONES,
                    key=f"nv_vfc_{tipo}"
                )
        else:
            nv_v_modo_participacion = ""
            nv_v_rol_perfil_antiguo = ""
            nv_v_frente_columna = ""
        # Subcampos condicionales de Verificación Perfil Actual
        if nv_v_perfil_actual == "SI":
            nv_pac_col1, nv_pac_col2 = st.columns(2)
            with nv_pac_col1:
                nv_v_organizacion = st.selectbox(
                    "V. ORGANIZACIÓN",
                    _VER_OPCIONES,
                    key=f"nv_vorg_{tipo}"
                )
            with nv_pac_col2:
                nv_v_rol_perfil_actual = st.selectbox(
                    "V. ROL",
                    _VER_OPCIONES,
                    key=f"nv_vrol_{tipo}"
                )
        else:
            nv_v_organizacion = ""
            nv_v_rol_perfil_actual = ""
        st.markdown("")
        if st.button("➕ Agregar esta verificación", use_container_width=True, key=f"btn_add_ver_{tipo}", type="secondary"):
            st.session_state.verificaciones.append({
                "fuente": nv_fuente if nv_fuente != "Seleccione..." else "",
                "nombre_fuente": nv_nombre_fuente.strip(),
                "v_hechos_riesgo": nv_v_hechos if nv_v_hechos != "Seleccione..." else "",
                "v_lugar_hechos": nv_v_lugar if nv_v_lugar != "Seleccione..." else "",
                "v_actor_hechos": nv_v_actor if nv_v_actor != "Seleccione..." else "",
                "v_motivacion_amenaza": nv_v_motivacion if nv_v_motivacion != "Seleccione..." else "",
                "v_perfil_antiguo": nv_v_perfil_antiguo if nv_v_perfil_antiguo != "Seleccione..." else "",
                "v_modo_participacion": nv_v_modo_participacion if nv_v_modo_participacion != "Seleccione..." else "",
                "v_rol_perfil_antiguo": nv_v_rol_perfil_antiguo if nv_v_rol_perfil_antiguo != "Seleccione..." else "",
                "v_frente_columna": nv_v_frente_columna if nv_v_frente_columna != "Seleccione..." else "",
                "v_perfil_actual": nv_v_perfil_actual if nv_v_perfil_actual != "Seleccione..." else "",
                "v_organizacion": nv_v_organizacion if nv_v_organizacion != "Seleccione..." else "",
                "v_rol_perfil_actual": nv_v_rol_perfil_actual if nv_v_rol_perfil_actual != "Seleccione..." else "",
            })
            st.success("✅ Verificación agregada"); st.rerun()

    # ── Impacto Consecuencial ─────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("📊 Impacto Consecuencial")

    st.markdown("**IMPACTO EN LA ESFERA ECONÓMICA**")
    imp_eco_col1, imp_eco_col2 = st.columns(2)
    with imp_eco_col1:
        imp_eco_dependencia = st.selectbox(
            "DEPENDENCIA EN PROGRAMAS DE SUBSIDIO DEL ESTADO",
            _IMPACTO_SI_NR,
            key=f"imp_eco_dependencia_{tipo}",
            index=_IMPACTO_SI_NR.index(st.session_state.get(f"imp_eco_dependencia_{tipo}", "Seleccione..."))
                if st.session_state.get(f"imp_eco_dependencia_{tipo}", "Seleccione...") in _IMPACTO_SI_NR else 0
        )
        imp_eco_empleos = st.selectbox(
            "ACCESO RESTRINGIDO A EMPLEOS FORMALES",
            _IMPACTO_SI_NR,
            key=f"imp_eco_empleos_{tipo}",
            index=_IMPACTO_SI_NR.index(st.session_state.get(f"imp_eco_empleos_{tipo}", "Seleccione..."))
                if st.session_state.get(f"imp_eco_empleos_{tipo}", "Seleccione...") in _IMPACTO_SI_NR else 0
        )
        imp_eco_bienes = st.selectbox(
            "ACCESO A SERVICIOS Y BIENES O ENSERES DE PRIMERA NECESIDAD",
            _IMPACTO_SI_NR,
            key=f"imp_eco_bienes_{tipo}",
            index=_IMPACTO_SI_NR.index(st.session_state.get(f"imp_eco_bienes_{tipo}", "Seleccione..."))
                if st.session_state.get(f"imp_eco_bienes_{tipo}", "Seleccione...") in _IMPACTO_SI_NR else 0
        )
    with imp_eco_col2:
        imp_eco_iniciativas = st.selectbox(
            "PÉRDIDA DE INICIATIVAS PRODUCTIVAS",
            _IMPACTO_SI_NR,
            key=f"imp_eco_iniciativas_{tipo}",
            index=_IMPACTO_SI_NR.index(st.session_state.get(f"imp_eco_iniciativas_{tipo}", "Seleccione..."))
                if st.session_state.get(f"imp_eco_iniciativas_{tipo}", "Seleccione...") in _IMPACTO_SI_NR else 0
        )
        imp_eco_ilicita = st.selectbox(
            "INSERCIÓN EN PROCESOS DE ECONOMÍAS ILÍCITAS O EMPLEOS INFORMALES PRECARIZADOS",
            _IMPACTO_SI_NR,
            key=f"imp_eco_ilicita_{tipo}",
            index=_IMPACTO_SI_NR.index(st.session_state.get(f"imp_eco_ilicita_{tipo}", "Seleccione..."))
                if st.session_state.get(f"imp_eco_ilicita_{tipo}", "Seleccione...") in _IMPACTO_SI_NR else 0
        )

    st.markdown("**IMPACTO EN LA ESFERA SOCIAL**")
    imp_soc_col1, imp_soc_col2 = st.columns(2)
    with imp_soc_col1:
        imp_soc_tejido = st.selectbox(
            "RUPTURA DEL TEJIDO SOCIAL",
            _IMPACTO_SI_NR,
            key=f"imp_soc_tejido_{tipo}",
            index=_IMPACTO_SI_NR.index(st.session_state.get(f"imp_soc_tejido_{tipo}", "Seleccione..."))
                if st.session_state.get(f"imp_soc_tejido_{tipo}", "Seleccione...") in _IMPACTO_SI_NR else 0
        )
        imp_soc_traslado = st.selectbox(
            "TRASLADO DE FACTORES DE VIOLENCIA DE UN TERRITORIO A OTRO",
            _IMPACTO_SI_NR,
            key=f"imp_soc_traslado_{tipo}",
            index=_IMPACTO_SI_NR.index(st.session_state.get(f"imp_soc_traslado_{tipo}", "Seleccione..."))
                if st.session_state.get(f"imp_soc_traslado_{tipo}", "Seleccione...") in _IMPACTO_SI_NR else 0
        )
        imp_soc_movilidad = st.selectbox(
            "RESTRICCIÓN DE MOVILIDAD",
            _IMPACTO_SI_NR,
            key=f"imp_soc_movilidad_{tipo}",
            index=_IMPACTO_SI_NR.index(st.session_state.get(f"imp_soc_movilidad_{tipo}", "Seleccione..."))
                if st.session_state.get(f"imp_soc_movilidad_{tipo}", "Seleccione...") in _IMPACTO_SI_NR else 0
        )
        imp_soc_normalizacion = st.selectbox(
            "NORMALIZACIÓN DE LA VIOLENCIA",
            _IMPACTO_SI_NR,
            key=f"imp_soc_normalizacion_{tipo}",
            index=_IMPACTO_SI_NR.index(st.session_state.get(f"imp_soc_normalizacion_{tipo}", "Seleccione..."))
                if st.session_state.get(f"imp_soc_normalizacion_{tipo}", "Seleccione...") in _IMPACTO_SI_NR else 0
        )
    with imp_soc_col2:
        imp_soc_redes = st.selectbox(
            "PÉRDIDA DE REDES DE APOYO",
            _IMPACTO_SI_NR,
            key=f"imp_soc_redes_{tipo}",
            index=_IMPACTO_SI_NR.index(st.session_state.get(f"imp_soc_redes_{tipo}", "Seleccione..."))
                if st.session_state.get(f"imp_soc_redes_{tipo}", "Seleccione...") in _IMPACTO_SI_NR else 0
        )
        imp_soc_confinamiento = st.selectbox(
            "CONFINAMIENTO O AUTO-CONFINAMIENTO",
            _IMPACTO_SI_NR,
            key=f"imp_soc_confinamiento_{tipo}",
            index=_IMPACTO_SI_NR.index(st.session_state.get(f"imp_soc_confinamiento_{tipo}", "Seleccione..."))
                if st.session_state.get(f"imp_soc_confinamiento_{tipo}", "Seleccione...") in _IMPACTO_SI_NR else 0
        )
        imp_soc_desarraigo = st.selectbox(
            "DESARRAIGO CULTURAL Y TERRITORIAL",
            _IMPACTO_SI_NR,
            key=f"imp_soc_desarraigo_{tipo}",
            index=_IMPACTO_SI_NR.index(st.session_state.get(f"imp_soc_desarraigo_{tipo}", "Seleccione..."))
                if st.session_state.get(f"imp_soc_desarraigo_{tipo}", "Seleccione...") in _IMPACTO_SI_NR else 0
        )
        imp_soc_libertad = st.selectbox(
            "AFECTACIÓN AL GOCE DEL DERECHO A LA LIBERTAD Y SEGURIDAD PERSONAL",
            _IMPACTO_SI_NR,
            key=f"imp_soc_libertad_{tipo}",
            index=_IMPACTO_SI_NR.index(st.session_state.get(f"imp_soc_libertad_{tipo}", "Seleccione..."))
                if st.session_state.get(f"imp_soc_libertad_{tipo}", "Seleccione...") in _IMPACTO_SI_NR else 0
        )

    st.markdown("**IMPACTO EN LA ESFERA POLÍTICO-INSTITUCIONAL**")
    imp_pol_col1, imp_pol_col2 = st.columns(2)
    with imp_pol_col1:
        imp_pol_participacion = st.selectbox(
            "RESTRICCIÓN EN LA PARTICIPACIÓN POLÍTICA",
            _IMPACTO_SI_NR,
            key=f"imp_pol_participacion_{tipo}",
            index=_IMPACTO_SI_NR.index(st.session_state.get(f"imp_pol_participacion_{tipo}", "Seleccione..."))
                if st.session_state.get(f"imp_pol_participacion_{tipo}", "Seleccione...") in _IMPACTO_SI_NR else 0
        )
        imp_pol_oferta = st.selectbox(
            "EXPOSICIÓN POR FALENCIAS EN LA IMPLEMENTACIÓN DE LA OFERTA INSTITUCIONAL",
            _IMPACTO_SI_NR,
            key=f"imp_pol_oferta_{tipo}",
            index=_IMPACTO_SI_NR.index(st.session_state.get(f"imp_pol_oferta_{tipo}", "Seleccione..."))
                if st.session_state.get(f"imp_pol_oferta_{tipo}", "Seleccione...") in _IMPACTO_SI_NR else 0
        )
        imp_pol_estigmatizacion = st.selectbox(
            "ESTIGMATIZACIÓN",
            _IMPACTO_SI_NR,
            key=f"imp_pol_estigmatizacion_{tipo}",
            index=_IMPACTO_SI_NR.index(st.session_state.get(f"imp_pol_estigmatizacion_{tipo}", "Seleccione..."))
                if st.session_state.get(f"imp_pol_estigmatizacion_{tipo}", "Seleccione...") in _IMPACTO_SI_NR else 0
        )
    with imp_pol_col2:
        imp_pol_liderazgos = st.selectbox(
            "DESARTICULACIÓN EN LOS LIDERAZGOS",
            _IMPACTO_SI_NR,
            key=f"imp_pol_liderazgos_{tipo}",
            index=_IMPACTO_SI_NR.index(st.session_state.get(f"imp_pol_liderazgos_{tipo}", "Seleccione..."))
                if st.session_state.get(f"imp_pol_liderazgos_{tipo}", "Seleccione...") in _IMPACTO_SI_NR else 0
        )
        imp_pol_derechos = st.selectbox(
            "AFECTACIÓN EN EL GOCE DE SUS DERECHOS POLÍTICOS",
            _IMPACTO_SI_NR,
            key=f"imp_pol_derechos_{tipo}",
            index=_IMPACTO_SI_NR.index(st.session_state.get(f"imp_pol_derechos_{tipo}", "Seleccione..."))
                if st.session_state.get(f"imp_pol_derechos_{tipo}", "Seleccione...") in _IMPACTO_SI_NR else 0
        )
        imp_pol_confianza = st.selectbox(
            "PÉRDIDA DE CONFIANZA EN LAS INSTITUCIONES",
            _IMPACTO_SI_NR,
            key=f"imp_pol_confianza_{tipo}",
            index=_IMPACTO_SI_NR.index(st.session_state.get(f"imp_pol_confianza_{tipo}", "Seleccione..."))
                if st.session_state.get(f"imp_pol_confianza_{tipo}", "Seleccione...") in _IMPACTO_SI_NR else 0
        )

    st.markdown("**IMPACTO EN LA ESFERA DE LA SALUD Y EL BIENESTAR**")
    imp_sal_col1, imp_sal_col2 = st.columns(2)
    with imp_sal_col1:
        imp_sal_proyeccion = st.selectbox(
            "AFECTACIÓN A LA PROYECCIÓN PERSONAL O COLECTIVA",
            _IMPACTO_SI_NR,
            key=f"imp_sal_proyeccion_{tipo}",
            index=_IMPACTO_SI_NR.index(st.session_state.get(f"imp_sal_proyeccion_{tipo}", "Seleccione..."))
                if st.session_state.get(f"imp_sal_proyeccion_{tipo}", "Seleccione...") in _IMPACTO_SI_NR else 0
        )
        imp_sal_desescolarizacion = st.selectbox(
            "DESESCOLARIZACIÓN",
            _IMPACTO_SI_NR,
            key=f"imp_sal_desescolarizacion_{tipo}",
            index=_IMPACTO_SI_NR.index(st.session_state.get(f"imp_sal_desescolarizacion_{tipo}", "Seleccione..."))
                if st.session_state.get(f"imp_sal_desescolarizacion_{tipo}", "Seleccione...") in _IMPACTO_SI_NR else 0
        )
        imp_sal_psicosocial = st.selectbox(
            "AFECTACIÓN PSICOSOCIAL",
            _IMPACTO_SI_NR,
            key=f"imp_sal_psicosocial_{tipo}",
            index=_IMPACTO_SI_NR.index(st.session_state.get(f"imp_sal_psicosocial_{tipo}", "Seleccione..."))
                if st.session_state.get(f"imp_sal_psicosocial_{tipo}", "Seleccione...") in _IMPACTO_SI_NR else 0
        )
        imp_sal_dano_vida = st.selectbox(
            "DAÑO IRREPARABLE A LA VIDA E INTEGRIDAD PERSONAL",
            _IMPACTO_SI_NR,
            key=f"imp_sal_dano_vida_{tipo}",
            index=_IMPACTO_SI_NR.index(st.session_state.get(f"imp_sal_dano_vida_{tipo}", "Seleccione..."))
                if st.session_state.get(f"imp_sal_dano_vida_{tipo}", "Seleccione...") in _IMPACTO_SI_NR else 0
        )
    with imp_sal_col2:
        imp_sal_cuidados = st.selectbox(
            "IMPOSIBILIDAD DE ATENDER LOS CUIDADOS DOMÉSTICOS O DE PERSONAS DEPENDIENTES",
            _IMPACTO_SI_NR,
            key=f"imp_sal_cuidados_{tipo}",
            index=_IMPACTO_SI_NR.index(st.session_state.get(f"imp_sal_cuidados_{tipo}", "Seleccione..."))
                if st.session_state.get(f"imp_sal_cuidados_{tipo}", "Seleccione...") in _IMPACTO_SI_NR else 0
        )
        imp_sal_abandono = st.selectbox(
            "PROCESOS DE ABANDONO A MENORES Y/O ADULTOS MAYORES",
            _IMPACTO_SI_NR,
            key=f"imp_sal_abandono_{tipo}",
            index=_IMPACTO_SI_NR.index(st.session_state.get(f"imp_sal_abandono_{tipo}", "Seleccione..."))
                if st.session_state.get(f"imp_sal_abandono_{tipo}", "Seleccione...") in _IMPACTO_SI_NR else 0
        )
        imp_sal_discapacidad = st.selectbox(
            "DISCAPACIDAD",
            _IMPACTO_SI_NR,
            key=f"imp_sal_discapacidad_{tipo}",
            index=_IMPACTO_SI_NR.index(st.session_state.get(f"imp_sal_discapacidad_{tipo}", "Seleccione..."))
                if st.session_state.get(f"imp_sal_discapacidad_{tipo}", "Seleccione...") in _IMPACTO_SI_NR else 0
        )

    # ── Nivel de Riesgo ───────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("⚠️ Nivel de Riesgo")
    nivel_riesgo = st.selectbox(
        "Nivel de Riesgo *",
        ["Seleccione...", "EXTRAORDINARIO", "EXTREMO", "ORDINARIO"],
        key=f"caso_nivel_riesgo_{tipo}"
    )

    # ── Observaciones ─────────────────────────────────────────────────────────
    st.markdown("---")
    observaciones = st.text_area("Observaciones (Opcional)", height=80, key=f"caso_observaciones_{tipo}")

    # ── Guardar borrador ──────────────────────────────────────────────────────
    col_borrador, col_registrar = st.columns([1, 2])
    with col_borrador:
        if st.button("💾 Guardar borrador", use_container_width=True, type="secondary", key=f"btn_guardar_borrador_{tipo}"):
            datos_borrador = {
                # DATOS DE OT/TE
                f"caso_tipo_estudio_{tipo}":     st.session_state.get(f"caso_tipo_estudio_{tipo}", "Seleccione..."),
                f"caso_ot_anio_{tipo}":          st.session_state.get(f"caso_ot_anio_{tipo}", None),
                f"caso_ot_numero_{tipo}":        st.session_state.get(f"caso_ot_numero_{tipo}", None),
                f"caso_solicitante_{tipo}":      st.session_state.get(f"caso_solicitante_{tipo}", "Seleccione..."),
                f"caso_fecha_expedicion_{tipo}": st.session_state.get(f"caso_fecha_expedicion_{tipo}", None),
                f"caso_tipo_poblacion_{tipo}":   st.session_state.get(f"caso_tipo_poblacion_{tipo}", "Seleccione..."),
                **{f"subpob_{i}_{tipo}": st.session_state.get(f"subpob_{i}_{tipo}", False)
                   for i in range(len(_SUBPOBLACIONES))},
                # CARACTERÍSTICAS DEMOGRÁFICAS
                f"caso_fecha_nacimiento_{tipo}": st.session_state.get(f"caso_fecha_nacimiento_{tipo}", None),
                f"caso_sexo_{tipo}":             st.session_state.get(f"caso_sexo_{tipo}", "Seleccione..."),
                f"caso_genero_{tipo}":           st.session_state.get(f"caso_genero_{tipo}", "Seleccione..."),
                f"caso_orientacion_{tipo}":      st.session_state.get(f"caso_orientacion_{tipo}", "Seleccione..."),
                f"caso_jefatura_{tipo}":         st.session_state.get(f"caso_jefatura_{tipo}", "Seleccione..."),
                f"p_departamento_{tipo}":        st.session_state.get(f"p_departamento_{tipo}", "Seleccione..."),
                f"p_municipio_{tipo}":           st.session_state.get(f"p_municipio_{tipo}", "Seleccione..."),
                f"caso_zona_rural_{tipo}":       st.session_state.get(f"caso_zona_rural_{tipo}", "Seleccione..."),
                f"caso_zona_reserva_{tipo}":     st.session_state.get(f"caso_zona_reserva_{tipo}", "Seleccione..."),
                f"caso_nivel_riesgo_{tipo}":     st.session_state.get(f"caso_nivel_riesgo_{tipo}", "Seleccione..."),
                f"caso_observaciones_{tipo}":    st.session_state.get(f"caso_observaciones_{tipo}", ""),
                # COMPOSICIÓN NÚCLEO FAMILIAR
                f"caso_num_personas_{tipo}":     st.session_state.get(f"caso_num_personas_{tipo}", None),
                f"caso_companero_{tipo}":        st.session_state.get(f"caso_companero_{tipo}", "Seleccione..."),
                f"caso_hijos_menores_{tipo}":    st.session_state.get(f"caso_hijos_menores_{tipo}", None),
                f"caso_menores_otros_{tipo}":    st.session_state.get(f"caso_menores_otros_{tipo}", None),
                f"caso_adultos_mayores_{tipo}":  st.session_state.get(f"caso_adultos_mayores_{tipo}", None),
                f"caso_discapacidad_{tipo}":     st.session_state.get(f"caso_discapacidad_{tipo}", None),
                # FACTORES DIFERENCIALES
                f"caso_osiegd_{tipo}":              st.session_state.get(f"caso_osiegd_{tipo}", ""),
                f"caso_factor_discapacidad_{tipo}": st.session_state.get(f"caso_factor_discapacidad_{tipo}", "Seleccione..."),
                f"caso_factor_etnia_{tipo}":        st.session_state.get(f"caso_factor_etnia_{tipo}", "Seleccione..."),
                f"caso_factor_campesino_{tipo}":    st.session_state.get(f"caso_factor_campesino_{tipo}", "Seleccione..."),
                f"caso_factor_cuidador_{tipo}":     st.session_state.get(f"caso_factor_cuidador_{tipo}", "Seleccione..."),
                **{f"victima_{i}_{tipo}": st.session_state.get(f"victima_{i}_{tipo}", False)
                   for i in range(len(_VICTIMA_CONFLICTO_ARMADO))},
                **{f"lider_{i}_{tipo}": st.session_state.get(f"lider_{i}_{tipo}", False)
                   for i in range(len(_LIDER_SOCIAL_DDHH))},
                # Hechos, perfiles y antecedentes
                "hechos":           st.session_state.get("hechos", []),
                "perfiles":         st.session_state.get("perfiles", []),
                "antecedentes":     st.session_state.get("antecedentes", []),
                "perfiles_actuales": st.session_state.get("perfiles_actuales", []),
                "desplazamientos":   st.session_state.get("desplazamientos", []),
                "verificaciones":    st.session_state.get("verificaciones", []),
                f"imp_eco_dependencia_{tipo}": st.session_state.get(f"imp_eco_dependencia_{tipo}", "Seleccione..."),
                f"imp_eco_iniciativas_{tipo}": st.session_state.get(f"imp_eco_iniciativas_{tipo}", "Seleccione..."),
                f"imp_eco_empleos_{tipo}":     st.session_state.get(f"imp_eco_empleos_{tipo}", "Seleccione..."),
                f"imp_eco_ilicita_{tipo}":     st.session_state.get(f"imp_eco_ilicita_{tipo}", "Seleccione..."),
                f"imp_eco_bienes_{tipo}":      st.session_state.get(f"imp_eco_bienes_{tipo}", "Seleccione..."),
                f"imp_soc_tejido_{tipo}":       st.session_state.get(f"imp_soc_tejido_{tipo}", "Seleccione..."),
                f"imp_soc_redes_{tipo}":        st.session_state.get(f"imp_soc_redes_{tipo}", "Seleccione..."),
                f"imp_soc_traslado_{tipo}":     st.session_state.get(f"imp_soc_traslado_{tipo}", "Seleccione..."),
                f"imp_soc_confinamiento_{tipo}": st.session_state.get(f"imp_soc_confinamiento_{tipo}", "Seleccione..."),
                f"imp_soc_movilidad_{tipo}":    st.session_state.get(f"imp_soc_movilidad_{tipo}", "Seleccione..."),
                f"imp_soc_desarraigo_{tipo}":   st.session_state.get(f"imp_soc_desarraigo_{tipo}", "Seleccione..."),
                f"imp_soc_normalizacion_{tipo}": st.session_state.get(f"imp_soc_normalizacion_{tipo}", "Seleccione..."),
                f"imp_soc_libertad_{tipo}":     st.session_state.get(f"imp_soc_libertad_{tipo}", "Seleccione..."),
                f"imp_pol_participacion_{tipo}": st.session_state.get(f"imp_pol_participacion_{tipo}", "Seleccione..."),
                f"imp_pol_liderazgos_{tipo}":    st.session_state.get(f"imp_pol_liderazgos_{tipo}", "Seleccione..."),
                f"imp_pol_oferta_{tipo}":        st.session_state.get(f"imp_pol_oferta_{tipo}", "Seleccione..."),
                f"imp_pol_derechos_{tipo}":      st.session_state.get(f"imp_pol_derechos_{tipo}", "Seleccione..."),
                f"imp_pol_estigmatizacion_{tipo}": st.session_state.get(f"imp_pol_estigmatizacion_{tipo}", "Seleccione..."),
                f"imp_pol_confianza_{tipo}":     st.session_state.get(f"imp_pol_confianza_{tipo}", "Seleccione..."),
                f"imp_sal_proyeccion_{tipo}":       st.session_state.get(f"imp_sal_proyeccion_{tipo}", "Seleccione..."),
                f"imp_sal_cuidados_{tipo}":         st.session_state.get(f"imp_sal_cuidados_{tipo}", "Seleccione..."),
                f"imp_sal_desescolarizacion_{tipo}": st.session_state.get(f"imp_sal_desescolarizacion_{tipo}", "Seleccione..."),
                f"imp_sal_abandono_{tipo}":         st.session_state.get(f"imp_sal_abandono_{tipo}", "Seleccione..."),
                f"imp_sal_psicosocial_{tipo}":      st.session_state.get(f"imp_sal_psicosocial_{tipo}", "Seleccione..."),
                f"imp_sal_discapacidad_{tipo}":     st.session_state.get(f"imp_sal_discapacidad_{tipo}", "Seleccione..."),
                f"imp_sal_dano_vida_{tipo}":        st.session_state.get(f"imp_sal_dano_vida_{tipo}", "Seleccione..."),
            }
            if guardar_borrador(st.session_state.username, tipo, datos_borrador):
                st.session_state[_borrador_key] = True  # evitar que el prompt borre perfiles recién agregados
                st.success("✅ Borrador guardado. Puedes retomarlo más tarde.")
            else:
                st.error("❌ No se pudo guardar el borrador.")

    with col_registrar:
        registrar = st.button(f"✅ REGISTRAR CASO {label_badge}", use_container_width=True, type="primary", key=f"btn_registrar_{tipo}")

    if registrar:
        errores = []
        if tipo_estudio == "Seleccione...":             errores.append("Debe seleccionar el tipo de estudio")
        if not es_emergencia and ot_anio is None:       errores.append("El año de la OT es obligatorio")
        if not es_emergencia and ot_numero is None:     errores.append("El número de la OT es obligatorio")
        if es_emergencia and ot_anio is None and ot_numero is None:
            pass  # ambos opcionales en emergencia
        if fecha_expedicion_ot is None:                 errores.append("La fecha de expedición OT es obligatoria")
        if tipo_poblacion == "Seleccione...":           errores.append("Debe seleccionar el tipo de población")
        if len(subpoblacion) == 0:                       errores.append("Debe seleccionar al menos una subpoblación")
        if es_individual and fecha_nacimiento is None:       errores.append("La fecha de nacimiento es obligatoria")
        if es_individual and fecha_nacimiento is not None:
            if fecha_nacimiento.year < 1900:                errores.append("La fecha de nacimiento no puede ser anterior a 1900")
            if fecha_nacimiento > date.today():             errores.append("La fecha de nacimiento no puede ser futura")
        if es_individual and sexo == "Seleccione...":        errores.append("Debe seleccionar un sexo")
        if es_individual and genero == "Seleccione...":             errores.append("Debe seleccionar un género")
        if es_individual and orientacion_sexual == "Seleccione...": errores.append("Debe seleccionar una orientación sexual")
        if es_individual and jefatura_hogar == "Seleccione...":     errores.append("Debe seleccionar jefatura del hogar")
        if departamento == "Seleccione...":             errores.append("Debe seleccionar un departamento")
        if es_individual and zona_rural == "Seleccione...":    errores.append("Debe indicar si vive en zona rural")
        if es_individual and zona_reserva == "Seleccione...":  errores.append("Debe indicar si vive en zona de reserva campesina")
        if municipio == "Seleccione...":                errores.append("Debe seleccionar un municipio")
        if solicitante == "Seleccione...":              errores.append("Debe seleccionar una entidad solicitante")
        if nivel_riesgo == "Seleccione...":             errores.append("Debe seleccionar un nivel de riesgo")
        if es_individual and num_personas is None:       errores.append("El número de personas en el núcleo familiar es obligatorio")
        if es_individual and companero == "Seleccione...": errores.append("Debe indicar si tiene compañero(a) permanente")
        if es_individual and num_hijos_menores is None:  errores.append("El número de hijos menores de edad es obligatorio")
        if es_individual and num_menores_otros is None:  errores.append("El número de menores de edad distintos a hijos es obligatorio")
        if es_individual and num_adultos_mayores is None: errores.append("El número de adultos mayores es obligatorio")
        if es_individual and num_discapacidad is None:   errores.append("El número de personas en situación de discapacidad es obligatorio")
        if es_individual and factor_discapacidad == "Seleccione...": errores.append("Debe seleccionar el factor de discapacidad")
        if es_individual and factor_etnia == "Seleccione...":        errores.append("Debe seleccionar el factor étnico")
        if es_individual and factor_campesino == "Seleccione...":    errores.append("Debe seleccionar el factor campesino")
        if es_individual and factor_cuidador == "Seleccione...":     errores.append("Debe seleccionar el factor cuidador")

        if errores:
            st.error("❌ Por favor corrija los siguientes errores:")
            for e in errores: st.write(f"   • {e}")
        else:
            try:
                registros_existentes = hoja_casos.get_all_records()
                ot_existentes = [str(r.get("OT-TE", "")) for r in registros_existentes]
                if ot_te.strip() in ot_existentes:
                    st.error(f"❌ El caso '{ot_te}' ya existe en esta hoja")
                else:
                    timestamp = datetime.now(tz=_BOGOTA).strftime("%Y-%m-%d %H:%M:%S")
                    id_caso   = obtener_siguiente_id(hoja_casos)
                    hoja_casos.append_row([
                        id_caso, timestamp, tipo_estudio, ot_te.strip(),
                        str(fecha_expedicion_ot) if fecha_expedicion_ot else "",
                        tipo_poblacion, " | ".join(subpoblacion),
                        str(fecha_nacimiento) if fecha_nacimiento else "", sexo,
                        genero if genero and genero != "Seleccione..." else "",
                        orientacion_sexual if orientacion_sexual and orientacion_sexual != "Seleccione..." else "",
                        jefatura_hogar if jefatura_hogar and jefatura_hogar != "Seleccione..." else "",
                        zona_rural if zona_rural and zona_rural != "Seleccione..." else "",
                        zona_reserva if zona_reserva and zona_reserva != "Seleccione..." else "",
                        departamento.strip(), municipio.strip(), solicitante, nivel_riesgo,
                        observaciones.strip() if observaciones else "",
                        num_personas if num_personas is not None else "",
                        companero if companero and companero != "Seleccione..." else "",
                        num_hijos_menores if num_hijos_menores is not None else "",
                        num_menores_otros if num_menores_otros is not None else "",
                        num_adultos_mayores if num_adultos_mayores is not None else "",
                        num_discapacidad if num_discapacidad is not None else "",
                        osiegd.strip() if osiegd else "",
                        factor_discapacidad if factor_discapacidad and factor_discapacidad != "Seleccione..." else "",
                        factor_etnia if factor_etnia and factor_etnia != "Seleccione..." else "",
                        factor_campesino if factor_campesino and factor_campesino != "Seleccione..." else "",
                        factor_cuidador if factor_cuidador and factor_cuidador != "Seleccione..." else "",
                        " | ".join(victima_conflicto),
                        " | ".join(lider_social),
                        imp_eco_dependencia if imp_eco_dependencia != "Seleccione..." else "",
                        imp_eco_iniciativas if imp_eco_iniciativas != "Seleccione..." else "",
                        imp_eco_empleos if imp_eco_empleos != "Seleccione..." else "",
                        imp_eco_ilicita if imp_eco_ilicita != "Seleccione..." else "",
                        imp_eco_bienes if imp_eco_bienes != "Seleccione..." else "",
                        imp_soc_tejido if imp_soc_tejido != "Seleccione..." else "",
                        imp_soc_redes if imp_soc_redes != "Seleccione..." else "",
                        imp_soc_traslado if imp_soc_traslado != "Seleccione..." else "",
                        imp_soc_confinamiento if imp_soc_confinamiento != "Seleccione..." else "",
                        imp_soc_movilidad if imp_soc_movilidad != "Seleccione..." else "",
                        imp_soc_desarraigo if imp_soc_desarraigo != "Seleccione..." else "",
                        imp_soc_normalizacion if imp_soc_normalizacion != "Seleccione..." else "",
                        imp_soc_libertad if imp_soc_libertad != "Seleccione..." else "",
                        imp_pol_participacion if imp_pol_participacion != "Seleccione..." else "",
                        imp_pol_liderazgos if imp_pol_liderazgos != "Seleccione..." else "",
                        imp_pol_oferta if imp_pol_oferta != "Seleccione..." else "",
                        imp_pol_derechos if imp_pol_derechos != "Seleccione..." else "",
                        imp_pol_estigmatizacion if imp_pol_estigmatizacion != "Seleccione..." else "",
                        imp_pol_confianza if imp_pol_confianza != "Seleccione..." else "",
                        imp_sal_proyeccion if imp_sal_proyeccion != "Seleccione..." else "",
                        imp_sal_cuidados if imp_sal_cuidados != "Seleccione..." else "",
                        imp_sal_desescolarizacion if imp_sal_desescolarizacion != "Seleccione..." else "",
                        imp_sal_abandono if imp_sal_abandono != "Seleccione..." else "",
                        imp_sal_psicosocial if imp_sal_psicosocial != "Seleccione..." else "",
                        imp_sal_discapacidad if imp_sal_discapacidad != "Seleccione..." else "",
                        imp_sal_dano_vida if imp_sal_dano_vida != "Seleccione..." else "",
                        st.session_state.nombre_completo, st.session_state.username
                    ])
                    hechos_guardados = 0
                    for hecho in st.session_state.hechos:
                        id_hecho = obtener_siguiente_id(hoja_hechos)
                        hoja_hechos.append_row([
                            id_hecho, id_caso, ot_te.strip(),
                            hecho["tipo"], hecho["fecha"],
                            hecho.get("departamento", ""), hecho.get("municipio", ""),
                            hecho.get("tipo_actor", ""), hecho.get("actor_generador", ""),
                            hecho.get("medio", ""), hecho.get("victima_situacion", ""), hecho.get("tipo_amenaza", ""),
                            hecho.get("motivacion_amenaza", ""), hecho.get("nexo_causal", ""),
                            hecho["descripcion"],
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
                    pa_guardados = 0
                    for pa in st.session_state.perfiles_actuales:
                        id_pa = obtener_siguiente_id(hoja_perfiles_actuales)
                        hoja_perfiles_actuales.append_row([
                            id_pa, id_caso, ot_te.strip(),
                            pa.get("familiar_parte_comunes", ""),
                            pa.get("nivel_educativo", ""),
                            pa.get("fuente_ingresos", ""),
                            pa.get("estado_proyecto_arn", ""),
                            pa.get("actividad_economica", ""),
                            pa.get("comparecencia_jep", ""),
                            pa.get("macrocasos_jep", ""),
                            pa.get("victima_jep", ""),
                            pa.get("macrocaso_victima", ""),
                            pa.get("participacion_toar", ""),
                            pa.get("busqueda_desaparecidos", ""),
                            pa.get("participacion_pnis", ""),
                            pa.get("desminado", ""),
                            pa.get("participa_comunes", ""),
                            pa.get("concejo_comunes", ""),
                            pa.get("instancias_partido", ""),   # compat: 1er registro
                            pa.get("roles_partido", ""),        # compat: 1er registro
                            pa.get("consejeria_nacional", ""),  # compat: 1er registro
                            pa.get("tipo_consejeria", ""),      # compat: 1er registro
                            pa.get("participa_otras_org", ""),
                            pa.get("tipo_org", ""),             # compat: 1er registro
                            pa.get("nombre_org", ""),           # compat: 1er registro
                            pa.get("ambito_org", ""),           # compat: 1er registro
                            pa.get("escala_org", ""),           # compat: 1er registro
                            pa.get("departamento_org", ""),     # compat: 1er registro
                            pa.get("municipio_org", ""),        # compat: 1er registro
                            pa.get("rol_org", ""),              # compat: 1er registro
                            pa.get("anio_inicio_org", ""),      # compat: 1er registro
                            pa.get("anio_fin_org", ""),         # compat: 1er registro
                            pa.get("cargo_eleccion", ""),
                            st.session_state.nombre_completo, st.session_state.username
                        ])
                        # ── Colección Instancias Comunes (multiregistro) ──────
                        for ic in pa.get("instancias_comunes", []):
                            id_ic = obtener_siguiente_id(hoja_instancias_comunes)
                            hoja_instancias_comunes.append_row([
                                id_ic, id_pa, id_caso, ot_te.strip(),
                                ic.get("instancias_partido", ""),
                                ic.get("roles_partido", ""),
                                ic.get("consejeria_nacional", ""),
                                ic.get("tipo_consejeria", ""),
                                st.session_state.nombre_completo, st.session_state.username
                            ])
                        # ── Colección Otras Organizaciones (multiregistro) ────
                        for oo in pa.get("otras_orgs", []):
                            id_oo = obtener_siguiente_id(hoja_otras_orgs)
                            hoja_otras_orgs.append_row([
                                id_oo, id_pa, id_caso, ot_te.strip(),
                                oo.get("tipo_org", ""),
                                oo.get("nombre_org", ""),
                                oo.get("ambito_org", ""),
                                oo.get("escala_org", ""),
                                oo.get("departamento_org", ""),
                                oo.get("municipio_org", ""),
                                oo.get("rol_org", ""),
                                oo.get("anio_inicio_org", ""),
                                oo.get("anio_fin_org", ""),
                                st.session_state.nombre_completo, st.session_state.username
                            ])
                        pa_guardados += 1
                    antecedentes_guardados = 0
                    for ant in st.session_state.antecedentes:
                        id_ant = obtener_siguiente_id(hoja_antecedentes)
                        hoja_antecedentes.append_row([
                            id_ant, id_caso, ot_te.strip(),
                            ant.get("registra_ot", ""),
                            ant.get("registra_resoluciones", ""),
                            ant.get("dia_resolucion", ""),
                            ant.get("mes_resolucion", ""),
                            ant.get("anio_resolucion", ""),
                            st.session_state.nombre_completo, st.session_state.username
                        ])
                        antecedentes_guardados += 1
                    desp_guardados = 0
                    for desp in st.session_state.desplazamientos:
                        id_desp = obtener_siguiente_id(hoja_desplazamientos)
                        hoja_desplazamientos.append_row([
                            id_desp, id_caso, ot_te.strip(),
                            desp.get("motivo", ""),
                            desp.get("medios_transporte", ""),
                            desp.get("dep_origen", ""),
                            desp.get("mun_origen", ""),
                            desp.get("dep_destino", ""),
                            desp.get("mun_destino", ""),
                            desp.get("frecuencia", ""),
                            desp.get("tipo_via", ""),
                            st.session_state.nombre_completo, st.session_state.username
                        ])
                        desp_guardados += 1
                    ver_guardados = 0
                    for ver in st.session_state.verificaciones:
                        id_ver = obtener_siguiente_id(hoja_verificaciones)
                        hoja_verificaciones.append_row([
                            id_ver, id_caso, ot_te.strip(),
                            ver.get("fuente", ""),
                            ver.get("nombre_fuente", ""),
                            ver.get("v_hechos_riesgo", ""),
                            ver.get("v_lugar_hechos", ""),
                            ver.get("v_actor_hechos", ""),
                            ver.get("v_motivacion_amenaza", ""),
                            ver.get("v_perfil_antiguo", ""),
                            ver.get("v_modo_participacion", ""),
                            ver.get("v_rol_perfil_antiguo", ""),
                            ver.get("v_frente_columna", ""),
                            ver.get("v_perfil_actual", ""),
                            ver.get("v_organizacion", ""),
                            ver.get("v_rol_perfil_actual", ""),
                            st.session_state.nombre_completo, st.session_state.username
                        ])
                        ver_guardados += 1
                    st.session_state.hechos = []
                    st.session_state.perfiles = []
                    st.session_state.antecedentes = []
                    st.session_state.perfiles_actuales = []
                    st.session_state.desplazamientos = []
                    st.session_state.verificaciones = []
                    eliminar_borrador(st.session_state.username, tipo)
                    st.session_state[f"borrador_cargado_{tipo}"] = False
                    st.success(f"✅ Caso **{ot_te}** registrado en {label_badge}!")
                    if hechos_guardados        > 0: st.info(f"⚠️ {hechos_guardados} hecho(s) de riesgo registrados")
                    if perfiles_guardados      > 0: st.info(f"🧑‍🤝‍🧑 {perfiles_guardados} perfil(es) registrados")
                    if antecedentes_guardados  > 0: st.info(f"📁 {antecedentes_guardados} antecedente(s) registrados")
                    if desp_guardados          > 0: st.info(f"🚗 {desp_guardados} desplazamiento(s) registrados")
                    if ver_guardados           > 0: st.info(f"✅ {ver_guardados} verificación(es) registradas")
                    st.balloons()
                    st.info(f"""
                    **Resumen:**
                    - **ID Caso:** {id_caso}
                    - **Tipo de Estudio:** {tipo_estudio}
                    - **OT-TE:** {ot_te}
                    - **Fecha Expedición OT:** {fecha_expedicion_ot}
                    - **Tipo de Población:** {tipo_poblacion}
                    - **Subpoblación:** {" | ".join(subpoblacion)}
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
            (hoja_casos, hoja_hechos, hoja_perfiles, hoja_antecedentes_v,
             hoja_perfiles_actuales_v, hoja_desplazamientos_v, hoja_verificaciones_v,
             hoja_instancias_comunes_v, hoja_otras_orgs_v, sheet_url) = conectar_sheet_casos(tipo)
            if hoja_casos is None: st.error(f"No se pudo conectar a la hoja {tipo}"); continue

            sub1, sub2, sub3, sub4, sub5, sub6, sub7, sub8, sub9 = st.tabs(["📋 Casos", "⚠️ Hechos de Riesgo", "🧑‍🤝‍🧑 Perfil Antiguo", "📁 Antecedentes", "🎯 Perfil Actual", "🚗 Desplazamientos", "✅ Verificaciones", "🏛️ Instancias Comunes", "🤝 Otras Orgs"])

            try: datos   = hoja_casos.get_all_records()
            except: datos = []
            try: datos_h = hoja_hechos.get_all_records()
            except: datos_h = []
            try: datos_p = hoja_perfiles.get_all_records()
            except: datos_p = []
            try: datos_a = hoja_antecedentes_v.get_all_records()
            except: datos_a = []
            try: datos_pa = hoja_perfiles_actuales_v.get_all_records()
            except: datos_pa = []
            try: datos_d = hoja_desplazamientos_v.get_all_records()
            except: datos_d = []
            try: datos_ver = hoja_verificaciones_v.get_all_records()
            except: datos_ver = []
            try: datos_ic  = hoja_instancias_comunes_v.get_all_records()
            except: datos_ic = []
            try: datos_oo  = hoja_otras_orgs_v.get_all_records()
            except: datos_oo = []

            df     = pd.DataFrame(datos)     if datos     else pd.DataFrame()
            df_h   = pd.DataFrame(datos_h)   if datos_h   else pd.DataFrame()
            df_p   = pd.DataFrame(datos_p)   if datos_p   else pd.DataFrame()
            df_a   = pd.DataFrame(datos_a)   if datos_a   else pd.DataFrame()
            df_pa  = pd.DataFrame(datos_pa)  if datos_pa  else pd.DataFrame()
            df_d   = pd.DataFrame(datos_d)   if datos_d   else pd.DataFrame()
            df_ver = pd.DataFrame(datos_ver) if datos_ver else pd.DataFrame()
            df_ic  = pd.DataFrame(datos_ic)  if datos_ic  else pd.DataFrame()
            df_oo  = pd.DataFrame(datos_oo)  if datos_oo  else pd.DataFrame()

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

            with sub4:
                if not df_a.empty:
                    c1,c2 = st.columns(2)
                    c1.metric("Total Antecedentes",    len(df_a))
                    c2.metric("Casos con antecedentes", df_a["ID_Caso"].nunique() if "ID_Caso" in df_a.columns else 0)
                    st.dataframe(df_a, use_container_width=True, hide_index=True)
                else: st.info("📭 No hay antecedentes registrados")

            with sub5:
                if not df_pa.empty:
                    c1, c2 = st.columns(2)
                    c1.metric("Total Perfiles Actuales", len(df_pa))
                    c2.metric("Casos con perfil actual", df_pa["ID_Caso"].nunique() if "ID_Caso" in df_pa.columns else 0)
                    st.dataframe(df_pa, use_container_width=True, hide_index=True)
                else: st.info("📭 No hay perfiles actuales registrados")

            with sub6:
                if not df_d.empty:
                    c1, c2 = st.columns(2)
                    c1.metric("Total Desplazamientos", len(df_d))
                    c2.metric("Casos con desplazamiento", df_d["ID_Caso"].nunique() if "ID_Caso" in df_d.columns else 0)
                    motivo_f = st.selectbox("Filtrar por Motivo", ["Todos"] + sorted(df_d["Motivo Desplazamiento"].unique().tolist()) if "Motivo Desplazamiento" in df_d.columns else ["Todos"], key=f"motivo_desp_{tipo}")
                    df_df = df_d[df_d["Motivo Desplazamiento"] == motivo_f].copy() if motivo_f != "Todos" else df_d.copy()
                    st.dataframe(df_df, use_container_width=True, hide_index=True)
                else: st.info("📭 No hay desplazamientos registrados")

            with sub7:
                if not df_ver.empty:
                    c1, c2 = st.columns(2)
                    c1.metric("Total Verificaciones", len(df_ver))
                    c2.metric("Casos con verificación", df_ver["ID_Caso"].nunique() if "ID_Caso" in df_ver.columns else 0)
                    fuente_f = st.selectbox("Filtrar por Fuente", ["Todos"] + sorted(df_ver["Fuente Verificacion"].unique().tolist()) if "Fuente Verificacion" in df_ver.columns else ["Todos"], key=f"fuente_ver_{tipo}")
                    df_verf = df_ver[df_ver["Fuente Verificacion"] == fuente_f].copy() if fuente_f != "Todos" else df_ver.copy()
                    st.dataframe(df_verf, use_container_width=True, hide_index=True)
                else: st.info("📭 No hay verificaciones registradas")

            with sub8:
                if not df_ic.empty:
                    c1, c2 = st.columns(2)
                    c1.metric("Total Instancias", len(df_ic))
                    c2.metric("Perfiles con instancias", df_ic["ID_Perfil_Actual"].nunique() if "ID_Perfil_Actual" in df_ic.columns else 0)
                    inst_f = st.selectbox("Filtrar por Instancia", ["Todos"] + sorted(df_ic["Instancias Partido"].dropna().unique().tolist()) if "Instancias Partido" in df_ic.columns else ["Todos"], key=f"inst_f_{tipo}")
                    df_icf = df_ic[df_ic["Instancias Partido"] == inst_f].copy() if inst_f != "Todos" else df_ic.copy()
                    st.dataframe(df_icf, use_container_width=True, hide_index=True)
                else: st.info("📭 No hay registros de instancias en Partido Comunes")

            with sub9:
                if not df_oo.empty:
                    c1, c2 = st.columns(2)
                    c1.metric("Total Organizaciones", len(df_oo))
                    c2.metric("Perfiles con org.", df_oo["ID_Perfil_Actual"].nunique() if "ID_Perfil_Actual" in df_oo.columns else 0)
                    tipo_org_f = st.selectbox("Filtrar por Tipo", ["Todos"] + sorted(df_oo["Tipo Org"].dropna().unique().tolist()) if "Tipo Org" in df_oo.columns else ["Todos"], key=f"tipo_org_f_{tipo}")
                    df_oof = df_oo[df_oo["Tipo Org"] == tipo_org_f].copy() if tipo_org_f != "Todos" else df_oo.copy()
                    st.dataframe(df_oof, use_container_width=True, hide_index=True)
                else: st.info("📭 No hay registros de otras organizaciones")


            st.markdown("---")
            if not df.empty or not df_h.empty or not df_p.empty or not df_a.empty or not df_pa.empty or not df_d.empty or not df_ver.empty or not df_ic.empty or not df_oo.empty:
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                    (df_f   if not df.empty   else df).to_excel(writer, sheet_name="Casos",              index=False)
                    (df_hf  if not df_h.empty else df_h).to_excel(writer, sheet_name="Hechos de Riesgo", index=False)
                    df_p.to_excel(writer, sheet_name="Perfiles",          index=False)
                    df_a.to_excel(writer, sheet_name="Antecedentes",      index=False)
                    df_pa.to_excel(writer, sheet_name="Perfiles Actuales", index=False)
                    df_ic.to_excel(writer, sheet_name="Instancias Comunes",  index=False)
                    df_oo.to_excel(writer, sheet_name="Otras Orgs",          index=False)
                buffer.seek(0)
                nombre_archivo = f"ISMR_{tipo}_{datetime.now(tz=_BOGOTA).strftime('%Y%m%d_%H%M')}.xlsx"
                st.download_button(
                    label="📥 Descargar reporte completo (.xlsx)",
                    data=buffer,
                    file_name=nombre_archivo,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key=f"dl_xlsx_{tipo}",
                    use_container_width=True,
                    type="primary"
                )


# ═══════════════════════════════════════════════════════════════════════════════
# Panel_gestion_usuarios
# ═══════════════════════════════════════════════════════════════════════════════

def panel_gestion_usuarios():
    import unicodedata, io
    from data.mongo.usuarios_repo import crear_usuarios_masivo, hashear_password

    def _normalizar(texto):
        """Quita tildes y pasa a minúsculas."""
        return "".join(
            c for c in unicodedata.normalize("NFD", texto)
            if unicodedata.category(c) != "Mn"
        ).lower()

    def _generar_username(nombre_completo):
        """'Juan Carlos Pérez López' → 'juan.perez'  (primer nombre . primer apellido)"""
        partes = nombre_completo.strip().split()
        if len(partes) >= 2:
            return f"{_normalizar(partes[0])}.{_normalizar(partes[-1])}"
        return _normalizar(partes[0]) if partes else ""

    st.title("👥 Gestión de Usuarios")
    st.markdown("---")

    tab1, tab2, tab3, tab4 = st.tabs([
        "➕ Crear Usuario",
        "📤 Carga Masiva (Excel)",
        "📋 Ver Usuarios",
        "🔑 Ver Hashes",
    ])

    # ── TAB 1: Crear usuario individual (sin cambios) ───────────────────────────
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
                    if crear_usuario(nuevo_username, password_default, nuevo_nombre, es_admin_nuevo, True):
                        st.success(f"✅ Usuario '{nuevo_username}' creado!")
                        st.info(f"Usuario: **{nuevo_username}** | Contraseña temporal: **{password_default}**")
                    else:
                        st.error("❌ El usuario ya existe o hubo un problema al crearlo")
                else:
                    st.warning("⚠️ Completa todos los campos")

    # ── TAB 2: Carga masiva desde Excel ────────────────────────────────────────
    with tab2:
        st.subheader("📤 Carga Masiva de Usuarios desde Excel")

        # Plantilla descargable
        with st.expander("📥 Descargar plantilla Excel", expanded=False):
            st.markdown(
                "El archivo debe tener **dos columnas** con los encabezados exactos:\n"
                "- `nombre_completo` — Ej: *María López Rodríguez*\n"
                "- `username` *(opcional)* — si se deja vacío se genera automáticamente "
                "como `primer_nombre.primer_apellido`"
            )
            df_plantilla = pd.DataFrame({
                "nombre_completo": ["María López Rodríguez", "Carlos Gómez Martínez"],
                "username":        ["maria.rodriguez",       ""],
            })
            buf_plantilla = io.BytesIO()
            df_plantilla.to_excel(buf_plantilla, index=False, engine="openpyxl")
            buf_plantilla.seek(0)
            st.download_button(
                "⬇️ Descargar plantilla",
                data=buf_plantilla,
                file_name="plantilla_usuarios.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

        st.markdown("---")

        archivo = st.file_uploader(
            "Sube el Excel con los usuarios", type=["xlsx", "xls"],
            help="Columna requerida: nombre_completo. Opcional: username",
        )

        if archivo:
            try:
                df_up = pd.read_excel(archivo, dtype=str).fillna("")
            except Exception as e:
                st.error(f"❌ No se pudo leer el archivo: {e}")
                df_up = None

            if df_up is not None:
                if "nombre_completo" not in df_up.columns:
                    st.error("❌ El archivo debe tener una columna llamada **nombre_completo**.")
                else:
                    # Generar username si está vacío o la columna no existe
                    if "username" not in df_up.columns:
                        df_up["username"] = ""
                    df_up["username"] = df_up.apply(
                        lambda r: r["username"].strip() if r["username"].strip()
                        else _generar_username(r["nombre_completo"]),
                        axis=1,
                    )
                    df_up = df_up[df_up["nombre_completo"].str.strip() != ""].reset_index(drop=True)

                    st.info(f"📊 Se encontraron **{len(df_up)}** usuarios en el archivo.")
                    st.dataframe(
                        df_up[["nombre_completo", "username"]],
                        use_container_width=True,
                        hide_index=True,
                    )

                    col_pw, col_adm = st.columns(2)
                    with col_pw:
                        pwd_masiva = st.text_input(
                            "Contraseña temporal para todos", value="ISMR2024",
                            key="pwd_masiva",
                            help="Todos los usuarios deberán cambiarla al primer ingreso",
                        )
                    with col_adm:
                        admin_masivo = st.checkbox(
                            "¿Todos son administradores?", value=False, key="admin_masivo"
                        )

                    if st.button("🚀 Crear todos los usuarios", type="primary", use_container_width=True):
                        if not pwd_masiva:
                            st.warning("⚠️ Define una contraseña temporal")
                        else:
                            lista = df_up[["nombre_completo", "username"]].to_dict("records")
                            with st.spinner(f"Registrando {len(lista)} usuarios…"):
                                resultado = crear_usuarios_masivo(lista, pwd_masiva, admin_masivo)

                            creados  = resultado["creados"]
                            omitidos = resultado["omitidos"]
                            errores  = resultado["errores"]

                            if creados:
                                st.success(f"✅ **{len(creados)}** usuarios creados correctamente.")
                            if omitidos:
                                st.warning(f"⚠️ **{len(omitidos)}** ya existían y fueron omitidos: {', '.join(omitidos)}")
                            if errores:
                                st.error(f"❌ **{len(errores)}** con errores:")
                                for e in errores:
                                    st.caption(f"• `{e['username']}`: {e['error']}")

                            # Resumen descargable
                            df_res = pd.DataFrame({
                                "username": creados + omitidos + [e["username"] for e in errores],
                                "estado":   (["creado"]     * len(creados) +
                                             ["ya existía"] * len(omitidos) +
                                             ["error"]      * len(errores)),
                                "detalle":  ([""] * len(creados) +
                                             [""] * len(omitidos) +
                                             [e["error"] for e in errores]),
                            })
                            buf_res = io.BytesIO()
                            df_res.to_excel(buf_res, index=False, engine="openpyxl")
                            buf_res.seek(0)
                            st.download_button(
                                "📥 Descargar resumen de carga",
                                data=buf_res,
                                file_name="resumen_carga_usuarios.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            )

    # ── TAB 3: Ver usuarios ─────────────────────────────────────────────────────
    with tab3:
        st.subheader("📋 Lista de Usuarios")
        usuarios = listar_usuarios()
        if usuarios:
            df = pd.DataFrame(usuarios)
            c1, c2, c3 = st.columns(3)
            c1.metric("Total", len(df))
            admins = df[df["es_admin"].astype(str).str.upper() == "TRUE"].shape[0] if "es_admin" in df.columns else 0
            c2.metric("Admins", admins)
            c3.metric("Analistas", len(df) - admins)
            st.dataframe(
                df[["username", "nombre_completo", "es_admin", "debe_cambiar_password"]],
                use_container_width=True,
            )
        else:
            st.info("📭 No hay usuarios")

    # ── TAB 4: Ver hashes ───────────────────────────────────────────────────────
    with tab4:
        st.subheader("🔑 Hashes de Contraseñas")
        st.warning("⚠️ Información sensible — solo visible para administradores")
        if st.checkbox("Mostrar hashes"):
            for u in listar_usuarios():
                with st.expander(f"👤 {u.get('nombre_completo','?')} (@{u.get('username','?')})"):
                    st.code(u.get('password_hash', 'N/A'), language=None)
                    st.caption(f"Debe cambiar: {u.get('debe_cambiar_password','N/A')}")


# ═════════════════════════════════════════════════════════════════════════════
# RECUPERACIÓN DE CONTRASEÑA
# ═════════════════════════════════════════════════════════════════════════════

def pantalla_recovery_solicitar():
    from service.recovery_service import enviar_codigo_recuperacion, username_a_email

    st.title("🔑 Recuperar Contraseña")
    st.markdown("---")
    st.info(
        "Ingresa tu nombre de usuario. Te enviaremos un código de verificación "
        "a tu correo institucional **@unp.gov.co**."
    )

    with st.form("recovery_solicitar_form"):
        username = st.text_input("Usuario", placeholder="nombre.apellido")
        submit   = st.form_submit_button("📨 Enviar código", use_container_width=True, type="primary")

        if submit:
            if not username.strip():
                st.warning("⚠️ Ingresa tu nombre de usuario")
            elif not usuario_existe(username.strip()):
                # Mensaje genérico para no revelar si el usuario existe
                st.warning("⚠️ Si el usuario existe, recibirás un correo en breve.")
            else:
                with st.spinner("Enviando código..."):
                    ok, resultado = enviar_codigo_recuperacion(username.strip())
                if ok:
                    email_visible = username_a_email(username.strip())
                    st.session_state["recovery_username"] = username.strip()
                    st.session_state.vista_recovery = "verificar"
                    st.success(f"✅ Código enviado a **{email_visible}**")
                    st.rerun()
                else:
                    st.error(f"❌ No se pudo enviar el correo. Contacta al administrador.\n\n`{resultado}`")

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("← Volver al inicio de sesión", type="secondary"):
        st.session_state.vista_recovery = None
        st.rerun()


def pantalla_recovery_verificar():
    from service.recovery_service import validar_codigo, username_a_email

    username = st.session_state.get("recovery_username", "")
    email_visible = username_a_email(username) if username else "tu correo"

    st.title("🔑 Verificar Código")
    st.markdown("---")
    st.info(f"Ingresa el código de 6 dígitos enviado a **{email_visible}**. Expira en 15 minutos.")

    with st.form("recovery_verificar_form"):
        codigo = st.text_input("Código de verificación", placeholder="000000", max_chars=6)
        submit = st.form_submit_button("✅ Verificar código", use_container_width=True, type="primary")

        if submit:
            if not codigo.strip():
                st.warning("⚠️ Ingresa el código")
            elif not validar_codigo(username, codigo.strip()):
                st.error("❌ Código incorrecto o expirado. Solicita uno nuevo.")
            else:
                st.session_state["recovery_codigo_ok"] = True
                st.session_state.vista_recovery = "nueva_password"
                st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("← Solicitar nuevo código", use_container_width=True, type="secondary"):
            st.session_state.vista_recovery = "solicitar"
            st.rerun()
    with col_b:
        if st.button("✖ Cancelar", use_container_width=True, type="secondary"):
            st.session_state.vista_recovery = None
            st.session_state.pop("recovery_username", None)
            st.rerun()


def pantalla_recovery_nueva_password():
    from service.recovery_service import limpiar_codigo

    username = st.session_state.get("recovery_username", "")

    # Guardia: si llegaron sin pasar por verificación, redirigir
    if not st.session_state.get("recovery_codigo_ok"):
        st.session_state.vista_recovery = "solicitar"
        st.rerun()

    st.title("🔑 Nueva Contraseña")
    st.markdown("---")
    st.success(f"✅ Identidad verificada para **{username}**")

    with st.form("recovery_nueva_password_form"):
        nueva     = st.text_input("Nueva contraseña", type="password", help="Mínimo 8 caracteres")
        confirmar = st.text_input("Confirmar contraseña", type="password")
        submit    = st.form_submit_button("💾 Guardar contraseña", use_container_width=True, type="primary")

        if submit:
            errores = []
            if not nueva:          errores.append("La contraseña no puede estar vacía")
            elif len(nueva) < 8:   errores.append("Mínimo 8 caracteres")
            if nueva != confirmar: errores.append("Las contraseñas no coinciden")

            if errores:
                for e in errores: st.error(f"❌ {e}")
            else:
                nuevo_hash = hashear_password(nueva)
                if actualizar_password(username, nuevo_hash, False):
                    limpiar_codigo(username)
                    st.session_state.vista_recovery        = None
                    st.session_state["recovery_username"]  = None
                    st.session_state["recovery_codigo_ok"] = False
                    st.success("✅ ¡Contraseña actualizada! Ya puedes iniciar sesión.")
                    time.sleep(2)
                    st.rerun()
                else:
                    st.error("❌ No se pudo actualizar la contraseña. Intenta de nuevo.")

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("✖ Cancelar", type="secondary"):
        st.session_state.vista_recovery        = None
        st.session_state["recovery_username"]  = None
        st.session_state["recovery_codigo_ok"] = False
        st.rerun()
