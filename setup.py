from setuptools import setup, find_packages

with open("requirements.txt") as f:
    install_requires = f.read().strip().split("\n")

setup(
    name="gastos_prorrateados",
    version="0.1.0",
    description="Módulo de Gastos Prorrateados entre múltiples empresas para ERPNext",
    author="OmniaOS",
    author_email="admin@omniaos.ai",
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    install_requires=install_requires,
)
