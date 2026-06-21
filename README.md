# Gastos Prorrateados para ERPNext

Módulo Frappe/ERPNext que permite distribuir un gasto entre múltiples empresas según porcentajes configurables, generando automáticamente las **Purchase Invoices** y, opcionalmente, los **Payment Entries** correspondientes en cada empresa.

## Características

- **Distribución porcentual** — Define cuánto absorbe cada empresa del gasto total. Los porcentajes deben sumar exactamente 100%.
- **Perfiles de prorrateo** — Guarda distribuciones frecuentes como plantillas reutilizables para cargarlas con un clic.
- **Generación automática de facturas** — Al enviar el documento se crean Purchase Invoices en cada empresa con su monto, cuenta de gasto y centro de costo correctos.
- **Pago inmediato** — Opción para generar Payment Entries en el mismo flujo, sin pasos adicionales.
- **Pago global o por empresa** — El modo de pago, cuenta bancaria y referencia se pueden configurar una sola vez para todas las empresas, o individualmente por empresa.
- **Filtros inteligentes** — Al seleccionar el modo de pago por empresa, el buscador muestra solo los modos que tienen cuenta configurada en esa empresa.
- **Formulario progresivo** — Las secciones del formulario aparecen conforme se completan los pasos previos, guiando al usuario de forma natural.
- **Cancelación en cascada** — Al cancelar un Gasto Prorrateado se anulan automáticamente los Payment Entries y luego las Purchase Invoices relacionadas.

## Requisitos

| Dependencia | Versión mínima |
|---|---|
| ERPNext | v16 |
| Frappe | v16 |

## Instalación

```bash
# Desde el directorio del bench
bench get-app https://github.com/OmniaOs/erpnext-gastos-prorrateados.git
bench --site <tu-sitio> install-app gastos_prorrateados
bench --site <tu-sitio> migrate
```

## Uso rápido

### 1. Crear un Perfil de Prorrateo (opcional)

Navega a **Gastos Prorrateados → Perfil de Prorrateo** y define la distribución porcentual por empresa que usarás frecuentemente.

### 2. Crear un Gasto Prorrateado

1. Ve a **Gastos Prorrateados → Gasto Prorrateado → Nuevo**.
2. Completa **Proveedor** y **Fecha**.
3. Agrega uno o más **Productos** en la tabla, con su cantidad y precio unitario. El **Monto Total** se calcula automáticamente como la suma de los importes.
4. Carga un **Perfil de Prorrateo** o agrega las líneas manualmente con empresa y porcentaje.
5. (Opcional) Activa **Marcar como pagado al generar** para crear los pagos en el mismo paso.
6. Envía el documento.

ERPNext creará automáticamente una Purchase Invoice por cada empresa. Cada factura incluye **todos los productos del gasto**, prorrateados según el porcentaje de la empresa (se conserva la cantidad y se escala el precio unitario, de modo que el importe de cada línea = importe del producto × porcentaje). La cuenta de gasto de cada producto se resuelve por sus Item Defaults en esa empresa (o el override de cuenta de la línea).

> **Fechas anteriores (backdating):** la **Fecha** del gasto se propaga como `posting_date` a las Purchase Invoices y Payment Entries generadas, incluso si es una fecha pasada (los documentos se crean con `set_posting_time = 1`). Si ERPNext rechaza una fecha anterior, revisa que: (1) caiga dentro de un **Año Fiscal activo** de la empresa (de lo contrario: `FiscalYearError`), y (2) no esté antes de **"Contabilidad congelada hasta"** (Accounts Settings → *Accounts Frozen Upto*). Ambos son configuración del ERP, no del módulo.

### 3. Actualizar el módulo

```bash
bench get-app gastos_prorrateados  # o git pull en el directorio del app
bench --site <tu-sitio> migrate
```

## Estructura del módulo

```
gastos_prorrateados/
├── gastos_prorrateados/
│   ├── doctype/
│   │   ├── gasto_prorrateado/       # DocType principal (submittable)
│   │   ├── producto_gasto_prorrateado/ # Child: productos del gasto (item, qty, rate)
│   │   ├── linea_gasto_prorrateado/ # Child: distribución por empresa
│   │   ├── linea_pago_empresa/      # Child: configuración de pago por empresa
│   │   ├── perfil_de_prorrateo/     # Plantillas de distribución
│   │   └── linea_de_prorrateo/      # Child: líneas del perfil
│   ├── fixtures/
│   │   └── custom_field.json        # Custom fields en Purchase Invoice y Payment Entry
│   └── hooks.py
├── setup.py
└── requirements.txt
```

## Custom Fields que instala

El módulo agrega los siguientes campos a DocTypes estándar de ERPNext:

| DocType | Campo | Descripción |
|---|---|---|
| Purchase Invoice | `gasto_prorrateado` | Referencia al documento origen |
| Purchase Invoice | `porcentaje_aplicado` | Porcentaje que representa esta factura |
| Payment Entry | `gasto_prorrateado` | Referencia al documento origen |
| Payment Entry | `empresa_prorrateada` | Empresa a la que corresponde el pago |

## Licencia

MIT — © OmniaOS
