# Runbook

What to do when something goes wrong. Log every SEV1 and SEV2 as an Incident in the admin (`/admin/core/incident/`), with root cause and follow-ups once it's fixed.

## Severity

| Level | Meaning | Example | Respond |
|---|---|---|---|
| SEV1 | Site down | `/healthz` failing, 500s on every page | Now |
| SEV2 | A feature is broken | Printables stuck or all failing | Same day |
| SEV3 | Degraded or cosmetic | One moment page has a typo | Next working session |

## First five minutes (any incident)

1. Confirm it: `curl -i https://stories.flipwhizz.com/healthz`
2. Check what changed: `cd /srv/growthhub/app && git log -3 --oneline`
3. Read the latest errors: `tail -50 /var/log/apache2/growthhub-error.log`
4. Open an Incident in the admin with what you know so far.

## Site is down (healthz 503 or no response)

- `503 {"database": "down"}` → `sudo systemctl status mysql`, then `sudo systemctl restart mysql`. Check disk space with `df -h` (a full disk is the usual cause).
- No response → `sudo systemctl status apache2`, `sudo apachectl configtest`, `sudo systemctl restart apache2`.
- 500 errors after a deploy → roll back (below).

## Rolling back a bad deploy

```bash
sudo -iu growthhub && cd /srv/growthhub/app
git log -5 --oneline                 # find the last good commit
git reset --hard <good-commit>
touch config/wsgi.py                 # reload the app
curl -s localhost/healthz -H "Host: stories.flipwhizz.com"
```

If the bad release included a migration, check whether the old code still works with the new schema before rolling back. If not, reverse the migration first: `../venv/bin/python manage.py migrate <app> <previous_migration>`.

## Printables not arriving

1. Admin → Printable requests, filter by status.
2. **Lots of `queued`, none `sent`:** cron isn't running. Check `crontab -l -u growthhub` and `tail /srv/growthhub/logs/printables.log`. Run it by hand: `../venv/bin/python manage.py process_printables`.
3. **`failed` with `Resend error 401/403`:** the Resend key is wrong or the domain isn't verified. Fix `.env`, `touch config/wsgi.py`, then use the admin action **Retry**.
4. **`failed` with `Resend error 429`:** rate limited by Resend. Retries back off automatically (5, 10, 20 minutes).
5. **`failed` with `Invalid JSON` / `Story too short`:** the model returned something unexpected. Try `preview_printable` with the same age and interests. If it keeps happening, check whether the model name in `ANTHROPIC_MODEL` is still valid.
6. **Stuck in `processing`:** released automatically after 15 minutes.

## Cost spike or abuse

- Lower `PRINTABLE_GLOBAL_LIMIT_PER_DAY` in `.env` and `touch config/wsgi.py`. Setting it to `0` turns the printable off without a deploy.
- Look for one `ip_hash` or email with many requests in the admin.

## Data requests (UK GDPR)

- **Delete my data:** `../venv/bin/python manage.py forget_email parent@example.com`
- Everything is cleared automatically after `PRINTABLE_RETENTION_DAYS` (30) by the daily purge.
