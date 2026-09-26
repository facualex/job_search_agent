# Agente de búsqueda de empleo

Busca ofertas de Data Engineer / Analytics Engineer en varias fuentes, las filtra
con un LLM (Claude o DeepSeek, configurable) según tu perfil y criterios, y te
manda por email las mejores del día (por defecto 3, puede ser menos si no hay
suficiente calidad).

**No postula automáticamente a nada.** Solo te informa para que revises y postules tú.

## Fuentes de ofertas

- [Remotive](https://remotive.com/) — remoto global, mayoría USA/Europa
- [Arbeitnow](https://www.arbeitnow.com/) — remoto global
- [Get on Board](https://www.getonbrd.com/) — Chile/LATAM, remoto e híbrido

> Nota: son APIs públicas gratuitas de terceros. Si alguna cambia su formato de
> respuesta en el futuro, `fetch_jobs.py` puede necesitar un ajuste — el código
> ya está preparado para que si una fuente falla, las otras sigan funcionando.

## Configuración inicial

### 1. Clona este repositorio a tu propia cuenta de GitHub

Sube esta carpeta a un repositorio nuevo (puede ser privado) en tu cuenta de GitHub.

### 2. Consigue las credenciales necesarias

- **API key del LLM** — solo necesitas la del proveedor que vayas a usar:
  - Anthropic (Claude): **ANTHROPIC_API_KEY** desde [console.anthropic.com](https://console.anthropic.com/settings/keys)
  - DeepSeek: **DEEPSEEK_API_KEY** desde [platform.deepseek.com](https://platform.deepseek.com/api_keys)
- **Credenciales SMTP** para enviar el email. La opción más simple es Gmail:
  1. Activa la verificación en 2 pasos en tu cuenta de Google
  2. Genera una "contraseña de aplicación" en https://myaccount.google.com/apppasswords
  3. `SMTP_HOST=smtp.gmail.com`, `SMTP_PORT=587`, `SMTP_USER=tu correo`, `SMTP_PASS=esa contraseña de aplicación`

### 3. Configura los Secrets en GitHub

En el repositorio: **Settings → Secrets and variables → Actions → New repository secret**.
Agrega `LLM_PROVIDER` (`anthropic` o `deepseek`), la API key del proveedor elegido,
los 5 de SMTP/email y los de búsqueda:

```
LLM_PROVIDER
ANTHROPIC_API_KEY   # si LLM_PROVIDER=anthropic
DEEPSEEK_API_KEY    # si LLM_PROVIDER=deepseek
SMTP_HOST
SMTP_PORT
SMTP_USER
SMTP_PASS
EMAIL_TO
JOB_SEARCH_PROFILE  # contenido completo de tu profile.md (ver "Ajustar criterios")
SEARCH_KEYWORDS     # ej: data engineer,analytics engineer
ALLOWED_COUNTRIES   # ej: Chile (opcional; vacío = no filtrar por país)
```

### 4. Activa el workflow

El archivo `.github/workflows/daily-job-search.yml` ya está configurado para
correr todos los días a las 08:00 hora de Chile aprox. (ajusta el cron si
quieres otro horario — está en UTC).

También se puede ejecutar manualmente: pestaña **Actions** → "Daily Job Search" →
**Run workflow**, para comprobar que todo funciona sin esperar al cron.

## Probar localmente (opcional)

```bash
cd agente-busqueda-empleo
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # y completa los valores
cp profile.example.md profile.md  # y completa tu perfil de búsqueda
cd src
set -a; source ../.env; set +a  # carga las variables de entorno
python main.py
```

## Ajustar criterios

El criterio de búsqueda es configuración privada de cada usuario y **no vive en
el repositorio**:

- **Perfil + criterios de evaluación** (stack objetivo, señales positivas,
  exclusiones duras, tipos de posición aceptados, cómo puntuar cada subcriterio):
  un texto libre que se inserta en el prompt del modelo. Se lee de la variable
  `JOB_SEARCH_PROFILE` si está definida (así se usa en GitHub Actions, como
  Secret multilínea), o si no del archivo `profile.md` en la raíz del repo
  (ignorado por git; se puede cambiar la ruta con `JOB_SEARCH_PROFILE_FILE`).
  Usá `profile.example.md` como plantilla.
- **`SEARCH_KEYWORDS`**: roles a buscar en las APIs, separados por coma.
- **`ALLOWED_COUNTRIES`**: países donde podés trabajar; descarta antes del LLM
  las ofertas restringidas a otros países.

Cuando cambien tus prioridades, editá tu `profile.md` y actualizá el Secret
`JOB_SEARCH_PROFILE` con el mismo contenido.

En el código (`src/config.py`, `src/curate.py`) solo quedan los parámetros
genéricos (`DAILY_PICKS`, `MIN_FIT_SCORE`, pesos de los subcriterios) y la
estructura del prompt.

## Cambiar de proveedor de LLM

El proveedor se elige con la variable de entorno `LLM_PROVIDER` (`anthropic` o
`deepseek`, por defecto `anthropic`). Solo se necesita la API key del proveedor
elegido. Opcionalmente `LLM_MODEL` fuerza un modelo específico; si no se
define, se usa el valor por defecto de cada proveedor (`claude-sonnet-5` /
`deepseek-chat`). La lógica vive en `src/llm_client.py` — para agregar otro
proveedor, se debe sumar una entrada en `PROVIDERS` y su función `_complete_<nombre>`.

## Cómo evita repetir ofertas

`src/state.py` guarda un `seen_jobs.json` con las URLs ya mostradas (con
timestamp). El workflow de GitHub Actions lo confirma de vuelta al repositorio
después de cada ejecución, así que el estado persiste entre corridas. Las
entradas de más de 45 días se limpian automáticamente.

## Limitaciones conocidas

- Las APIs gratuitas no cubren todo el mercado (por ejemplo, no hay una API
  pública estable de LinkedIn — por eso no está incluida, para evitar el
  scraping frágil).
- Get on Board cubre bien Chile/LATAM pero puede no tener tantas ofertas
  específicas de Data/Analytics Engineering día a día — es normal que algunos
  días el email tenga menos de 3 ofertas.
- El filtro de "buena compensación" para roles en Chile es aproximado: muchas
  ofertas no publican salario, así que el modelo infiere por empresa/seniority
  cuando no hay dato explícito.
