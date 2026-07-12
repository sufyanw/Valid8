# Accessible Travel Assistant

Stateless v1 prototype for recommending US travel providers based on free-text accessibility needs, transportation preference, and trip duration.

## What is implemented

- FastAPI backend with `/api/recommend` async job creation and `/api/recommend/{job_id}` polling.
- In-memory job state with TTL; no database.
- Per-IP in-memory rate limiting for `/api/recommend`, defaulting to 10 requests/hour.
- Gemini REST integration using `GEMINI_API_KEY`.
- Strict response validation: the LLM may only return provider IDs; backend overwrites provider names, policy URLs, booking URLs, and logo URLs from the curated dataset.
- Static curated provider dataset at [app/data/providers.json](/mnt/c/Users/repla/valid8/mockAgent/app/data/providers.json).
- React/Vite frontend served by FastAPI after build.
- Accessible UI basics: semantic labels, fieldsets, keyboard focus states, skip link, live status region, high contrast, reduced-motion-safe styling, and plain-language copy.

## Local setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
npm --prefix frontend install
npm --prefix frontend run build
export GEMINI_API_KEY="your-key"
uvicorn app.main:app --reload
```

Open `http://localhost:8000`.

For local UI/API testing without calling Gemini:

```bash
export ALLOW_FAKE_LLM=true
uvicorn app.main:app --reload
```

The fake mode is deterministic and only exists for development. Production should use Gemini.

## Heroku deployment

Use a single Heroku app with Python and Node buildpacks.

```bash
heroku buildpacks:clear
heroku buildpacks:add heroku/nodejs
heroku buildpacks:add heroku/python
heroku config:set GEMINI_API_KEY="your-key"
heroku config:set GEMINI_MODEL="gemini-flash-latest"
git push heroku main
```

The root `heroku-postbuild` script builds the Vite app into `frontend/dist`, and FastAPI serves that directory.

## Provider dataset notes

Each provider has:

- disability/accessibility category tags;
- official accessibility policy URL;
- official booking/reservation URL;
- duration-sensitive fields for powered mobility devices, service-animal relief planning, medical equipment/medication, and seating/rest;
- `logo_url` pointing to a self-hosted static asset copied into the React build.

The bundled SVG files under [frontend/public/logos](/mnt/c/Users/repla/valid8/mockAgent/frontend/public/logos) are self-hosted provider identifiers. If strict production compliance requires exact official press-kit logo files, replace those SVGs with official assets while keeping the same paths or update `logo_url` values in the dataset.

## Official sources checked

- Delta Accessible Travel Services: https://www.delta.com/us/en/accessible-travel-services/overview
- United Accessibility and Assistance: https://www.united.com/en/us/fly/travel/accessibility-and-assistance.html
- American Airlines Special Assistance: https://www.aa.com/i18n/travel-info/special-assistance/special-assistance.jsp
- Southwest Assistance for Customers with Disabilities: https://support.southwest.com/helpcenter/s/article/Assistance-for-Customers-with-Disabilities
- JetBlue Accessibility Assistance: https://www.jetblue.com/at-the-airport/accessibility-assistance
- Alaska Airlines Accessible Services: https://www.alaskaair.com/content/travel-info/accessible-services/airport-accessibility
- Amtrak Accessible Travel Services: https://www.amtrak.com/accessible-travel-services
- Uber Accessibility: https://www.uber.com/us/en/about/accessibility/
- Lyft Accessibility Statement and rider page: https://www.lyft.com/accessibility and https://www.lyft.com/rider

## API shape

Create a job:

```http
POST /api/recommend
Content-Type: application/json

{
  "needs_description": "I use a powered wheelchair and travel with a service dog.",
  "transport_preferences": "not sure",
  "trip_duration": "5 days",
  "quick_tags": ["mobility", "service_animal"],
  "plain_language": true
}
```

Poll:

```http
GET /api/recommend/{job_id}
```
