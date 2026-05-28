import frappe
from frappe import _
from frappe.model.document import Document


class PerfildeProrrateo(Document):
    def validate(self):
        self.validar_porcentajes()
        self.validar_empresas_duplicadas()

    def validar_porcentajes(self):
        if not self.lineas_prorrateo:
            frappe.throw(_("Debe agregar al menos una línea de prorrateo."))

        total = sum(float(l.porcentaje or 0) for l in self.lineas_prorrateo)
        if abs(total - 100.0) > 0.01:
            frappe.throw(
                _("Los porcentajes deben sumar exactamente 100%. Suma actual: {0}%").format(
                    round(total, 4)
                )
            )

    def validar_empresas_duplicadas(self):
        empresas = [l.empresa for l in self.lineas_prorrateo if l.empresa]
        if len(empresas) != len(set(empresas)):
            frappe.throw(_("No puede haber empresas duplicadas en las líneas de prorrateo."))
