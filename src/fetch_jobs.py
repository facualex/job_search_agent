"""
Obtiene ofertas de trabajo crudas desde varias fuentes públicas:
- Remotive (remoto global/USA)
- Arbeitnow (remoto global/Europa, incluye muchas ofertas USA-friendly)
- Get on Board (Chile/LATAM, remoto e híbrido)
- Himalayas (remoto global, empresas verificadas, salario estructurado)
- Vacantes Digitales (LATAM tech, agrega desde LinkedIn y otras fuentes)

Cada función devuelve una lista de dicts normalizados con las mismas claves:
    title, company, location, remote, url, description, source, tags, salary
"""
import time
import json
import os
import requests
from config import SEARCH_KEYWORDS, RAW_FETCH_LIMIT

HEADERS = {"User-Agent": "job-search-agent/1.0 (personal use)"}
TIMEOUT = 20


def _title_matches(title: str, keyword: str) -> bool:
    """True si todas las palabras del keyword aparecen en el título,
    sin exigir que estén pegadas (ej. 'data engineer' matchea
    'Senior Data Platform Engineer')."""
    title_lower = (title or "").lower()
    return all(word in title_lower for word in keyword.lower().split())


def _safe_get(url, params=None):
    try:
        resp = requests.get(url, params=params, headers=HEADERS, timeout=TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"[fetch_jobs] WARNING: fallo al consultar {url}: {e}")
        return None


def fetch_remotive():
    """Ofertas remotas globales (mayoría USA/Europa), sin auth.

    Nota: el parámetro `search` de Remotive puede devolver una lista
    genérica/de fallback cuando no hay matches reales (se observó
    job-count idéntico para dos búsquedas distintas). Por eso NO se usa
    `search` — se trae por categoría ("software-dev" y "data", que
    cubre Data/Analytics Engineering) y se filtra por título del lado
    del cliente, igual que con Arbeitnow.
    """
    jobs = []
    seen_urls_this_fetch = set()
    for category in ("software-dev", "data"):
        data = _safe_get(
            "https://remotive.com/api/remote-jobs",
            params={"category": category, "limit": RAW_FETCH_LIMIT},
        )
        if not data:
            continue
        job_count = data.get("job-count")
        print(f"[fetch_jobs] Remotive reporta job-count={job_count} para categoría '{category}'")
        for j in data.get("jobs", []):
            title = j.get("title") or ""
            if not any(_title_matches(title, kw) for kw in SEARCH_KEYWORDS):
                continue
            url = j.get("url")
            if url in seen_urls_this_fetch:
                continue
            seen_urls_this_fetch.add(url)
            jobs.append({
                "title": j.get("title"),
                "company": j.get("company_name"),
                "location": j.get("candidate_required_location"),
                "remote": True,
                "url": url,
                "description": (j.get("description") or "")[:3000],
                "source": "Remotive",
                "tags": j.get("tags", []),
                "salary": j.get("salary") or "",
            })
        time.sleep(0.5)
    return jobs


def fetch_arbeitnow():
    """Ofertas remotas (mayormente Europa, pero muchas abiertas a global)."""
    jobs = []
    data = _safe_get("https://www.arbeitnow.com/api/job-board-api")
    if not data:
        return jobs
    for j in data.get("data", []):
        title = j.get("title") or ""
        if not any(_title_matches(title, kw) for kw in SEARCH_KEYWORDS):
            continue
        jobs.append({
            "title": j.get("title"),
            "company": j.get("company_name"),
            "location": j.get("location"),
            "remote": bool(j.get("remote")),
            "url": j.get("url"),
            "description": (j.get("description") or "")[:3000],
            "source": "Arbeitnow",
            "tags": j.get("tags", []),
            "salary": j.get("salary") or "",
        })
    return jobs


def fetch_getonbrd():
    """Ofertas de Chile/LATAM, remoto e híbrido, vía la API pública de
    Get on Board. El endpoint correcto es /search/jobs (público, sin auth) —
    /jobs es el endpoint PRIVADO que lista los avisos de tu propia empresa
    y requiere una API key de empresa (por eso daba 401).

    Estructura real de cada resultado (formato JSON:API):
      { "id": ..., "type": "job",
        "attributes": { "title": ..., "countries": [...], "remote": bool, ... },
        "links": { "public_url": "..." } }
    Nota: "public_url" vive en "links", NO en "attributes". "company" es una
    relación sin datos embebidos salvo que se pida expand[]=company.
    """
    jobs = []
    for kw in SEARCH_KEYWORDS:
        data = _safe_get(
            "https://www.getonbrd.com/api/v0/search/jobs",
            params={
                "per_page": RAW_FETCH_LIMIT,
                "lang": "es",
                "query": kw,
                "expand[]": "company",
            },
        )
        if not data:
            continue
        entries = data.get("data", data if isinstance(data, list) else [])
        if os.environ.get("FETCH_DEBUG") and entries:
            print(f"[fetch_jobs] DEBUG — primer resultado crudo de GetOnBrd:\n{json.dumps(entries[0], ensure_ascii=False, indent=2)}")
        for j in entries:
            if not isinstance(j, dict):
                continue
            attrs = j.get("attributes", {})
            title = attrs.get("title") or ""
            if not any(_title_matches(title, kw2) for kw2 in SEARCH_KEYWORDS):
                continue  # GetOnBrd matchea sobre descripción también, filtramos por título
            url = (j.get("links") or {}).get("public_url")

            company_rel = (attrs.get("company") or {}).get("data") or {}
            company_name = "Empresa no especificada"
            if isinstance(company_rel, dict):
                company_name = (
                    company_rel.get("attributes", {}).get("name")
                    or company_rel.get("name")
                    or company_name
                )

            countries = attrs.get("countries") or []
            location = ", ".join(countries) if countries else "Remoto"

            jobs.append({
                "title": attrs.get("title"),
                "company": company_name,
                "location": location,
                "remote": bool(attrs.get("remote")),
                "url": url,
                "description": (attrs.get("description") or attrs.get("functions") or "")[:3000],
                "source": "GetOnBrd",
                "tags": [],
                "salary": attrs.get("salary") or "",
            })
        time.sleep(0.5)
    return jobs


