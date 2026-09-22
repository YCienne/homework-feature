# Learnairium — Homework Help Service

Step-by-step AI tutoring for Learnairium students: controlled, curriculum-aligned,
and step-gated. Never gives the final answer directly — guides the student to it
one question at a time.

This service is a standalone Python microservice, separate from Learnairium's main
Spring Boot backend. It shares Learnairium's AWS infrastructure (Cognito, Redis,
RDS, S3) but owns its own domain logic and deployment.

## Contents

- [Architecture](#architecture)
- [Tech stack](#tech-stack)
- [How a session works](#how-a-session-works)
- [API reference](#api-reference)
- [LLM providers](#llm-providers)
- [Configuration](#configuration)
- [Database](#database)
- [Local development](#local-development)
- [Testing](#testing)
- [Deployment](#deployment)
- [Integration with the main Learnairium website](#integration-with-the-main-learnairium-website)
- [Known open items](#known-open-items)

## Architecture

```
Student (browser / PWA)
        │  Cognito access token
        ▼
┌───────────────────┐        ┌──────────────────────────┐
│  Learnairium main  │  ───▶  │  homework-service         │
│  site (Spring Boot)│        │  (this repo — FastAPI)    │
└───────────────────┘        └──────────────────────────┘
                                     │        │        │
                                 Redis    MySQL/RDS   S3
                                (sessions) (concept   (image
                                            tags)      uploads)
                                     │
                                LLM provider
                          (Gemini / DeepSeek / Anthropic /
                           Claude Platform on AWS)
```

Both the main site and this service validate the **same Cognito User Pool**
JWTs independently — `homework-service` derives the student identity straight
from the token's `sub` claim, so no separate service-to-service auth scheme is
needed. See [Integration with the main Learnairium website](#integration-with-the-main-learnairium-website)
for the agreed routing pattern.

## Tech stack

| Layer            | Choice                                              |
|-------------------|------------------------------------------------------|
| Language / framework | Python 3.12, FastAPI (async)                      |
| Auth              | AWS Cognito (JWT, validated locally against JWKS)    |
| Session store     | Redis (24h TTL per session)                          |
| Persistent store  | MySQL on AWS RDS (SQLAlchemy async, shared `learnairium` schema) |
| Image storage     | AWS S3                                               |
| LLM providers     | Gemini, DeepSeek, Anthropic (direct API or Claude Platform on AWS) |
| Deployment        | Docker container on EC2 (private subnet, behind ALB) |

## How a session works

1. **`POST /homework/session/start`** — student submits a question (typed, or
   confirmed from an image extraction). Input is validated and sanitised
   (`src/core/validator/input_validator.py`), classified into a subject
   (`subject_classifier.py`), and a `Session` is created in Redis.
2. **`prompt_builder.py`** assembles a system/user prompt pair from
   subject-specific templates (`src/core/prompt/templates/action_templates.py`).
3. **`llm_client.py`** calls the configured provider. **`retry_handler.py`**
   validates the JSON response (`response_validator.py`) against 6 rules
   (schema, step-gating, length, etc.), retries once with a stricter prompt on
   failure, and falls back to a safe canned response rather than ever erroring
   out to the student.
4. Further student actions — `CONTINUE`, `IM_NOT_SURE`, `SHOW_NEXT_STEP`,
   `EXPLAIN_AGAIN` — go through **`POST /homework/session/{id}/action`**,
   repeating the build → call → validate cycle against the session's stored
   step history.
5. On completion, `concept_tracker.py` fire-and-forget writes a struggle-index
   row to the `concept_tags` table — a tracking failure here must never affect
   the student's response.

## API reference

All endpoints require `Authorization: Bearer <Cognito access token>`.

| Method | Path                                | Purpose                                   |
|--------|-------------------------------------|--------------------------------------------|
| POST   | `/homework/image/extract`           | Upload an image, get OCR'd text back for confirmation |
| POST   | `/homework/session/start`           | Start a tutoring session for a question    |
| GET    | `/homework/session/{session_id}`    | Get session state                          |
| POST   | `/homework/session/{session_id}/action` | Advance the session (CONTINUE / IM_NOT_SURE / SHOW_NEXT_STEP / EXPLAIN_AGAIN) |
| GET    | `/homework/usage/{student_id}`      | Daily session usage / remaining quota      |
| GET    | `/health`                           | Liveness check (no auth)                   |

Interactive docs at `/docs` (disabled in production).

## LLM providers

Set via `LLM_PROVIDER` in `.env`:

| Value           | Auth                          | Notes |
|------------------|-------------------------------|-------|
| `anthropic`      | `ANTHROPIC_API_KEY`           | Default. Direct Claude API. |
| `anthropic_aws`  | IAM/SigV4 (AWS credential chain) | Claude Platform on AWS — `CLAUDE_AWS_REGION` + `CLAUDE_AWS_WORKSPACE_ID` required. **The workspace's AWS region only scopes IAM/billing, it does not pin where inference runs** — do not treat region choice alone as a data-residency guarantee (e.g. for POPIA). |
| `gemini`         | `GEMINI_API_KEY`               | |
| `deepseek`       | `DEEPSEEK_API_KEY`             | |

Image OCR (`/homework/image/extract`) uses a separate `IMAGE_EXTRACTION_PROVIDER`
setting (`gemini` or `anthropic`) — vision calls don't go through the text
providers above.

## Configuration

Copy `.env.example` to `.env` and fill in the values below. Full field list
lives in `src/config/settings.py`.

| Group | Key variables |
|-------|----------------|
| LLM | `LLM_PROVIDER`, `*_API_KEY`, `LLM_MODEL_*`, `LLM_TIMEOUT_MS` |
| Claude Platform on AWS | `CLAUDE_AWS_REGION`, `CLAUDE_AWS_WORKSPACE_ID` |
| Cognito | `COGNITO_USER_POOL_ID`, `COGNITO_REGION`, `COGNITO_CLIENT_ID`, `STUDENT_ID_FIELD` |
| Redis | `REDIS_URL`, `REDIS_PASSWORD`, `SESSION_TTL_SECONDS` |
| Database | `DATABASE_URL`, `DATABASE_POOL_SIZE` |
| S3 | `IMAGE_BUCKET_NAME`, `IMAGE_S3_PREFIX`, `IMAGE_MAX_SIZE_MB`, `AWS_REGION` |
| Limits | `DAILY_SESSION_LIMIT`, `MAX_STEPS_DEFAULT`, `MAX_STEPS_HARD_CAP` |
| Service | `ENVIRONMENT`, `PORT`, `LOG_LEVEL` |

**Region policy**: all new AWS resources for this service match Learnairium's
existing region (`af-south-1`), per DevOps sign-off.

**Production AWS auth**: S3 access in production goes through the EC2 instance's
attached IAM role, not static keys — `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY`
are only needed for local development. The same pattern applies to
`anthropic_aws` if its IAM actions are added to that role.

## Database

`concept_tags` lives in the **shared `learnairium` RDS schema** — this service
does not own a separate database. Run `migrations/create_concept_tags.sql`
once against that schema before deploying. One row is written per completed
session; failures to write are logged and swallowed, never surfaced to the
student.

## Local development

```bash
cp .env.example .env   # fill in API keys
docker-compose up
```

This starts `homework-service` (port `2095`), Redis, and a local MySQL
container. `docker-compose.yml`'s own `environment:` block overrides `.env`'s
`REDIS_URL`/`DATABASE_URL` for containerized runs, so local dev is unaffected
by whatever production values are configured in `.env`.

Dev-mode auth bypass: set `DEV_BYPASS_TOKEN` in `.env` (see `.env.example` for how
to generate one), then send `Authorization: Bearer <that value>` to skip real
Cognito validation when `ENVIRONMENT=development` (see `src/api/middleware/auth.py`).
Disabled by default — an empty `DEV_BYPASS_TOKEN` never matches any token.

## Testing

```bash
pytest
```

107 tests — unit tests per module plus integration tests exercising the full
FastAPI request/response cycle. `conftest.py` auto-overrides Cognito auth, the
rate limiter, Redis, and the DB session for every test, so the suite never
needs a real Redis/MySQL/Cognito connection.

## Deployment

Docker container on EC2, in the same private subnet as the rest of
Learnairium's backend infrastructure (not directly internet-facing — reached
via Route 53 → ALB → security groups, same pattern as the main platform).
Redis and RDS are shared with the main platform rather than provisioned
separately for this service.

For a temporary, share-a-link demo deployment (single EC2 instance, self-contained
stack, not the shared infra above), see [docs/HOSTING.md](docs/HOSTING.md).

## Integration with the main Learnairium website

The main site (`https://www.learnairium.ai`, Spring Boot) and this service
share one Cognito User Pool. The agreed integration pattern: Spring Boot acts
as a **BFF/proxy** — it validates the same Cognito JWT, applies its own
business gating (subscription tier, quotas, logging) in front of this service,
then forwards the request with the *same* original access token rather than
minting a new credential. This service's own daily session cap
(`DAILY_SESSION_LIMIT`) is a separate, lower-level abuse-prevention check and
isn't replaced by Spring Boot's gating.

Spring Boot proxies the 5 endpoints listed above under its own `/api/homework/**`
path; the image-upload endpoint needs multipart passthrough, the rest are plain
JSON forwards. Set the `WebClient` timeout comfortably above `LLM_TIMEOUT_MS`
(15s) since LLM calls are the slow path.

## Known open items

- **`DATABASE_URL`** in `.env` has a placeholder for RDS credentials
  (`<DB_USER>:<DB_PASSWORD>`) — DevOps confirmed host/port/schema but not the
  actual login.
- **`CLAUDE_AWS_WORKSPACE_ID`** is still unset — requires creating a workspace
  in the AWS Console (Claude Platform on AWS → Workspaces) first.
- **Data residency / POPIA**: if South African data residency is an actual
  product requirement, region choice (`af-south-1`) does not by itself satisfy
  it for the `anthropic_aws` provider — confirm with Anthropic/legal, or route
  through Amazon Bedrock instead.
- **Subscription-tier session limits**: `DAILY_SESSION_LIMIT` is currently flat
  for all students; differentiating by plan tier is a Product decision still
  open per the requirements doc.
- **Data retention**: no automatic deletion of `concept_tags` rows is
  implemented; the requirements doc recommends a 30-day auto-delete policy —
  needs a decision from Legal/Product before launch.
- **COPPA / GDPR-K**: minimum student age and applicable compliance regime are
  still open questions for Legal — non-negotiable before processing student
  data in production per the requirements doc.
- **Spring Boot proxy code**: not yet written — pending access to the
  Spring Boot repo (package structure, existing Security config, HTTP client
  conventions).
