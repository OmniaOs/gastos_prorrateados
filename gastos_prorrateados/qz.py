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


# -*- coding: utf-8 -*-
# Helper de Jinja para Print Formats "raw printing" (ESC/POS): genera el bloque
# completo de comandos de codigo QR (GS ( k, modelo 2) con el prefijo de longitud
# calculado en tiempo real con chr()/len() reales de Python.
#
# Se expone como metodo global de Jinja (ver hooks.py -> jinja.methods) porque el
# entorno Jinja de Frappe para Print Formats corre en una SandboxedEnvironment que
# NO expone chr()/ord() -- sin este helper no se puede calcular el prefijo de
# longitud (pL/pH) de un payload de tamano variable (p.ej. una URL) directamente
# en la plantilla.
def escpos_qr_command(data, size=6, ec_level=1):
    """Devuelve los comandos ESC/POS (GS ( k) para imprimir `data` como QR."""
    if not isinstance(data, str):
        data = str(data)

    GS = chr(0x1D)

    def _store(cn, fn, payload=""):
        body = cn + fn + payload
        length = len(body)
        pL = chr(length % 256)
        pH = chr(length // 256)
        return GS + "(" + "k" + pL + pH + body

    cmd = ""
    cmd += _store("1", "A", "2" + chr(0))  # seleccionar modelo 2
    cmd += _store("1", "C", chr(size))  # tamano de modulo (1-16)
    cmd += _store("1", "E", chr(0x30 + ec_level))  # nivel de correccion (0=L..3=H)
    cmd += _store("1", "P", chr(0x30) + data)  # guardar datos (m=0)
    cmd += _store("1", "Q", chr(0x30))  # imprimir el simbolo guardado
    return cmd
