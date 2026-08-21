"""
Usa un LLM (proveedor configurable, ver llm_client.py) para evaluar las
ofertas crudas contra el perfil del candidato y elegir las DAILY_PICKS
mejores, con una justificación breve para cada una. Nunca envía ni postula
nada — solo curación y explicación.
"""
import json
import os
from config import CANDIDATE_PROFILE, DAILY_PICKS
from llm_client import complete


def _build_prompt(jobs: list) -> str:
    jobs_json = json.dumps(
        [
            {
                "index": i,
                "title": j["title"],
                "company": j["company"],
                "location": j["location"],
                "remote": j["remote"],
                "source": j["source"],
                "tags": j.get("tags", []),
                "description_snippet": (j.get("description") or "")[:800],
            }
            for i, j in enumerate(jobs)
        ],
        ensure_ascii=False,
        indent=2,
    )

    return f"""Sos un asistente de búsqueda de empleo muy exigente y honesto. Tu tarea es
elegir, de una lista de ofertas crudas, las {DAILY_PICKS} MEJORES para este candidato.

PERFIL DEL CANDIDATO:
{CANDIDATE_PROFILE}

REGLAS DE SELECCIÓN:
- Descartá ofertas junior/trainee/entry-level.
- Descartá ofertas que sean claramente stack legado (NiFi, PowerCenter, Informatica,
  ETL bancario tradicional on-prem) salvo que el salario o la empresa sean excepcionales.
- Priorizá stack cloud-native (dbt, Airflow, Spark, Snowflake, BigQuery, AWS/GCP/Azure, Terraform).
- Solo considerá: (a) 100% remoto para empresas de USA, o (b) remoto/híbrido en Chile con
  buena compensación aparente.
- Si hay menos de {DAILY_PICKS} ofertas que realmente valgan la pena, devolvé menos —
  NUNCA rellenes con ofertas mediocres solo para completar el cupo.

OFERTAS CRUDAS (formato JSON, "index" es el identificador):
{jobs_json}

Respondé EXCLUSIVAMENTE con un JSON válido (sin texto adicional, sin markdown) con esta forma:
{{
  "picks": [
    {{
      "index": <int>,
      "fit_score": <int 1-10>,
      "why": "<1-2 frases explicando por qué encaja, en español, tono directo sin relleno>",
      "flags": "<opcional: alguna alerta u observación honesta, o cadena vacía>"
    }}
  ]
}}
"""


def curate(jobs: list) -> list:
    """Devuelve una lista de dicts: cada uno es una oferta original enriquecida
    con fit_score, why y flags. Longitud <= DAILY_PICKS."""
    if not jobs:
        return []

    prompt = _build_prompt(jobs)
    print(f"[curate] tamaño del prompt: {len(prompt)} caracteres, {len(jobs)} ofertas")

    raw_text = complete(prompt, max_tokens=4000)

    # por si el modelo igual envuelve en ```json ... ```
    if raw_text.startswith("```"):
        raw_text = raw_text.strip("`")
        raw_text = raw_text.split("\n", 1)[1] if "\n" in raw_text else raw_text
        raw_text = raw_text.rsplit("```", 1)[0]

    if os.environ.get("CURATE_DEBUG"):
        print(f"[curate] DEBUG — respuesta cruda del modelo:\n{raw_text}\n")

    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError as e:
        print(f"[curate] ERROR parseando respuesta del modelo: {e}\nRespuesta cruda:\n{raw_text}")
        return []

    if os.environ.get("CURATE_DEBUG"):
        print(f"[curate] DEBUG — {len(parsed.get('picks', []))} picks devueltos por el modelo antes de re-mapear")

    picks = []
    for p in parsed.get("picks", [])[:DAILY_PICKS]:
        idx = p.get("index")
        if idx is None or not (0 <= idx < len(jobs)):
            continue
        enriched = dict(jobs[idx])
        enriched["fit_score"] = p.get("fit_score")
        enriched["why"] = p.get("why", "")
        enriched["flags"] = p.get("flags", "")
        picks.append(enriched)

    return picks