def fetch_himalayas():
    """Ofertas remotas globales vía Himalayas — empresas verificadas y
    salario estructurado (minSalary/maxSalary/currency) cuando la empresa
    lo publica.

    Importante: el endpoint es /jobs/api/search, NO /jobs/api (sin
    "/search") — ese segundo endpoint ignora los parámetros de query y
    siempre devuelve el firehose general sin filtrar (se comprobó
    empíricamente). El parámetro "q" ya filtra razonablemente bien del
    lado del servidor; igual se aplica _title_matches como red de
    seguridad, igual que con el resto de las fuentes.

    La API no tiene un booleano "remote" explícito (todo en Himalayas es
    remoto por definición), pero sí expone `locationRestrictions`: la
    lista de países donde el postulante debe estar habilitado para
    trabajar (ej. ["United States"] en ofertas que en el anuncio dicen
    literalmente "United States Only"). Si esa lista no está vacía y no
    incluye Chile, la oferta no aplica al perfil (ver TIPOS DE POSICIÓN
    ACEPTADOS en CANDIDATE_PROFILE) y se descarta acá, antes de llegar al
    LLM o a la notificación.
    """
    jobs = []
    seen_urls_this_fetch = set()
    for kw in SEARCH_KEYWORDS:
        data = _safe_get(
            "https://himalayas.app/jobs/api/search",
            params={"q": kw},
        )
        if not data:
            continue
        for j in data.get("jobs", []):
            title = j.get("title") or ""
            if not _title_matches(title, kw):
                continue
            url = j.get("applicationLink") or j.get("guid")
            if not url or url in seen_urls_this_fetch:
                continue

            locations = j.get("locationRestrictions") or []
            if locations and not any(loc.strip().lower() == "chile" for loc in locations):
                continue

            seen_urls_this_fetch.add(url)

            min_s, max_s, currency = j.get("minSalary"), j.get("maxSalary"), j.get("currency")
            salary = f"{min_s}-{max_s} {currency}" if min_s and max_s else ""

            jobs.append({
                "title": title,
                "company": j.get("companyName"),
                "location": ", ".join(locations) if locations else "Remoto",
                "remote": True,
                "url": url,
                "description": (j.get("description") or j.get("excerpt") or "")[:3000],
                "source": "Himalayas",
                "tags": j.get("categories", []),
                "salary": salary,
            })
        time.sleep(0.5)
    return jobs


def fetch_vacantesdigitales():
    """Ofertas de tecnología en LATAM vía Vacantes Digitales. Agrega
    publicaciones desde LinkedIn y otras fuentes con contenido reescrito;
    el `url`/apply_url puede apuntar a un post de LinkedIn en vez de a la
    página propia de la empresa. No expone un campo de salario estructurado.
    """
    jobs = []
    for kw in SEARCH_KEYWORDS:
        data = _safe_get(
            "https://vacantesdigitales.com/api/search",
            params={"q": kw},
        )
        if not data:
            continue
        for j in data.get("data", []):
            title = j.get("title") or ""
            if not _title_matches(title, kw):
                continue

            company = (j.get("company") or {}).get("name") or "Empresa no especificada"
            location_type = (j.get("location_type") or "").lower()
            title_lower = title.lower()
            is_remote = (
                location_type == "remote"
                or "remoto" in title_lower
                or "remote" in title_lower
            )
            location = j.get("address_locality") or j.get("address_country") or "LATAM"

            jobs.append({
                "title": title,
                "company": company,
                "location": location,
                "remote": is_remote,
                "url": j.get("url"),
                "description": (j.get("content") or j.get("summary") or "")[:3000],
                "source": "VacantesDigitales",
                "tags": j.get("skills", []),
                "salary": "",
            })
    return jobs


def fetch_all():
    """Junta todas las fuentes. Si una falla, sigue con las demás."""
    all_jobs = []
    for fetcher in (fetch_remotive, fetch_arbeitnow, fetch_getonbrd, fetch_himalayas, fetch_vacantesdigitales):
        try:
            found = fetcher()
            print(f"[fetch_jobs] {fetcher.__name__}: {len(found)} ofertas")
            all_jobs.extend(found)
        except Exception as e:
            print(f"[fetch_jobs] ERROR en {fetcher.__name__}: {e}")
    # Descarta entradas sin título o url (datos incompletos)
    all_jobs = [j for j in all_jobs if j.get("title") and j.get("url")]
    # Dedup por URL (puede haber overlap entre keywords o fuentes)
    seen_urls = set()
    deduped = []
    for j in all_jobs:
        if j["url"] in seen_urls:
            continue
        seen_urls.add(j["url"])
        deduped.append(j)
    if len(deduped) != len(all_jobs):
        print(f"[fetch_jobs] Descartados {len(all_jobs) - len(deduped)} duplicados por URL")
    return deduped


if __name__ == "__main__":
    jobs = fetch_all()
    print(f"\nTotal ofertas crudas obtenidas: {len(jobs)}")
    for j in jobs[:5]:
        print("-", j["title"], "@", j["company"], f"[{j['source']}]")
