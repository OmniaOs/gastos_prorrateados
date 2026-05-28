ARG FRAPPE_IMAGE=frappe/erpnext
ARG FRAPPE_VERSION=version-16
FROM ${FRAPPE_IMAGE}:${FRAPPE_VERSION}

USER root

RUN cd /home/frappe/frappe-bench/apps \
    && git clone --depth 1 https://github.com/OmniaOs/gastos_prorrateados.git \
    && /home/frappe/frappe-bench/env/bin/pip install --no-deps \
         -e /home/frappe/frappe-bench/apps/gastos_prorrateados \
    && chown -R frappe:frappe /home/frappe/frappe-bench/apps/gastos_prorrateados

USER frappe
