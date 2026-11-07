# Deploying the Growth Hub

Target: one DigitalOcean droplet in London running Ubuntu 24.04 LTS, Apache + mod_wsgi, MySQL 8, HTTPS with Let's Encrypt. Plan on about 2 hours the first time.

## 1. Create the droplet

- Basic Droplet, Ubuntu 24.04 LTS, region **London (LON1)**, 2 GB RAM.
- Authentication: **SSH key** (not password).
- Turn on weekly backups.
- In GoDaddy DNS (where flipwhizz.com DNS lives), add an **A record**: `stories` → the droplet's IP.

## 2. Base server setup (as root, once)

```bash
apt update && apt upgrade -y
apt install -y apache2 libapache2-mod-wsgi-py3 mysql-server python3-venv python3-pip git ufw certbot python3-certbot-apache
a2enmod headers wsgi

# Firewall: SSH and web only
ufw allow OpenSSH && ufw allow "Apache Full" && ufw enable

# App user with no password login
adduser --disabled-password --gecos "" growthhub
mkdir -p /srv/growthhub/logs && chown -R growthhub:growthhub /srv/growthhub
```

Note: the `libapache2-mod-wsgi-py3` package is built for Ubuntu's own Python (3.12 on 24.04), so the venv below must use that same `python3`.

## 3. MySQL

```bash
mysql_secure_installation
mysql -u root
```
```sql
CREATE DATABASE growthhub CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'growthhub'@'localhost' IDENTIFIED BY 'a-long-random-password';
GRANT ALL PRIVILEGES ON growthhub.* TO 'growthhub'@'localhost';
FLUSH PRIVILEGES;
```

MySQL only listens on localhost by default. Leave it that way.

## 4. App code (as the growthhub user)

```bash
sudo -iu growthhub
cd /srv/growthhub
git clone https://github.com/<you>/growthhub.git app
python3 -m venv venv
venv/bin/pip install -r app/requirements.txt
cp app/.env.example app/.env && nano app/.env    # fill in secrets, DJANGO_DEBUG=0
chmod 600 app/.env

cd app
../venv/bin/python manage.py migrate
../venv/bin/python manage.py collectstatic --noinput
../venv/bin/python manage.py createsuperuser
../venv/bin/python manage.py seed_moments
../venv/bin/python manage.py check --deploy
```

Make a secret key with: `python3 -c "import secrets; print(secrets.token_urlsafe(50))"`

## 5. Apache and HTTPS (as root)

```bash
cp /srv/growthhub/app/deploy/apache-growthhub.conf /etc/apache2/sites-available/growthhub.conf
a2ensite growthhub && a2dissite 000-default
apachectl configtest && systemctl reload apache2
certbot --apache -d stories.flipwhizz.com --redirect
```

Certbot renews automatically. Check with `certbot renew --dry-run`.

## 6. Background jobs

```bash
crontab -u growthhub /srv/growthhub/app/deploy/crontab
```

This runs `process_printables` every minute and `purge_printables` daily at 03:15.

## 7. Monitoring

- Add `https://stories.flipwhizz.com/healthz` to an uptime monitor (UptimeRobot free tier, or your own status monitor). It returns 503 if the database is down.
- Logs: `/var/log/apache2/growthhub-error.log` and `/srv/growthhub/logs/printables.log`.

## 8. Everyday deploys

```bash
sudo -iu growthhub
cd /srv/growthhub/app && ./deploy/deploy.sh
```

The script pulls `main`, installs, migrates, collects static, reloads, and checks `/healthz`. If the health check fails it prints the rollback command.

## Phase 2: serve at flipwhizz.com/stories

Pages on `flipwhizz.com` build search authority for the main site, while a subdomain is partly treated as separate. When the pages are ready to go under the main domain:

1. Apache: change to `WSGIScriptAlias /stories /srv/growthhub/app/config/wsgi.py` and `Alias /stories/static/ /srv/growthhub/app/staticfiles/`.
2. `.env`: `STATIC_URL=/stories/static/` and `PUBLIC_BASE_URL=https://flipwhizz.com`, then run `deploy.sh`.
3. In the FlipWhizz Next.js app, `next.config.js`:

```js
// next.config.js (add to the existing config)
async rewrites() {
  return [
    { source: "/stories/:path*", destination: "https://stories.flipwhizz.com/stories/:path*" },
  ];
},
```

4. Add `https://flipwhizz.com/stories/sitemap.xml` in Google Search Console.

`PUBLIC_BASE_URL` makes canonical tags, the sitemap, robots.txt and API links all point at flipwhizz.com, so Google sees one site.
