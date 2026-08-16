"""
Arma y envía el email diario con las ofertas curadas. Solo informa —
nunca postula ni envía nada a los empleadores.
"""
import os
import smtplib
from datetime import date
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from config import EMAIL_SUBJECT_PREFIX, EMAIL_FROM_NAME


def _render_html(picks: list) -> str:
    if not picks:
        return """
        <p>Hoy no encontré ofertas que realmente valieran la pena según tus criterios.
        Mejor cero postulaciones que postulaciones mediocres — mañana vuelvo a intentar.</p>
        """

    cards = []
    for p in picks:
        flags_html = f'<p style="color:#b45309;margin:4px 0 0;"><b>⚠ {p["flags"]}</b></p>' if p.get("flags") else ""
        cards.append(f"""
        <div style="border:1px solid #e2e8f0;border-radius:10px;padding:16px 20px;margin-bottom:16px;">
          <h3 style="margin:0 0 4px;">{p['title']}</h3>
          <p style="margin:0 0 8px;color:#475569;">
            {p.get('company', 'Empresa no especificada')} · {p.get('location', '')} ·
            <span style="color:#2563eb;">{p.get('source', '')}</span>
          </p>
          <p style="margin:0 0 8px;"><b>Fit: {p.get('fit_score', '?')}/10</b> — {p.get('why', '')}</p>
          {flags_html}
          <a href="{p['url']}" style="display:inline-block;margin-top:8px;color:#2563eb;">Ver oferta →</a>
        </div>
        """)

    return "<div>" + "".join(cards) + "</div>"


def send_daily_email(picks: list):
    smtp_host = os.environ["SMTP_HOST"]
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    smtp_user = os.environ["SMTP_USER"]
    smtp_pass = os.environ["SMTP_PASS"]
    to_addr = os.environ.get("EMAIL_TO", smtp_user)

    today = date.today().strftime("%d-%m-%Y")
    subject = f"{EMAIL_SUBJECT_PREFIX} ({today})"

    html_body = f"""
    <html><body style="font-family:sans-serif;max-width:640px;margin:0 auto;">
      <h2>{subject}</h2>
      <p>Curadas automáticamente, revisadas por vos antes de postular. No se envió nada todavía.</p>
      {_render_html(picks)}
    </body></html>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{EMAIL_FROM_NAME} <{smtp_user}>"
    msg["To"] = to_addr
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.sendmail(smtp_user, [to_addr], msg.as_string())

    print(f"[send_email] Email enviado a {to_addr} con {len(picks)} ofertas.")
