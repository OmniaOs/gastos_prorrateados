app_name = "gastos_prorrateados"
app_title = "Gastos Prorrateados"
app_publisher = "OmniaOS"
app_description = "Módulo de Gastos Prorrateados entre múltiples empresas para ERPNext"
app_email = "admin@omniaos.ai"
app_license = "MIT"

# Fixtures exportables (custom fields en doctypes estándar de ERPNext)
fixtures = [
    {
        "dt": "Custom Field",
        "filters": [
            ["name", "in", [
                "Purchase Invoice-gasto_prorrateado",
                "Purchase Invoice-porcentaje_aplicado",
                "Payment Entry-gasto_prorrateado",
                "Payment Entry-empresa_prorrateada",
            ]]
        ]
    }
]

# Módulos del workspace
app_include_css = []
app_include_js = []

# DocTypes que se incluyen en el módulo
required_apps = ["erpnext"]
