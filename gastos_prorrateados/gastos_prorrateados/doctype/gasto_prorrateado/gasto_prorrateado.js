// Copyright (c) 2024, OmniaOS and contributors
// For license information, please see license.txt

frappe.ui.form.on("Gasto Prorrateado", {

    // ------------------------------------------------------------------
    // Setup inicial
    // ------------------------------------------------------------------
    setup: function (frm) {
        // Filtrar cuenta de gasto por empresa en la child table
        frm.set_query("cuenta_gasto", "lineas_gasto", function (doc, cdt, cdn) {
            let row = locals[cdt][cdn];
            return {
                filters: {
                    company: row.empresa,
                    account_type: "Expense Account",
                    is_group: 0,
                }
            };
        });

        // Filtrar centro de costo por empresa en la child table
        frm.set_query("centro_costo", "lineas_gasto", function (doc, cdt, cdn) {
            let row = locals[cdt][cdn];
            return {
                filters: {
                    company: row.empresa,
                    is_group: 0,
                }
            };
        });

        // Filtrar cuenta bancaria global
        frm.set_query("cuenta_bancaria", function () {
            return { filters: { is_company_account: 1 } };
        });

        // Filtrar modo de pago en la tabla por empresa
        frm.set_query("modo_pago", "pagos_por_empresa", function (doc, cdt, cdn) {
            let row = locals[cdt][cdn];
            return {
                query: "gastos_prorrateados.gastos_prorrateados.doctype.gasto_prorrateado.gasto_prorrateado.buscar_modos_pago_empresa",
                filters: { empresa: row.empresa }
            };
        });

        // Filtrar cuenta bancaria en la tabla por empresa
        frm.set_query("cuenta_bancaria", "pagos_por_empresa", function (doc, cdt, cdn) {
            let row = locals[cdt][cdn];
            return { filters: { is_company_account: 1, company: row.empresa } };
        });
    },

    // ------------------------------------------------------------------
    // Refresh
    // ------------------------------------------------------------------
    refresh: function (frm) {
        frm.trigger("pago_inmediato");
        frm.trigger("pago_por_empresa");
        frm.trigger("actualizar_indicador_porcentaje");

        // Botones de acceso rápido a documentos generados (solo en modo lectura)
        if (frm.doc.docstatus === 1) {
            frm.add_custom_button(__("Ver Facturas de Compra"), function () {
                frappe.set_route("List", "Purchase Invoice", {
                    gasto_prorrateado: frm.doc.name,
                });
            }, __("Documentos"));

            if (frm.doc.estado === "Pagado") {
                frm.add_custom_button(__("Ver Entradas de Pago"), function () {
                    frappe.set_route("List", "Payment Entry", {
                        gasto_prorrateado: frm.doc.name,
                    });
                }, __("Documentos"));
            }
        }
    },

    // ------------------------------------------------------------------
    // Campos de cabecera
    // ------------------------------------------------------------------
    perfil_prorrateo: function (frm) {
        if (!frm.doc.perfil_prorrateo) return;

        if (!frm.doc.monto_total) {
            frappe.msgprint(__("Ingrese el Monto Total antes de cargar el perfil."));
            return;
        }

        frappe.call({
            method: "gastos_prorrateados.gastos_prorrateados.doctype.gasto_prorrateado.gasto_prorrateado.cargar_perfil_prorrateo",
            args: {
                perfil: frm.doc.perfil_prorrateo,
                monto_total: frm.doc.monto_total,
            },
            callback: function (r) {
                if (!r.message || !r.message.length) return;

                frm.clear_table("lineas_gasto");
                r.message.forEach(function (linea) {
                    let row = frm.add_child("lineas_gasto");
                    row.empresa = linea.empresa;
                    row.porcentaje = linea.porcentaje;
                    row.monto = linea.monto;
                    row.centro_costo = linea.centro_costo;
                    row.cuenta_gasto = linea.cuenta_gasto;
                    row.estado_linea = "Pendiente";
                });
                frm.refresh_field("lineas_gasto");
                frm.trigger("actualizar_indicador_porcentaje");
            }
        });
    },

    monto_total: function (frm) {
        frm.trigger("recalcular_montos");
    },

    moneda: function (frm) {
        // Refrescar campos Currency en la tabla para que respeten la moneda
        frm.refresh_field("lineas_gasto");
    },

    // ------------------------------------------------------------------
    // Pago inmediato (POS)
    // ------------------------------------------------------------------
    pago_inmediato: function (frm) {
        let activo = frm.doc.pago_inmediato;
        frm.toggle_display("pago_por_empresa", activo);
        if (!activo) {
            frappe.model.set_value(frm.doctype, frm.docname, "pago_por_empresa", 0);
        }
        frm.trigger("pago_por_empresa");
    },

    pago_por_empresa: function (frm) {
        let activo = frm.doc.pago_inmediato;
        let porEmpresa = frm.doc.pago_por_empresa;
        let mostrarGlobal = activo && !porEmpresa;
        frm.toggle_display(["modo_pago", "cuenta_bancaria", "referencia_pago"], mostrarGlobal);
        frm.toggle_reqd("modo_pago", mostrarGlobal);

        // Auto-poblar la tabla de pagos desde las líneas de distribución
        if (activo && porEmpresa) {
            frm.trigger("sincronizar_pagos_por_empresa");
        }
    },

    sincronizar_pagos_por_empresa: function (frm) {
        let empresasEnPagos = new Set(
            (frm.doc.pagos_por_empresa || []).map(r => r.empresa)
        );
        let empresasEnLineas = (frm.doc.lineas_gasto || [])
            .map(r => r.empresa)
            .filter(Boolean);

        // Agregar filas faltantes
        let agregado = false;
        empresasEnLineas.forEach(function (empresa) {
            if (!empresasEnPagos.has(empresa)) {
                let row = frm.add_child("pagos_por_empresa");
                row.empresa = empresa;
                agregado = true;
            }
        });

        // Eliminar filas huérfanas (empresa removida de lineas_gasto)
        let lineasSet = new Set(empresasEnLineas);
        (frm.doc.pagos_por_empresa || []).forEach(function (row) {
            if (row.empresa && !lineasSet.has(row.empresa)) {
                frm.get_field("pagos_por_empresa").grid.delete_row(row);
            }
        });

        if (agregado || frm.doc.pagos_por_empresa.length !== empresasEnLineas.length) {
            frm.refresh_field("pagos_por_empresa");
        }
    },

    // ------------------------------------------------------------------
    // Helpers internos
    // ------------------------------------------------------------------
    recalcular_montos: function (frm) {
        (frm.doc.lineas_gasto || []).forEach(function (linea) {
            frappe.model.set_value(
                linea.doctype,
                linea.name,
                "monto",
                flt(frm.doc.monto_total) * flt(linea.porcentaje) / 100
            );
        });
        frm.refresh_field("lineas_gasto");
        frm.trigger("actualizar_indicador_porcentaje");
    },

    actualizar_indicador_porcentaje: function (frm) {
        let total = 0;
        (frm.doc.lineas_gasto || []).forEach(function (linea) {
            total += flt(linea.porcentaje);
        });
        total = Math.round(total * 10000) / 10000;

        let color = Math.abs(total - 100) < 0.01 ? "green" : "red";
        let icono = Math.abs(total - 100) < 0.01 ? "✓" : "✗";
        let mensaje = `${icono} Porcentaje total: <b>${total}%</b> ${Math.abs(total - 100) < 0.01 ? "" : "(debe ser 100%)"}`;

        // Mostrar en el área de ayuda de la sección
        if (!frm.fields_dict["lineas_gasto"]) return;
        let wrapper = frm.fields_dict["lineas_gasto"].$wrapper;
        wrapper.find(".porcentaje-indicador").remove();
        wrapper.prepend(
            `<div class="porcentaje-indicador" style="color:${color};padding:4px 8px;font-size:12px;">${mensaje}</div>`
        );
    }
});

