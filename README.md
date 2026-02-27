# ISMR Formulario – Documentación Técnica (BETA)

## Descripción del Proyecto

Aplicación web para el **Sistema de Investigación de Múltiples Riesgos
(ISMR)**.

Permite a analistas:

-   Registrar casos de riesgo (individuales y colectivos)
-   Gestionar múltiples hechos de riesgo por caso (multiregistros)
-   Autenticarse mediante login con control de roles
-   Exportar datos en `.xlsx`
-   Importar usuarios desde `.xlsx`
-   Trabajar con guardado temporal ante fallos de conexión

> ⚠️ **Estado del proyecto:** Fase **BETA / PRUEBA**  
> Sistema en etapa de validación funcional y detección de errores antes
> de su versión estable.

------------------------------------------------------------------------

# Stack Tecnológico

-   Python 3.11
-   Streamlit
-   MongoDB
-   pandas
-   openpyxl
-   Arquitectura modular por capas

------------------------------------------------------------------------

# Estructura Actual del Proyecto

    ismr-formulario/
    │
    ├── .devcontainer/
    ├── .idea/
    ├── .streamlit/
    │
    ├── configuration/
    │   ├── __init__.py
    │   └── settings.py
    │
    ├── data/
    │   ├── mongo/
    │   │   ├── __init__.py
    │   │   ├── casos_repo.py
    │   │   └── usuarios_repo.py
    │   │
    │   ├── __init__.py
    │   ├── casos_repo.py
    │   ├── usuarios_repo.py
    │   └── diccionarios.py
    │
    ├── service/
    │   ├── __init__.py
    │   ├── auth_service.py
    │   └── recovery_service.py
    │
    ├── front/
    │   ├── __init__.py
    │   ├── pages.py
    │   └── styles.py
    │
    ├── new_app_ismr_sheets.py
    ├── requirements.txt
    ├── .gitignore
    └── README.md

------------------------------------------------------------------------

# Arquitectura

El sistema sigue una arquitectura por capas:

1.  **Front (Presentación)**  
    Renderizado de vistas, formularios y control de sesión.

2.  **Service (Lógica de Negocio)**  
    Autenticación, validaciones, control de roles y procesamiento de
    datos.

3.  **Data (Persistencia)**  
    Repositorios MongoDB y operaciones CRUD.

4.  **Configuration**  
    Parámetros globales y configuración del entorno.

------------------------------------------------------------------------

# Funcionalidades

## Autenticación

-   Login con usuario y contraseña
-   Hash seguro de contraseñas
-   Roles: Usuario (Analista) y Administrador

## Registro de Casos

-   Casos individuales y colectivos
-   Multiregistro de hechos de riesgo
-   Validación de identificadores únicos
-   Persistencia en MongoDB

## Guardado Temporal

-   Conservación en `session_state`
-   Reintento de guardado ante fallos
-   Minimiza pérdida de información

## Exportación e Importación

-   Exportación de datos en `.xlsx` (solo admin)
-   Importación masiva de usuarios desde `.xlsx`
-   Validación y control de duplicados

------------------------------------------------------------------------

# Ejecución Local

``` bash
pip install -r requirements.txt
streamlit run app_ismr_sheets.py
```

Aplicación disponible en:

http://localhost:8501

------------------------------------------------------------------------

# Estado del Proyecto

🟡 BETA

Sistema en fase de pruebas internas, sujeto a mejoras estructurales y
corrección de errores.

https://ismr-formulario-gqzurmnkdwcynb59a8rq3h.streamlit.app/
