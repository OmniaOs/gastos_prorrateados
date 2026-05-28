import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, cint


class GastoProrrateado(Document):
    # ------------------------------------------------------------------
    # Lifecycle hooks
    # ------------------------------------------------------------------

    def validate(self):
        self.validar_porcentajes()
        self.validar_empresas_duplicadas()
        self.calcular_montos()
        if self.pago_inmediato:
            self.validar_campos_pago()

    def on_submit(self):
        self.generar_facturas_por_empresa()
        if self.pago_inmediato:
            self.generar_pagos_pos()
        nuevo_estado = "Pagado" if self.pago_inmediato else "Generado"
        self.db_set("estado", nuevo_estado)

    def on_cancel(self):
        self.cancelar_documentos_relacionados()
        self.db_set("estado", "Borrador")

    # ------------------------------------------------------------------
    # Validaciones
    # ------------------------------------------------------------------

    def validar_porcentajes(self):
        if not self.lineas_gasto:
            frappe.throw(_("Debe agregar al menos una línea de distribución."))

        total = sum(flt(l.porcentaje) for l in self.lineas_gasto)
        if abs(total - 100.0) > 0.01:
            frappe.throw(
                _("Los porcentajes deben sumar 100%. Suma actual: <b>{0}%</b>").format(
                    round(total, 4)
                )
            )

    def validar_empresas_duplicadas(self):
        empresas = [l.empresa for l in self.lineas_gasto if l.empresa]
        if len(empresas) != len(set(empresas)):
            frappe.throw(
                _("Hay empresas duplicadas en las líneas de distribución. Cada empresa debe aparecer solo una vez.")
            )

    def validar_campos_pago(self):
        if self.pago_por_empresa:
            if not self.pagos_por_empresa:
                frappe.throw(_("Configure al menos una fila en la tabla <b>Pagos por Empresa</b>."))
            pago_map = {p.empresa: p for p in self.pagos_por_empresa}
            for linea in self.lineas_gasto:
                pago = pago_map.get(linea.empresa)
                if not pago or not pago.modo_pago:
                    frappe.throw(
                        _("La empresa <b>{0}</b> no tiene Modo de Pago configurado en la tabla de pagos.").format(linea.empresa)
                    )
        else:
            if not self.modo_pago:
                frappe.throw(_("El campo <b>Modo de Pago</b> es obligatorio cuando se activa Pago Inmediato."))

    # ------------------------------------------------------------------
    # Cálculo de montos
    # ------------------------------------------------------------------

    def calcular_montos(self):
        for linea in self.lineas_gasto:
            linea.monto = flt(self.monto_total) * flt(linea.porcentaje) / 100.0

    # ------------------------------------------------------------------
    # Generación de Purchase Invoices
    # ------------------------------------------------------------------

    def generar_facturas_por_empresa(self):
        for linea in self.lineas_gasto:
            if linea.factura_compra:
                # Ya fue generada (ej. reintento tras error parcial)
                continue

            moneda_empresa = (
                self.moneda
                or frappe.get_cached_value("Company", linea.empresa, "default_currency")
            )
            centro_costo = (
                linea.centro_costo
                or frappe.get_cached_value("Company", linea.empresa, "cost_center")
            )
            cuenta_gasto = linea.cuenta_gasto or self._obtener_cuenta_gasto(linea.empresa)

            pi = frappe.new_doc("Purchase Invoice")
            pi.company = linea.empresa
            pi.supplier = self.proveedor
            pi.posting_date = self.fecha
            pi.due_date = self.fecha
            pi.currency = moneda_empresa
            pi.conversion_rate = flt(self.tipo_cambio) or 1.0
            pi.gasto_prorrateado = self.name
            pi.porcentaje_aplicado = flt(linea.porcentaje)
            pi.remarks = (
                f"Generado desde Gasto Prorrateado {self.name} — "
                f"{flt(linea.porcentaje)}% para {linea.empresa}"
            )

            pi.append(
                "items",
                {
                    "item_code": self.producto,
                    "qty": 1,
                    "rate": flt(linea.monto),
                    "expense_account": cuenta_gasto,
                    "cost_center": centro_costo,
                    "description": self.descripcion or frappe.get_cached_value("Item", self.producto, "item_name"),
                },
            )

            pi.set_missing_values()
            pi.insert(ignore_permissions=True)
            pi.submit()

            linea.db_set("factura_compra", pi.name)
            linea.db_set("estado_linea", "Generada")

    def _obtener_cuenta_gasto(self, empresa):
        """Resuelve la cuenta de gasto desde Item Defaults → Company default."""
        item_defaults = frappe.get_all(
            "Item Default",
            filters={"parent": self.producto, "company": empresa},
            fields=["expense_account"],
            limit=1,
        )
        if item_defaults and item_defaults[0].get("expense_account"):
            return item_defaults[0]["expense_account"]

        company_default = frappe.get_cached_value("Company", empresa, "default_expense_account")
        if not company_default:
            frappe.throw(
                _(
                    "No se encontró cuenta de gasto para el producto <b>{0}</b> en la empresa <b>{1}</b>. "
                    "Configure los Item Defaults del producto o la cuenta de gasto predeterminada de la empresa."
                ).format(self.producto, empresa)
            )
        return company_default

    # ------------------------------------------------------------------
    # Generación de Payment Entries (POS)
    # ------------------------------------------------------------------

    def generar_pagos_pos(self):
        for linea in self.lineas_gasto:
            if not linea.factura_compra or linea.entrada_pago:
                continue

            pi = frappe.get_doc("Purchase Invoice", linea.factura_compra)
            moneda_empresa = (
                self.moneda
                or frappe.get_cached_value("Company", linea.empresa, "default_currency")
            )

            # Resolver campos de pago: por empresa o globales
            if self.pago_por_empresa:
                pago_map = {p.empresa: p for p in self.pagos_por_empresa}
                pago_info = pago_map.get(linea.empresa, frappe._dict())
                modo_pago = pago_info.get("modo_pago")
                cuenta_bancaria = pago_info.get("cuenta_bancaria")
                referencia_pago = pago_info.get("referencia_pago")
            else:
                modo_pago = self.modo_pago
                cuenta_bancaria = self.cuenta_bancaria
                referencia_pago = self.referencia_pago

            pe = frappe.new_doc("Payment Entry")
            pe.payment_type = "Pay"
            pe.company = linea.empresa
            pe.posting_date = self.fecha
            pe.mode_of_payment = modo_pago
            pe.party_type = "Supplier"
            pe.party = self.proveedor
            pe.party_name = frappe.get_cached_value("Supplier", self.proveedor, "supplier_name")
            pe.paid_amount = flt(linea.monto)
            pe.received_amount = flt(linea.monto)
            pe.source_exchange_rate = flt(self.tipo_cambio) or 1.0
            pe.target_exchange_rate = flt(self.tipo_cambio) or 1.0
            pe.paid_from_account_currency = moneda_empresa
            pe.paid_to_account_currency = moneda_empresa
            pe.gasto_prorrateado = self.name
            pe.empresa_prorrateada = linea.empresa
            pe.reference_no = referencia_pago or self.name
            pe.reference_date = self.fecha

            # Cuenta de pago desde la cuenta bancaria o modo de pago
            if cuenta_bancaria:
                ba = frappe.get_doc("Bank Account", cuenta_bancaria)
                pe.paid_from = ba.account
            else:
                pe.paid_from = frappe.get_cached_value(
                    "Mode of Payment Account",
                    {"parent": modo_pago, "company": linea.empresa},
                    "default_account",
                )

            pe.paid_to = pi.credit_to

            # setup_party_account_field() solo se llama en __init__ para docs
            # existentes; en new_doc() no corre, dejando party_account sin
            # inicializar y rompiendo set_missing_values() en ERPNext v16.
            pe.setup_party_account_field()

            pe.append(
                "references",
                {
                    "reference_doctype": "Purchase Invoice",
                    "reference_name": linea.factura_compra,
                    "allocated_amount": flt(linea.monto),
                    "total_amount": flt(linea.monto),
                    "outstanding_amount": flt(linea.monto),
                },
            )

            pe.set_missing_values()
            pe.insert(ignore_permissions=True)
            pe.submit()

            linea.db_set("entrada_pago", pe.name)
            linea.db_set("estado_linea", "Pagada")

    # ------------------------------------------------------------------
    # Cancelación
    # ------------------------------------------------------------------

    def cancelar_documentos_relacionados(self):
        """Cancela en orden: Payment Entries primero, luego Purchase Invoices."""
        for linea in self.lineas_gasto:
            if linea.entrada_pago:
                pe = frappe.get_doc("Payment Entry", linea.entrada_pago)
                if pe.docstatus == 1:
                    pe.cancel()
                linea.db_set("entrada_pago", None)
                linea.db_set("estado_linea", "Generada")

        for linea in self.lineas_gasto:
            if linea.factura_compra:
                pi = frappe.get_doc("Purchase Invoice", linea.factura_compra)
                if pi.docstatus == 1:
                    pi.cancel()
                linea.db_set("factura_compra", None)
                linea.db_set("estado_linea", "Pendiente")


