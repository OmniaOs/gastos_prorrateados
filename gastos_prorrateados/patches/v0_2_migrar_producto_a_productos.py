"""Backfill: migra el campo único `producto` a la nueva tabla `productos`.

Para cada Gasto Prorrateado existente que tenga `producto` seteado y aún no
tenga filas en `productos`, crea una fila con ese producto, cantidad 1 y el
monto_total como precio unitario. Conserva los documentos históricos legibles
sin afectar las Purchase Invoices ya generadas.
"""

import frappe
from frappe.utils import flt


def execute():
    # Si la columna vieja no existe (instalación nueva), no hay nada que migrar.
    if not frappe.db.has_column("Gasto Prorrateado", "producto"):
        return

    gastos = frappe.get_all(
        "Gasto Prorrateado",
        filters={"producto": ["is", "set"]},
        fields=["name", "producto", "monto_total", "descripcion"],
    )

    for g in gastos:
        ya_tiene = frappe.db.count("Producto Gasto Prorrateado", {"parent": g.name})
        if ya_tiene:
            continue

        monto = flt(g.monto_total)
        fila = frappe.get_doc(
            {
                "doctype": "Producto Gasto Prorrateado",
                "parent": g.name,
                "parenttype": "Gasto Prorrateado",
                "parentfield": "productos",
                "idx": 1,
                "item_code": g.producto,
                "descripcion": g.descripcion,
                "qty": 1,
                "rate": monto,
                "amount": monto,
            }
        )
        fila.insert(ignore_permissions=True)

    frappe.db.commit()
