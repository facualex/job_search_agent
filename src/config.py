"""
Configuración central del agente de búsqueda de empleo.
Los valores personales (perfil, keywords, países) se leen del entorno o de
profile.md; acá quedan solo los parámetros genéricos del agente.
"""

import os
from pathlib import Path

# --- Instrucciones de búsqueda (perfil + criterios de puntaje + exclusiones) ---
# NO viven en el repo: son configuración privada de cada usuario. Se leen de:
#   1. la variable de entorno JOB_SEARCH_PROFILE (texto completo; así se pasa
#      como Secret en GitHub Actions), o
#   2. el archivo indicado en JOB_SEARCH_PROFILE_FILE (default: profile.md en
#      la raíz del repo, ignorado por git). Ver profile.example.md.
_REPO_ROOT = Path(__file__).resolve().parent.parent


def load_candidate_profile() -> str:
    profile = os.environ.get("JOB_SEARCH_PROFILE", "").strip()
    if profile:
        return profile
    path = Path(os.environ.get("JOB_SEARCH_PROFILE_FILE") or _REPO_ROOT / "profile.md")
    if not path.is_file():
        raise RuntimeError(
            f"No se encontró el perfil de búsqueda: definí JOB_SEARCH_PROFILE o creá {path} "
            "(copiá profile.example.md como punto de partida)."
        )
    return path.read_text(encoding="utf-8").strip()


def _env_list(name: str) -> list:
    return [v.strip() for v in os.environ.get(name, "").split(",") if v.strip()]


# --- Roles a buscar (usados como keywords en las APIs), separados por coma ---
# Ej: SEARCH_KEYWORDS="data engineer,analytics engineer"
SEARCH_KEYWORDS = _env_list("SEARCH_KEYWORDS")

# --- Países donde el candidato puede trabajar, separados por coma. Las ofertas
# con restricción explícita de país que no incluya ninguno de estos se descartan
# antes del LLM (hoy solo Himalayas expone ese dato). Vacío = no filtrar. ---
ALLOWED_COUNTRIES = [c.lower() for c in _env_list("ALLOWED_COUNTRIES")]

# --- Cuántas ofertas curadas se envían por día ---
DAILY_PICKS = 3

# --- fit_score mínimo (1-10, autoasignado por el LLM) para que una oferta
# se incluya en el email. Ofertas con score menor o inválido se descartan
# en vez de rellenar el cupo con matches mediocres. ---
MIN_FIT_SCORE = 6

# --- Cuántas ofertas crudas (pre-filtro LLM) se piden a cada fuente por keyword/categoría ---
RAW_FETCH_LIMIT = 100

# --- Email ---
EMAIL_SUBJECT_PREFIX = "🎯 Tus 3 postulaciones curadas de hoy"
EMAIL_FROM_NAME = "Agente de Búsqueda de Empleo"

# --- Archivo de estado (ofertas ya vistas, para no repetir) ---
SEEN_JOBS_FILE = "seen_jobs.json"
SEEN_JOBS_MAX_AGE_DAYS = 45  # limpieza de entradas viejas del archivo de estado
