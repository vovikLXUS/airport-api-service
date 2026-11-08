# Airport Service API

REST API for an airport management system: airports, routes, airplanes, crew,
flights and ticket orders. Django REST Framework, JWT auth, PostgreSQL, Docker.

## Tech stack

Python 3.14 · Django 6.0 · Django REST Framework 3.18 · PostgreSQL 15 ·
simplejwt · drf-spectacular · Pillow · Docker Compose

## Database schema

```
Airport ──< Route >── Airport          source / destination
Route ──< Flight >── Airplane >── AirplaneType
Flight >──< Crew                       many-to-many
Flight ──< Ticket >── Order >── User
```

- `Airplane.seats` and `Crew.full_name` are computed properties.
- `Ticket` is unique on `(flight, row, seat)` and validates the row and seat
  against the airplane capacity.
- `User` is a custom model with `email` as `USERNAME_FIELD`.

## Project architecture

```
API/
├── airport/                  # core domain app
│   ├── migrations/
│   ├── tests/
│   │   ├── test_models.py
│   │   ├── test_serializers.py
│   │   ├── test_views.py
│   │   └── test_permissions.py
│   ├── models.py
│   ├── serializers.py        # separate serializers for list / retrieve / write
│   ├── views.py              # viewsets, filtering, query optimization
│   ├── permissions.py        # IsAdminAllOrIsAuthenticatedReadOnly
│   └── urls.py               # DefaultRouter
├── user/                     # custom user model and auth endpoints
│   ├── tests/
│   ├── models.py             # User with email as USERNAME_FIELD
│   ├── serializers.py
│   ├── views.py
│   └── urls.py
├── airport_service/          # project settings and root urlconf
├── Dockerfile
├── docker-compose.yaml
├── requirements.txt
└── manage.py
```

## Endpoints

| Endpoint | Methods |
|---|---|
| `/api/airport-service/airports/` | GET, POST |
| `/api/airport-service/airports/{id}/` | GET, PUT, PATCH |
| `/api/airport-service/airports/{id}/upload-image/` | POST |
| `/api/airport-service/routes/` | GET, POST |
| `/api/airport-service/crew/` | GET, POST |
| `/api/airport-service/airplane-types/` | GET, POST |
| `/api/airport-service/airplanes/` | GET, POST |
| `/api/airport-service/airplanes/{id}/upload-image/` | POST |
| `/api/airport-service/flights/` | GET, POST |
| `/api/airport-service/orders/` | GET, POST |
| `/api/airport-service/tickets/` | GET, POST |
| `/api/user/register/` | POST |
| `/api/user/token/` `token/refresh/` `token/verify/` | POST |
| `/api/user/me/` | GET, PUT, PATCH |
| `/api/doc/swagger/` `/api/doc/redoc/` `/api/schema/` | GET |

Every resource also has a detail route at `{id}/` with GET, PUT and PATCH.
The flight list includes `tickets_available` — free seats calculated in SQL.

## Filtering

| Resource | Parameters |
|---|---|
| airports | `name`, `city` |
| routes | `source`, `destination`, `from_city`, `to_city`, `min_distance`, `max_distance` |
| crew | `name` (first or last) |
| airplane-types | `name` |
| airplanes | `name`, `airplane_type`, `min_seats`, `max_seats` |
| flights | `routes`, `airplane_type`, `crew`, `date`, `date_from`, `date_to`, `from_city`, `to_city`, `available` |
| orders | `date_from`, `date_to` |
| tickets | `flight`, `order` |

Id parameters accept a comma-separated list. Filters can be combined:

```
GET /api/airport-service/flights/?from_city=kyiv&date_from=2026-11-10&available=true
```

## Authentication

Authentication uses JWT. The access token lives 10 minutes, the refresh token
3 days. Get a token at `POST /api/user/token/` with `email` and `password`, then
send it with every request:

```
Authorization: Bearer <access_token>
```

| Role | Read | Write |
|---|---|---|
| Anonymous | no | no |
| Authenticated | yes | no |
| Staff | yes | yes |

Orders and tickets are the exception: any authenticated user can create them,
and each user sees only their own orders.

Pagination: `LimitOffsetPagination`, default limit 5.
Throttling: 100 requests/day anonymous, 1000/day authenticated.

## Environment variables

Copy `.env.sample` to `.env` and fill it in:

```
SECRET_KEY=your-secret-key
DEBUG=True

POSTGRES_DB=airport
POSTGRES_USER=airport_user
POSTGRES_PASSWORD=your-password
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
PGDATA=/var/lib/postgresql/data
```

Inside Docker Compose `POSTGRES_HOST` is overridden to `db`. Avoid `$` in
`SECRET_KEY` — Compose interpolates it.

## Run with Docker

```
git clone https://github.com/<your-account>/airport-service-api.git
cd airport-service-api
copy .env.sample .env
docker compose up --build
docker compose exec app python manage.py createsuperuser
```

The API is available at `http://127.0.0.1:8000/`.

## Run locally

```
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## Tests

```
python manage.py test
```

Covers computed properties, the upload path builder, seat validation,
serializer switching per action, every filter, the `tickets_available`
annotation, the permission matrix and the JWT flow.

## Notes on the implementation

- Separate serializers per action: lists return related objects as ids, detail
  views expand them.
- `select_related` and `prefetch_related` in `get_queryset` per action — the
  flight list went from 171 queries to a constant number.
- `tickets_available` is annotated with `F()` and `Count(distinct=True)`;
  nothing is counted in Python.
- Seat validation lives in `Ticket.validate_seat()` and is reused by the model
  `clean()` and the serializer `validate()`.
- Images are uploaded through a dedicated `upload-image` action with
  `MultiPartParser`.
- The database service has a `pg_isready` health check, so migrations never
  start before PostgreSQL is ready.
