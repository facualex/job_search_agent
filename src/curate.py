"""
Usa un LLM (proveedor configurable, ver llm_client.py) para puntuar cada
oferta cruda contra el perfil del candidato en base a subcriterios
explícitos (stack, seniority, rol, tipo de oferta). fit_score se calcula
en código a partir de esos subscores — el modelo no autoasigna el
puntaje final — y se usa para rankear numéricamente y quedarse con las
DAILY_PICKS mejores por encima de MIN_FIT_SCORE. Nunca envía ni postula
nada — solo curación y explicación.
"""
import json
import os
from config import CANDIDATE_PROFILE, DAILY_PICKS, MIN_FIT_SCORE
from llm_client import complete

# Pesos de los subcriterios sobre los que se calcula fit_score en código
# (no se confía en que el LLM haga la cuenta). Reflejan el orden de
# prioridad implícito en CANDIDATE_PROFILE: stack > seniority > tipo de
# oferta/compensación > literalidad del rol. Deben sumar 1.0.
_SUBSCORE_WEIGHTS = {
    "stack_fit": 0.40,
    "seniority_fit": 0.25,
    "offer_fit": 0.20,
    "role_fit": 0.15,
}

# Score máximo cuando el modelo marca hard_exclusion=true, sin importar
# qué tan bien haya puntuado los subcriterios.
_HARD_EXCLUSION_CAP = 3


def _compute_fit_score(p: dict) -> int | None:
    """Calcula fit_score (1-10) a partir de los subscores que devuelve el
    modelo. Devuelve None si algún subscore falta o es inválido."""
    values = {}
    for key in _SUBSCORE_WEIGHTS:
        v = p.get(key)
        if not isinstance(v, int) or not (1 <= v <= 10):
            return None
        values[key] = v

    weighted = sum(values[key] * weight for key, weight in _SUBSCORE_WEIGHTS.items())
    score = round(weighted)
    if p.get("hard_exclusion"):
        score = min(score, _HARD_EXCLUSION_CAP)
    return max(1, min(10, score))


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
                "salary": j.get("salary") or "no especificado",
                "description": j.get("description") or "",
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

CRITERIOS DE PUNTAJE (asigná cada uno de 1 a 10, siendo honesto y exigente):
- stack_fit: qué tan cloud-native es el stack de la oferta vs. legado (dbt, Airflow
  gestionado, Spark, Snowflake/BigQuery, AWS/Azure/GCP, Terraform = alto; NiFi,
  PowerCenter, ETL bancario on-prem = bajo).
- seniority_fit: qué tan bien calza el nivel pedido con un perfil mid-level de ~2 años
  (explícito "2-4 años" o similar = alto; junior/trainee = bajísimo; pide 5+ años duros
  sin señal de valorar potencial = bajo).
- role_fit: si el trabajo real es ingeniería de pipelines de datos (alto) vs. DBA,
  soporte de BI, analista de reportes, o Data Scientist/ML Engineer centrado en
  modelado (bajo), aunque el título diga "Data Engineer".
- offer_fit: tipo de posición según TIPOS DE POSICIÓN ACEPTADOS del perfil (100% remoto
  para empresa de USA en USD, o remoto/híbrido en Chile = base alta; cualquier otra
  modalidad = base baja).
  IMPORTANTE sobre salario: la mayoría de las ofertas NO especifican salario — si no lo
  especifica, NO lo penalices, evaluá offer_fit solo por tipo de posición y tratá la
  falta de dato como neutral. Si SÍ especifica salario y es competitivo/transparente,
  sumá hasta 2 puntos extra sobre esa base (sin pasar de 10). Si SÍ especifica salario y
  está claramente por debajo de mercado (especialmente en Chile), bajalo.

EXCLUSIÓN DURA — marcá "hard_exclusion": true si aplica CUALQUIERA de estas, sin
importar los subscores:
- Junior/trainee/entry-level, aunque el título diga "Data Engineer".
- Rol bancario/financiero con stack on-prem tradicional, salvo compensación o empresa
  excepcional.
- Es en realidad DBA, soporte de BI o analista de reportes, no ingeniería de pipelines.
- Pide 5+ años duros de experiencia en el stack cloud objetivo sin señal de valorar
  potencial/portfolio.
- Modalidad fuera de TIPOS DE POSICIÓN ACEPTADOS: presencial (sin opción remota) en
  cualquier país, o híbrido/remoto en un país que no sea Chile y la empresa no sea de
  USA. Esto aplica aunque el stack y el rol sean un fit excelente — la modalidad es un
  requisito duro, no un matiz a promediar con el resto.

Si hay menos de {DAILY_PICKS} ofertas que realmente valgan la pena, devolvé menos —
NUNCA rellenes con ofertas mediocres solo para completar el cupo.

OFERTAS CRUDAS (formato JSON, "index" es el identificador):
{jobs_json}

Respondé EXCLUSIVAMENTE con un JSON válido (sin texto adicional, sin markdown) con esta forma:
{{
  "picks": [
    {{
      "index": <int>,
      "stack_fit": <int 1-10>,
      "seniority_fit": <int 1-10>,
      "role_fit": <int 1-10>,
      "offer_fit": <int 1-10>,
      "hard_exclusion": <bool>,
      "why": "<1-2 frases explicando por qué encaja o no, en español, tono directo sin relleno>",
      "flags": "<opcional: alguna alerta u observación honesta, o cadena vacía>"
    }}
  ]
}}
"""


def curate(jobs: list) -> list:
    """Devuelve una lista de dicts: cada uno es una oferta original enriquecida
    con fit_score (calculado en código), los subscores, why y flags, ordenada
    de mayor a menor fit_score. Longitud <= DAILY_PICKS. Descarta picks con
    subscores inválidos o fit_score menor a MIN_FIT_SCORE, aunque eso deje la
    lista corta."""
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

    candidates = []
    for p in parsed.get("picks", []):
        idx = p.get("index")
        if idx is None or not (0 <= idx < len(jobs)):
            continue

        fit_score = _compute_fit_score(p)
        if fit_score is None:
            print(f"[curate] descartado index={idx}: subscores inválidos ({p!r})")
            continue
        if fit_score < MIN_FIT_SCORE:
            print(f"[curate] descartado index={idx}: fit_score={fit_score} < MIN_FIT_SCORE={MIN_FIT_SCORE}")
            continue

        enriched = dict(jobs[idx])
        enriched["fit_score"] = fit_score
        enriched["stack_fit"] = p.get("stack_fit")
        enriched["seniority_fit"] = p.get("seniority_fit")
        enriched["role_fit"] = p.get("role_fit")
        enriched["offer_fit"] = p.get("offer_fit")
        enriched["why"] = p.get("why", "")
        enriched["flags"] = p.get("flags", "")
        candidates.append(enriched)

    # Ranking numérico real: ordena por fit_score (calculado en código, no
    # autoasignado por el modelo) y se queda con las DAILY_PICKS mejores.
    candidates.sort(key=lambda c: c["fit_score"], reverse=True)
    return candidates[:DAILY_PICKS]