# ------------------------------------------------------------------
# Whitelisted API: cargar perfil en el formulario JS
# ------------------------------------------------------------------

@frappe.whitelist()
def buscar_modos_pago_empresa(doctype, txt, searchfield, start, page_len, filters):
    """Devuelve los Modos de Pago que tienen cuenta configurada para la empresa dada."""
    if isinstance(filters, str):
        filters = frappe.parse_json(filters)
    empresa = (filters or {}).get("empresa", "")

    return frappe.db.sql(
        """
        SELECT DISTINCT mpa.parent
        FROM `tabMode of Payment Account` mpa
        INNER JOIN `tabMode of Payment` mp ON mp.name = mpa.parent
        WHERE mpa.company = %(empresa)s
          AND mp.enabled = 1
          AND mpa.parent LIKE %(txt)s
        ORDER BY mpa.parent
        LIMIT %(page_len)s OFFSET %(start)s
        """,
        {
            "empresa": empresa,
            "txt": f"%{txt}%",
            "start": cint(start),
            "page_len": cint(page_len),
        },
    )


@frappe.whitelist()
def cargar_perfil_prorrateo(perfil, monto_total):
    """
    Devuelve las líneas del perfil con montos calculados.
    Llamado desde el cliente JS al cambiar el perfil.
    """
    if not perfil:
        return []

    perfil_doc = frappe.get_doc("Perfil de Prorrateo", perfil)

    if not perfil_doc.activo:
        frappe.throw(_("El perfil <b>{0}</b> está inactivo.").format(perfil))

    monto_total = flt(monto_total)
    lineas = []
    for l in perfil_doc.lineas_prorrateo:
        lineas.append(
            {
                "empresa": l.empresa,
                "porcentaje": flt(l.porcentaje),
                "monto": monto_total * flt(l.porcentaje) / 100.0,
                "centro_costo": l.centro_costo,
                "cuenta_gasto": l.cuenta_gasto,
                "estado_linea": "Pendiente",
            }
        )
    return lineas
