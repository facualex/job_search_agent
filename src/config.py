"""
Configuración central del agente de búsqueda de empleo.
Ajustá estos valores para afinar qué tipo de ofertas se buscan y cómo se filtran.
"""

# --- Perfil profesional usado por el LLM para evaluar cada oferta ---
CANDIDATE_PROFILE = """
PERFIL
Data Engineer con ~2 años de experiencia profesional en stack legado bancario (Apache NiFi,
Informatica PowerCenter, MariaDB). Ingeniería Civil en Computación, UTEM (nota 7.0/7.0).
Certificación Apache Airflow (Astronomer Fundamentals). Inglés C2.

STACK OBJETIVO (en orden de fit real, no aspiracional)
- Orquestación: Airflow (certificado) > Managed Airflow / Data Factory
- Transformación: dbt (portfolio propio + proyecto dbt sobre NYC Taxi con DuckDB)
- Cloud: AWS (S3, Athena, Glue) es el foco principal de portfolio; Azure (Fabric, Data Factory)
  como stack secundario válido
- Lenguajes/herramientas: PySpark, Terraform, Snowflake/BigQuery (teóricos, sin producción aún)
- Evidencia de skill cloud-native: pipeline propio dbt + Airflow + S3 Medallion (raw/staging/marts)
  + Terraform + Athena + Streamlit, con IaC completo (IAM, budgets, workgroups)

SEÑALES POSITIVAS FUERTES (priorizar)
- Menciona explícitamente dbt, Airflow gestionado (MWAA/Composer/Astronomer), o modern data stack
- Rol "Analytics Engineer" con dbt como herramienta central
- Empresa con equipo de datos ya migrado a cloud (no "estamos empezando a migrar")
- Compensación transparente o rango de mercado claro (no "a convenir")
- Mid-level explícito o "2-4 años de experiencia" como rango

SEÑALES DE EXCLUSIÓN (descartar salvo compensación excepcional)
- Roles centrados en soporte/mantención de ETL tradicional, Informatica, SSIS, Talend
- "Data Engineer" que en la descripción es en realidad DBA, soporte de BI, o analista de reportes
- Bancario/financiero con stack on-prem tradicional (ya es su día a día — no aporta transición)
- Junior/trainee/entry-level, aunque el título diga "Data Engineer"
- Roles que piden 5+ años de experiencia dura en el stack cloud objetivo (no cumple aún, evitar
  ofertas donde el gap de seniority es evidente y no hay señal de que valoren potencial/portfolio)
- Data Scientist / ML Engineer donde el foco es modelado, no pipelines

TIPOS DE POSICIÓN ACEPTADOS
1. 100% remoto, empresa de EE.UU., contrato en USD.
2. Remoto o híbrido en Chile, con compensación competitiva para el mercado local
   (evitar ofertas locales con banda salarial claramente por debajo de mercado para el rol).

CRITERIO DE VOLUMEN
Prioriza calidad sobre cantidad: 3 ofertas bien evaluadas y justificadas por sobre una lista
larga de matches parciales. Si un día no hay ninguna oferta que cumpla los criterios fuertes,
es preferible enviar menos de 3 (o ninguna) antes que rellenar con ofertas mediocres.
No hay urgencia de cambio inmediato — tiene trabajo actual.
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
