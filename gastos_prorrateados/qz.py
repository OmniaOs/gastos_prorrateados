# -*- coding: utf-8 -*-
# Firma de peticiones QZ Tray para impresión raw sin diálogos.
# Colocar en la app custom del sitio (p.ej. apps/<app>/<app>/qz.py)
#
# La llave y el certificado viven FUERA del código, en el volumen de sites,
# para que sobrevivan rebuilds de imagen:
#   /home/frappe/frappe-bench/sites/qz_certs/qz-private-key.pem
#   /home/frappe/frappe-bench/sites/qz_certs/qz-certificate.crt

import os
from base64 import b64encode

import frappe
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

CERT_DIR = os.path.join(frappe.utils.get_bench_path(), "sites", "qz_certs")
KEY_PATH = os.path.join(CERT_DIR, "qz-private-key.pem")
CERT_PATH = os.path.join(CERT_DIR, "qz-certificate.crt")


@frappe.whitelist()
def get_certificate():
    """Devuelve el certificado público que QZ Tray validará contra override.crt."""
    with open(CERT_PATH) as f:
        return f.read()


@frappe.whitelist()
def sign(request):
    """Firma el challenge de QZ Tray con la llave privada (RSA + SHA512)."""
    if not isinstance(request, str) or not request:
        frappe.throw("Invalid request")

    with open(KEY_PATH, "rb") as f:
        key = serialization.load_pem_private_key(f.read(), password=None)

    signature = key.sign(
        request.encode("utf-8"),
        padding.PKCS1v15(),
        hashes.SHA512(),
    )
    return b64encode(signature).decode("ascii")
