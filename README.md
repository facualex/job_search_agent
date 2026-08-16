# Agente de búsqueda de empleo

Busca ofertas de Data Engineer / Analytics Engineer en varias fuentes, las filtra
con Claude según tu perfil y criterios, y te manda por email las mejores del día
(por defecto 3, puede ser menos si no hay suficiente calidad).

**No postula automáticamente a nada.** Solo te informa para que revises y postules vos.

## Fuentes de ofertas

- [Remotive](https://remotive.com/) — remoto global, mayoría USA/Europa
- [Arbeitnow](https://www.arbeitnow.com/) — remoto global
- [Get on Board](https://www.getonbrd.com/) — Chile/LATAM, remoto e híbrido

> Nota: son APIs públicas gratuitas de terceros. Si alguna cambia su formato de
> respuesta en el futuro, `fetch_jobs.py` puede necesitar un ajuste — el código
> ya está armado para que si una fuente falla, las otras sigan funcionando.

## Setup

### 1. Cloná esto a tu propio repo de GitHub

Subí esta carpeta a un repo nuevo (puede ser privado) en tu cuenta de GitHub.

### 2. Conseguí las credenciales necesarias

- **ANTHROPIC_API_KEY**: desde [console.anthropic.com](https://console.anthropic.com/settings/keys)
- **Credenciales SMTP** para enviar el email. La opción más simple es Gmail:
  1. Activá verificación en 2 pasos en tu cuenta de Google
  2. Generá una "contraseña de aplicación" en https://myaccount.google.com/apppasswords
  3. `SMTP_HOST=smtp.gmail.com`, `SMTP_PORT=587`, `SMTP_USER=tu correo`, `SMTP_PASS=esa contraseña de app`

### 3. Configurá los Secrets en GitHub

En tu repo: **Settings → Secrets and variables → Actions → New repository secret**.
Agregá estos 6:

```
ANTHROPIC_API_KEY
SMTP_HOST
SMTP_PORT
SMTP_USER
SMTP_PASS
EMAIL_TO
```

### 4. Activá el workflow

El archivo `.github/workflows/daily-job-search.yml` ya está configurado para
correr de lunes a viernes a las 08:00 hora de Chile aprox. (ajustá el cron si
querés otro horario — está en UTC).

También podés correrlo manualmente: pestaña **Actions** → "Daily Job Search" →
**Run workflow**, para probar que todo funciona sin esperar al cron.

## Probar localmente (opcional)

```bash
cd agente-busqueda-empleo
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # y completá los valores
cd src
export $(cat ../.env | xargs)  # carga las variables de entorno
python main.py
```

## Ajustar criterios

Todo el criterio de selección vive en dos lugares:

- `src/config.py` → `CANDIDATE_PROFILE`, `SEARCH_KEYWORDS`, `DAILY_PICKS`
- `src/curate.py` → el prompt que se le manda al modelo (reglas de descarte,
  prioridades de stack, etc.)

Editá el texto de `CANDIDATE_PROFILE` cuando cambien tus prioridades (por
ejemplo, si en el futuro considerás roles de AI Engineer).

## Cómo evita repetir ofertas

`src/state.py` guarda un `seen_jobs.json` con las URLs ya mostradas (con
timestamp). El workflow de GitHub Actions lo commitea de vuelta al repo
después de cada corrida, así que el estado persiste entre ejecuciones. Las
entradas de más de 45 días se limpian automáticamente.

## Limitaciones conocidas

- Las APIs gratuitas no cubren todo el mercado (por ejemplo, no hay una API
  pública estable de LinkedIn — por eso no está incluido, para evitar el
  scraping frágil que ya probaste antes).
- Get on Board cubre bien Chile/LATAM pero puede no tener tantas ofertas
  específicas de Data/Analytics Engineering día a día — es normal que algunos
  días el email tenga menos de 3 ofertas.
- El filtro de "buena compensación" para roles en Chile es aproximado: muchas
  ofertas no publican salario, así que el modelo infiere por empresa/seniority
  cuando no hay dato explícito.
