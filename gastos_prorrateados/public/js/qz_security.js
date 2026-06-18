// qz_security.js — Firma las peticiones QZ Tray para eliminar el diálogo "Untrusted website".
// Colocar en apps/gastos_prorrateados/gastos_prorrateados/public/js/qz_security.js
// y registrar en hooks.py:  app_include_js = ["/assets/gastos_prorrateados/js/qz_security.js"]
//
// Envuelve frappe.ui.form.qz_connect para configurar qz.security
// (certificado + firma vía API del servidor) antes de conectar.

(function () {
	"use strict";

	// El método del servidor; ajustar "<app>" al nombre real de la app
	const QZ_API = {
		certificate: "gastos_prorrateados.qz.get_certificate",
		sign: "gastos_prorrateados.qz.sign",
	};

	function setup_qz_security() {
		if (typeof qz === "undefined" || qz.__omnia_signed) return;
		qz.__omnia_signed = true;

		qz.security.setCertificatePromise(function (resolve, reject) {
			frappe
				.call(QZ_API.certificate)
				.then((r) => resolve(r.message))
				.catch(reject);
		});

		qz.security.setSignatureAlgorithm("SHA512");

		qz.security.setSignaturePromise(function (toSign) {
			return function (resolve, reject) {
				frappe
					.call({ method: QZ_API.sign, args: { request: toSign } })
					.then((r) => resolve(r.message))
					.catch(reject);
			};
		});
	}

	$(document).on("app_ready", function () {
		if (!frappe.ui || !frappe.ui.form || !frappe.ui.form.qz_connect) return;

		const _qz_connect = frappe.ui.form.qz_connect;
		frappe.ui.form.qz_connect = function () {
			const args = arguments;
			return frappe.ui.form.qz_init().then(() => {
				setup_qz_security();
				return _qz_connect.apply(this, args);
			});
		};
	});
})();
