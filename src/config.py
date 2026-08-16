"""
Configuración central del agente de búsqueda de empleo.
Ajustá estos valores para afinar qué tipo de ofertas se buscan y cómo se filtran.
"""

# --- Perfil profesional usado por el LLM para evaluar cada oferta ---
CANDIDATE_PROFILE = """
Data Engineer con ~2 años de experiencia en un stack legado (Apache NiFi, PowerCenter,
MariaDB) en proyectos bancarios. Título de Ingeniería Civil en Computación (UTEM, nota 7.0/7.0).
Certificación en Apache Airflow (Astronomer Fundamentals). Inglés C2.

En transición activa hacia un stack cloud-native: dbt, Airflow, Spark/PySpark, Terraform,
AWS (S3, Athena, Glue), Snowflake/BigQuery. Portfolio propio con pipelines dbt + Airflow +
S3 Medallion + Terraform.

Busca roles de Data Engineer o Analytics Engineer, de nivel mid o superior (no junior/trainee).
Quiere alejarse explícitamente de stacks legado tipo NiFi/PowerCenter/ETL bancario tradicional
salvo que la oferta compense claramente con stack moderno o alto salario.

Acepta dos tipos de posición:
1. 100% remoto para empresas de USA (contrato en USD).
2. Remoto o híbrido en Chile, siempre que la compensación sea buena para el mercado local.

No tiene apuro extremo (tiene trabajo actual), así que prefiere calidad sobre volumen:
mejor 3 ofertas realmente bien evaluadas que muchas mediocres.
"""

# --- Roles a buscar (usados como keywords en las APIs) ---
SEARCH_KEYWORDS = [
    "data engineer",
    "analytics engineer",
]

# --- Cuántas ofertas curadas se envían por día ---
DAILY_PICKS = 3

# --- Cuántas ofertas crudas (pre-filtro LLM) se piden a cada fuente por keyword/categoría ---
RAW_FETCH_LIMIT = 100

# --- Email ---
EMAIL_SUBJECT_PREFIX = "🎯 Tus 3 postulaciones curadas de hoy"
EMAIL_FROM_NAME = "Agente de Búsqueda de Empleo"

# --- Archivo de estado (ofertas ya vistas, para no repetir) ---
SEEN_JOBS_FILE = "seen_jobs.json"
SEEN_JOBS_MAX_AGE_DAYS = 45  # limpieza de entradas viejas del archivo de estado
