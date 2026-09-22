# Interim hosting on a single EC2 instance

This is a **temporary, share-a-link-with-testers** deployment — one EC2 box
running the whole stack from `docker-compose.prod.yml`, behind Caddy for
automatic HTTPS. It is not the [intended production
topology](ARCHITECTURE.md#11-deployment) (shared RDS/Redis, Spring Boot BFF,
real Cognito) — use this to get a working link in front of people quickly,
then tear it down.

## Why this shape

- **One box, one compose file.** No separate RDS/ElastiCache to provision —
  MySQL and Redis run as containers alongside the app, same as local dev.
- **Dev-bypass auth, not Cognito.** Testers won't have Cognito accounts, and
  restricting the link to specific IPs defeats the point of sharing it. See
  [Authentication model](#authentication-model) below for how this is made
  safe enough for a short-lived public demo.
- **Caddy + nip.io for TLS.** [nip.io](https://nip.io) is a public DNS service
  that resolves `<anything>.<your-ip>.nip.io` back to `<your-ip>` — so you get
  a real, publicly resolvable hostname (and therefore a real Let's Encrypt
  certificate) without owning a domain. If you do have a domain, point an A
  record at the instance's Elastic IP instead and use that.

## Authentication model

The frontend and backend both use the existing **dev bypass** (see
`src/api/middleware/auth.py`), not real Cognito — but with two changes from
the repo defaults:

1. **`DEV_BYPASS_TOKEN` is a fresh random secret you generate for this
   deployment, set only in the server's `.env` (never committed).** The old
   hardcoded token (`dev-token-learnarium`) has been in this repo's public git
   history and must never be used again anywhere reachable from the internet.
2. **`DAILY_SESSION_LIMIT` is raised.** All dev-bypass requests share one
   identity (`dev-student-001`), so the daily session cap is shared across
   every tester, not per-person. Raise it (e.g. `100`) for the demo so one
   tester doesn't lock the rest out.

What this buys you: anyone with the hosted **link** can use the app, because
`VITE_DEV_TOKEN` is baked into the frontend's built JS and sent automatically.
Anyone *without* the link has to find both the domain and the token, which
isn't in the public repo. It is not real auth — don't leave it running longer
than you're actively sharing it, and don't put real student data through it.

## 1. Launch the instance

Console steps (the AWS CLI in this environment needs you to re-authenticate
first — see the note at the end if you'd rather I run these instead):

1. **EC2 → Launch instance.**
   - AMI: Ubuntu 22.04 LTS.
   - Instance type: **t3.small** (2 GB RAM — MySQL + Redis + the app + Caddy
     together are tight on the free-tier t2.micro/t3.micro's 1 GB). At
     on-demand pricing (~$0.02/hr) a few days of demo time is a rounding
     error against credits. Use `t3.micro` instead if you want to stay inside
     the literal 750 free hours/month.
   - Storage: 20–30 GB gp3 (30 GB is the free-tier allowance).
   - Key pair: create or reuse one you have the private key for (you'll SSH in).
2. **Security group** — inbound rules:
   - SSH (22) from **your IP only**.
   - HTTP (80) from anywhere — needed for Let's Encrypt's certificate check.
   - HTTPS (443) from anywhere — this is what testers actually use.
   - Nothing else. Do **not** open 2095, 3306, or 6379 — the compose file
     already keeps those off the host network entirely.
3. **Allocate an Elastic IP** and associate it with the instance, so the
   address (and therefore your nip.io hostname) survives a reboot.

## 2. Set up the instance

SSH in, then:

```bash
sudo apt-get update && sudo apt-get install -y ca-certificates curl gnupg git
# Docker Engine + Compose plugin (official convenience script)
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
newgrp docker

# Node, for the one-time frontend build
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs

git clone https://github.com/YCienne/homework-feature.git
cd homework-feature
```

## 3. Configure secrets

```bash
cp .env.example .env
```

Edit `.env` and fill in:

| Key | Value |
|---|---|
| `LLM_PROVIDER` + matching `*_API_KEY` | Pick one provider. DeepSeek or Gemini are cheaper per token than Anthropic if strangers will be poking at it. |
| `DEV_BYPASS_TOKEN` | Generate fresh: `python3 -c "import secrets; print(secrets.token_urlsafe(24))"`. Never reuse a value from git history. |
| `DAILY_SESSION_LIMIT` | Raise from the default `5` — e.g. `100` — since it's shared across every tester (see [Authentication model](#authentication-model)). |
| `MYSQL_ROOT_PASSWORD` | Any random string — only used inside the Docker network. |
| `SITE_ADDRESS` | `<elastic-ip-with-dots-replaced-by-dashes>.nip.io`, e.g. `3-10-20-30.nip.io`. Or your own domain if you have one (point its A record at the Elastic IP first). |

`ENVIRONMENT` should stay `development` — that's what turns the dev bypass on
at all (see [Authentication model](#authentication-model)); it also opens
`/docs`, which is fine to leave on for a demo.

## 4. Build the frontend

The dev token has to be baked into the static build, so this is a real build
step, not just `npm run dev`:

```bash
cd homework-frontend
cat > .env.production <<EOF
VITE_HOMEWORK_API_URL=/homework
VITE_USE_MOCK=false
VITE_DEV_TOKEN=<same value as DEV_BYPASS_TOKEN above>
EOF
npm ci
npm run build
cd ..
```

This produces `homework-frontend/dist/`, which `docker-compose.prod.yml`
mounts straight into the Caddy container.

## 5. Start the stack

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

Then run the one-time migration against the containerized MySQL:

```bash
docker compose -f docker-compose.prod.yml exec -T mysql \
  mysql -uroot -p"$(grep ^MYSQL_ROOT_PASSWORD .env | cut -d= -f2)" \
  < migrations/create_concept_tags.sql
```

Give Caddy a minute to obtain its certificate, then open
`https://<SITE_ADDRESS>/` — that's the link to share. Check logs if anything
looks off: `docker compose -f docker-compose.prod.yml logs -f`.

## 6. When you're done

This is meant to be temporary. When testing wraps up:

```bash
docker compose -f docker-compose.prod.yml down -v   # -v also drops the MySQL volume
```

then stop or terminate the instance and **release the Elastic IP** (it's
billed while unattached) from the EC2 console, so nothing keeps burning
credits after you've stopped using it.

## Provisioning this for you instead

I can run the EC2/security-group steps above directly if you'd rather not do
them by hand — the AWS CLI in this session just needs you to re-authenticate
first (it returned "Unable to refresh login credentials because of a change
in your password" when I checked). Once that's done, tell me and I'll pick up
from step 1.