// ------------------------------------------------------------------
// Eventos de la child table
// ------------------------------------------------------------------
frappe.ui.form.on("Linea Gasto Prorrateado", {

    porcentaje: function (frm, cdt, cdn) {
        let linea = locals[cdt][cdn];
        frappe.model.set_value(
            cdt, cdn, "monto",
            flt(frm.doc.monto_total) * flt(linea.porcentaje) / 100
        );
        frm.trigger("actualizar_indicador_porcentaje");
    },

    lineas_gasto_remove: function (frm) {
        frm.trigger("actualizar_indicador_porcentaje");
        if (frm.doc.pago_inmediato && frm.doc.pago_por_empresa) {
            frm.trigger("sincronizar_pagos_por_empresa");
        }
    },

    lineas_gasto_add: function (frm) {
        frm.trigger("actualizar_indicador_porcentaje");
        if (frm.doc.pago_inmediato && frm.doc.pago_por_empresa) {
            frm.trigger("sincronizar_pagos_por_empresa");
        }
    },

    empresa: function (frm, cdt, cdn) {
        // Al cambiar empresa, limpiar campos que dependen de ella
        frappe.model.set_value(cdt, cdn, "centro_costo", null);
        frappe.model.set_value(cdt, cdn, "cuenta_gasto", null);
        if (frm.doc.pago_inmediato && frm.doc.pago_por_empresa) {
            frm.trigger("sincronizar_pagos_por_empresa");
        }
    }
});
