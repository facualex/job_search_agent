"""
Punto de entrada del agente. Flujo:
  1. Obtener ofertas crudas de varias fuentes
  2. Descartar las que ya se mostraron antes
  3. Curar con LLM -> top N
  4. Enviar email
  5. Marcar como vistas y guardar estado
No postula ni envía nada a ningún empleador — solo informa por email.

DRY_RUN=1 corta el flujo antes de llamar al modelo y antes de enviar el
email — útil para probar fetch + dedup + estado sin gastar en la API.
"""
import os
from fetch_jobs import fetch_all
from state import load_seen, save_seen, filter_unseen, mark_seen
from curate import curate
from send_email import send_daily_email


def run():
    print("=== Agente de búsqueda de empleo — inicio ===")
    dry_run = bool(os.environ.get("DRY_RUN"))
    if dry_run:
        print("[main] DRY_RUN activo — no se va a llamar al modelo ni a enviar email")

    seen = load_seen()

    raw_jobs = fetch_all()
    print(f"Ofertas crudas totales: {len(raw_jobs)}")

    new_jobs = filter_unseen(raw_jobs, seen)
    print(f"Ofertas nuevas (no vistas antes): {len(new_jobs)}")

    if os.environ.get("CURATE_DEBUG") or dry_run:
        print("[main] ofertas nuevas (candidatas a mandarse al modelo):")
        for j in new_jobs:
            print(f"  - {j['title']} @ {j['company']} | loc={j['location']} | remote={j['remote']} | fuente={j['source']}")

    if dry_run:
        print("=== DRY_RUN — fin (no se llamó al modelo ni se envió email) ===")
        return

    picks = curate(new_jobs)
    print(f"Ofertas curadas seleccionadas: {len(picks)}")
    for p in picks:
        print(f"  - [{p.get('fit_score')}/10] {p['title']} @ {p['company']} ({p['source']})")

    send_daily_email(picks)

    # Solo marcamos como vistas las que se mostraron en el email,
    # para que las no elegidas puedan competir de nuevo mañana.
    mark_seen(picks, seen)
    save_seen(seen)

    print("=== Agente de búsqueda de empleo — fin ===")


if __name__ == "__main__":
    run()
