# Deploying free on Vercel + Aiven

Cost: £0, and no card needed. About 30 minutes the first time.

- **Vercel (Hobby)** runs the Django app. It finds `manage.py` and deploys from GitHub, like FlipWhizz.
- **Aiven (Free plan)** runs MySQL.
- **GitHub Actions** calls `/internal/cron/` every 15 minutes to retry any printable that failed. Vercel Cron also calls it once a day (the most the free plan allows).

For a full Linux server with Apache instead, see [DEPLOY.md](DEPLOY.md).

## 1. Create the database on Aiven

1. Sign up at aiven.io and create a **MySQL** service on the **Free** plan. Pick the region closest to the UK that's offered.
2. When it's running, open the service's **Overview** page and note the **Host**, **Port**, **User** (usually `avnadmin`), **Password** and **Database name** (usually `defaultdb`).
3. Download the **CA certificate** from the same page. You'll paste its text into an environment variable.

Keep the password out of chats, code and screenshots.

## 2. Create the tables (from your Mac, once)

Save the downloaded certificate as `ca.pem` in the project folder (`*.pem` is git-ignored), then put the Aiven details in your local `.env`:

```bash
DB_ENGINE=mysql
DB_HOST=<aiven host>
DB_PORT=<aiven port>
DB_USER=avnadmin
DB_PASSWORD=<aiven password>
DB_NAME=defaultdb
DB_SSL_CA=ca.pem
DJANGO_SECRET_KEY=<any long random string>
```

Then:

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_moments
python manage.py createsuperuser
```

Run `migrate` again from your Mac whenever a change includes a new migration. It isn't run during Vercel builds, so a build can never change the database by accident.

## 3. Deploy on Vercel

1. In Vercel: **Add New → Project** and import `KathrynLamb/growthhub`. Vercel detects Django on its own.
2. Before the first deploy, add these **Environment Variables**:

| Name | Value |
|---|---|
| `DJANGO_SECRET_KEY` | a new long random string (make one with `python3 -c "import secrets; print(secrets.token_urlsafe(50))"`) |
| `DJANGO_ALLOWED_HOSTS` | `.vercel.app,stories.flipwhizz.com` |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | `https://growthhub.vercel.app,https://stories.flipwhizz.com` (use your real Vercel URL) |
| `DB_ENGINE` | `mysql` |
| `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME` | from Aiven |
| `DB_SSL_CA` | the full certificate text |
| `PRINTABLE_PROCESS_INLINE` | `1` |
| `CRON_SECRET` | another long random string |
| `ANTHROPIC_API_KEY` | your key |
| `RESEND_API_KEY` | your key |
| `IP_HASH_SALT` | another long random string |

3. Deploy. Then open `https://<your-app>.vercel.app/healthz`. You should see `{"status": "ok", "database": "up"}`.

## 4. Turn on the 15-minute retries

In GitHub: repo **Settings → Secrets and variables → Actions → New repository secret**:

- `CRON_URL` = `https://<your-app>.vercel.app/internal/cron/`
- `CRON_SECRET` = the same value as in Vercel

Test it: **Actions → Retry printables → Run workflow**. A green tick means it worked.

## 5. Optional: use stories.flipwhizz.com

In Vercel: **Settings → Domains → add `stories.flipwhizz.com`**. Vercel shows a CNAME record to add in GoDaddy DNS. Add only that record and leave the email records alone.

## How it behaves on Vercel

- When a parent submits the form, the story is written and emailed during that request (about 10 to 20 seconds; the button says "Writing your story..."). If anything fails, the parent still sees the thanks page, and the request is retried with backoff (5, 10, 20 minutes) by the scheduled call.
- The daily data purge runs on the same scheduled call.
- The first visit after a quiet spell can take a couple of seconds while Vercel starts Python.
- Admin is at `/admin/`. Publish the moments there after reviewing them.

## If something's wrong

- **`/healthz` shows 503:** the database details or certificate are wrong. Check the Vercel function logs (Project → Logs).
- **"DisallowedHost" or a 400 on every page:** add your Vercel URL to `DJANGO_ALLOWED_HOSTS`.
- **"CSRF verification failed" on the form or admin login:** add the full `https://` URL to `DJANGO_CSRF_TRUSTED_ORIGINS`.
- **Printables not arriving:** see [RUNBOOK.md](RUNBOOK.md). On Vercel, check the **Retry printables** runs in GitHub Actions too.
