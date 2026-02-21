import streamlit as st

from configuration.settings import defaults
from service.auth_service import logout
from front.pages import (
    login_page,
    pantalla_cambiar_password,
    pantalla_selector,
    formulario_casos,
    panel_visualizacion,
    panel_gestion_usuarios,
)

st.set_page_config(page_title="Sistema ISMR", page_icon="📋", layout="centered")

for key, val in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = val


def main():
    if not st.session_state.autenticado:
        login_page(); return
    if st.session_state.debe_cambiar_password:
        pantalla_cambiar_password(); return
    if st.session_state.es_admin:
        st.sidebar.title("📊 Sistema ISMR")
        st.sidebar.success(f"👤 {st.session_state.nombre_completo}")
        st.sidebar.markdown("---")
        opcion = st.sidebar.radio("Menú", ["🏠 Inicio", "📊 Ver Datos", "👥 Gestionar Usuarios"])
        if st.sidebar.button("🚪 Cerrar Sesión", use_container_width=True): logout()
        vista = st.session_state.get("vista")
        if   vista == "individual":          formulario_casos("individual")
        elif vista == "colectivo":           formulario_casos("colectivo")
        elif opcion == "🏠 Inicio":          pantalla_selector()
        elif opcion == "📊 Ver Datos":       panel_visualizacion()
        else:                                panel_gestion_usuarios()
        return
    vista = st.session_state.vista
    if   vista is None:         pantalla_selector()
    elif vista == "individual": formulario_casos("individual")
    elif vista == "colectivo":  formulario_casos("colectivo")


if __name__ == "__main__":
    main()
