from frappe import _


def get_data():
    return [
        {
            "module_name": "Gastos Prorrateados",
            "color": "#5E64FF",
            "icon": "octicon octicon-split",
            "type": "module",
            "label": _("Gastos Prorrateados"),
            "description": _("Gestión de gastos compartidos entre múltiples empresas"),
        }
    ]
