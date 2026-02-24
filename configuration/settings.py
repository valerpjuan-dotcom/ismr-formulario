defaults = {
    "autenticado": False, "username": None, "nombre_completo": None,
    "debe_cambiar_password": False, "es_admin": False, "vista": None,
    "hechos": [], "perfiles": [], "antecedentes": [], "perfiles_actuales": []
}

TAB_NOMBRES = {
    "individual": {
        "casos": "Individual", "hechos": "Hechos_Individual",
        "perfiles": "Perfiles_Individual", "antecedentes": "Antecedentes_Individual",
        "perfiles_actuales": "Perfiles_Actuales_Individual",
    },
    "colectivo": {
        "casos": "Colectivo", "hechos": "Hechos_Colectivo",
        "perfiles": "Perfiles_Colectivo", "antecedentes": "Antecedentes_Colectivo",
        "perfiles_actuales": "Perfiles_Actuales_Colectivo",
    },
}
