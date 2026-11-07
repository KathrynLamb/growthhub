# FlipWhizz Growth Hub

A Django service that brings new parents to [FlipWhizz](https://flipwhizz.com), a personalised children's book platform. It runs alongside the main Next.js app and talks to it over a JSON API.

It has two parts so far:

1. **Moments.** Pages for the big moments in a young child's life (a new sibling, starting nursery, moving house, a pet dying), each with an educator's note, a sample story you can try with your own child's name, and reading tips. They're written for search, and nothing goes live until a person has reviewed it.
2. **Free printable.** A parent enters their child's first name, age and interests. A background job writes a short story with Claude, builds a draw-your-own storybook PDF, and emails it through Resend.

## Stack

Python 3.12, Django 5.2 LTS, MySQL 8, jQuery, ReportLab, the Anthropic API, the Resend API, Apache + mod_wsgi on Ubuntu, GitHub Actions.

## Design decisions

- **The child's name never goes to the AI provider.** The model writes `{name}` and the server swaps the real name in when building the PDF. Only age, interests and the chosen moment are sent.
- **Minimum data, minimum time** (UK Children's Code). IPs are stored only as salted hashes. A daily job clears names, emails and stories after 30 days. `forget_email` handles erasure requests.
- **No Celery or Redis.** A cron job claims queued requests with `SELECT ... FOR UPDATE SKIP LOCKED`, so overlapping runs never double-process. Failures retry with backoff (5, 10, 20 minutes), stuck jobs are released after 15 minutes, and the generated story is kept between retries so a failed email doesn't pay for a second generation.
- **Cost and abuse limits** per email, per IP and globally per day, counted in the database. A honeypot field stops simple bots. Interests text is cleaned and passed to the model as data, not instructions.
- **Content review.** Moments start as drafts. The admin "Publish" action records who reviewed each one and when.
- **One site for search.** With `PUBLIC_BASE_URL` set, canonical tags, the sitemap, robots.txt and API links all use flipwhizz.com even when the request comes through a proxy.

## Run it locally

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env      # set DJANGO_DEBUG=1; use DB_ENGINE=sqlite for no MySQL
python manage.py migrate
python manage.py seed_moments          # 10 draft moments to review
python manage.py createsuperuser
python manage.py runserver
```

Then publish moments in `/admin/`. Without API keys, the app uses an offline story generator and skips sending email, so everything works with no setup.

Useful commands:

| Command | What it does |
|---|---|
| `process_printables` | Generate and send queued printables (cron, every minute) |
| `purge_printables` | Clear personal data older than 30 days (cron, daily) |
| `preview_printable --name Maisie --moment new-baby-sibling` | Write a sample PDF to `sample-output/` |
| `forget_email parent@example.com` | Erase one parent's data |
| `seed_moments` | Load the starter moments as drafts |

## Tests

```bash
pytest
```

33 tests cover publishing rules, the JSON API, form validation, rate limits, prompt privacy, story parsing, the retry and backoff pipeline, data purging and the health check. CI runs them against MySQL 8 on every push, along with `check --deploy` and a missing-migrations check.

## API

Read-only, public, CORS-enabled, published content only.

| Endpoint | Returns |
|---|---|
| `GET /api/moments/` | `{"count": n, "results": [...]}`. Filter with `?age=1-3`, `3-5` or `5-8` (400 for anything else) |
| `GET /api/moments/<slug>/` | One moment, plus `why_it_helps` and `tips` |
| `GET /healthz` | `{"status": "ok", "database": "up"}`, or 503 if the database is down |

## Operations

- [DEPLOY.md](DEPLOY.md): server setup on DigitalOcean, Apache, HTTPS, cron, and moving to flipwhizz.com/stories
- [RUNBOOK.md](RUNBOOK.md): incident severities, first steps, rollback, and fixes for known failures

Incidents are logged in the admin with impact, root cause and follow-ups.
