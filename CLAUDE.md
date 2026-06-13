# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Lumberjacked is a Django REST Framework backend for a workout tracking app. It exposes a token-authenticated JSON API for managing movements, workouts, and movement logs. The database is PostgreSQL (required — uses `ArrayField` for sets data).

## Commands

**Run locally with a local Postgres container:**
```bash
docker-compose -f docker-compose.local.yml up
```

**Run with the Supabase-hosted dev database:**
```bash
docker-compose -f docker-compose.local-dev-db.yml up
```

**Run all tests:**
```bash
python manage.py test
```

**Run a single test class or method:**
```bash
python manage.py test api.tests.MovementTests
python manage.py test api.tests.MovementTests.test_create_movement
```

**Migrations (run inside the running container):**
```bash
docker exec -it <container_name> python manage.py makemigrations
docker exec -it <container_name> python manage.py migrate
```

Always use `makemigrations` to generate migrations — never write them by hand.

## Environment

Settings load from `local.env` (via `python-dotenv`). Required variables: `DJANGO_SECRET_KEY`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, `POSTGRES_PORT`, `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET`, `GOOGLE_OAUTH_CALLBACK_URL`, and email config vars.

## Architecture

**Two Django apps:**
- `authn/` — custom `User` model (email-based, no username), login/registration via `dj-rest-auth` + `django-allauth`, and Google OAuth2 social login.
- `api/` — the core workout data: `Movement`, `Workout`, `MovementLog` models with full CRUD views.

**URL structure:**
- `/auth/` — registration, login/logout, password, Google OAuth (`authn/urls.py`)
- `/api/` — movements, workouts, movement logs (`api/urls.py`)

**Authentication:** Token-only (`rest_framework.authentication.TokenAuthentication`). `SessionAuthentication` is intentionally excluded to avoid CSRF issues on token endpoints.

**IDs:** All models use `generate_id()` (48-bit random integer from `lumberjacked/utils.py`) as primary keys instead of auto-increment.

**Key data model decisions:**
- `Workout.movements` is a PostgreSQL `ArrayField` storing an ordered list of `Movement` IDs (not a M2M relation). This ordering is preserved in API responses using a `Case/When` ORM sort.
- `MovementLog.reps` and `MovementLog.loads` are both `ArrayField`s — one element per set. They must always have the same length (enforced in `MovementLogSerializer.validate`).

**Workout serializer variants** (`api/serializers.py`):
- `WorkoutWithRecordedLogsSerializer` — used by list/detail views; each movement includes the log recorded *in that workout* (`recorded_log`).
- `WorkoutWithLatestLogsSerializer` — used by `WorkoutCurrent`; each movement includes the most recent log across all workouts, plus a `for_current_workout` boolean flag.

**`attach_movements_details()`** (`api/views.py`) is the key helper that annotates workout instances with `movements_details_prefetched` using a `Subquery + JSONObject` pattern. Both `WorkoutList` and `WorkoutDetail` call it; `WorkoutCurrent` has its own inline variant that adds `for_current_workout`.

**Permissions:** Object-level permission classes (`IsMovementOwner`, `IsMovementLogOwner`, `IsWorkoutOwner`) in `api/permissions.py` enforce user ownership on detail endpoints. Create-time ownership is checked manually in `perform_create`.

**Pagination:** Default page size is 100 (`PAGE_SIZE = 100`).
