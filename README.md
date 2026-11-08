# Airport Service API

REST API for an airport management system: airports, routes, airplanes, crew,
flights and ticket orders. Built with Django REST Framework, JWT authentication
and PostgreSQL, fully containerized with Docker.

---

## Table of contents

- [Features](#features)
- [Tech stack](#tech-stack)
- [Database schema](#database-schema)
- [Project structure](#project-structure)
- [API endpoints](#api-endpoints)
- [Filtering](#filtering)
- [Authentication and permissions](#authentication-and-permissions)
- [Design decisions](#design-decisions)
- [Environment variables](#environment-variables)
- [Getting started with Docker](#getting-started-with-docker)
- [Getting started locally](#getting-started-locally)
- [Running tests](#running-tests)
- [API documentation](#api-documentation)

---

## Features

- Full CRUD for airports, routes, airplane types, airplanes, crew and flights
- Ticket orders bound to the authenticated user
- JWT authentication with a custom user model (email instead of username)
- Role-based access: admins write, authenticated users read
- Rich filtering on every list endpoint (dates, cities, capacity, seat availability)
- `tickets_available` calculated on the database side for every flight
- Image upload for airports and airplanes
- OpenAPI schema with Swagger UI and ReDoc
- Rate limiting and pagination out of the box
- Test suite covering models, serializers, views and permissions

---

## Tech stack

| Layer | Technology |
|---|---|
| Language | Python 3.14 |
| Framework | Django 6.0, Django REST Framework 3.18 |
| Database | PostgreSQL 15 (SQLite for quick local runs) |
| Auth | djangorestframework-simplejwt 5.5 |
| Docs | drf-spectacular 0.30 (OpenAPI 3) |
| Images | Pillow 12 |
| Containers | Docker, Docker Compose |
| Profiling | django-debug-toolbar |
| Code style | flake8, black |

---

## Database schema

```
Airport ──< Route >── Airport          source / destination
Route ──< Flight >── Airplane
Airplane >── AirplaneType
Flight >──< Crew                       many-to-many
Flight ──< Ticket >── Order
Order >── User
```

| Model | Key fields | Notes |
|---|---|---|
| `Airport` | `name`, `closest_big_city`, `image` | |
| `Route` | `source`, `destination`, `distance` | two FKs to `Airport` with different `related_name` |
| `AirplaneType` | `name` | |
| `Airplane` | `name`, `rows`, `seats_in_row`, `airplane_type`, `image` | `seats` is a computed property |
| `Crew` | `first_name`, `last_name` | `full_name` is a computed property |
| `Flight` | `route`, `airplane`, `departure_time`, `arrival_time`, `crew` | `crew` is M2M |
| `Order` | `created_at`, `user` | ordered newest first |
| `Ticket` | `row`, `seat`, `flight`, `order` | unique together: flight + row + seat |

---

## Project structure

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

---

## API endpoints

### Airport service

| Method | Endpoint | Description |
|---|---|---|
| GET / POST | `/api/airport-service/airports/` | list / create airports |
| GET / PUT / PATCH | `/api/airport-service/airports/{id}/` | retrieve / update an airport |
| POST | `/api/airport-service/airports/{id}/upload-image/` | upload an airport image, admin only |
| GET / POST | `/api/airport-service/routes/` | list / create routes |
| GET / PUT / PATCH | `/api/airport-service/routes/{id}/` | nested source and destination |
| GET / POST | `/api/airport-service/crew/` | list / create crew members |
| GET / PUT / PATCH | `/api/airport-service/crew/{id}/` | returns `full_name` |
| GET / POST | `/api/airport-service/airplane-types/` | list / create airplane types |
| GET / PUT / PATCH | `/api/airport-service/airplane-types/{id}/` | |
| GET / POST | `/api/airport-service/airplanes/` | list / create airplanes |
| GET / PUT / PATCH | `/api/airport-service/airplanes/{id}/` | nested airplane type |
| POST | `/api/airport-service/airplanes/{id}/upload-image/` | upload an airplane image, admin only |
| GET / POST | `/api/airport-service/flights/` | list / create flights, with `tickets_available` |
| GET / PUT / PATCH | `/api/airport-service/flights/{id}/` | full nested card |
| GET / POST | `/api/airport-service/orders/` | only the current user's orders |
| GET / PUT / PATCH | `/api/airport-service/orders/{id}/` | |
| GET / POST | `/api/airport-service/tickets/` | list / create tickets |
| GET / PUT / PATCH | `/api/airport-service/tickets/{id}/` | nested flight and order |

### Users and authentication

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/user/register/` | create an account, no token required |
| POST | `/api/user/token/` | obtain access and refresh tokens |
| POST | `/api/user/token/refresh/` | refresh an access token |
| POST | `/api/user/token/verify/` | verify a token |
| GET / PUT / PATCH | `/api/user/me/` | read or update own profile |

### Documentation

| Endpoint | Description |
|---|---|
| `/api/schema/` | raw OpenAPI 3 schema |
| `/api/doc/swagger/` | Swagger UI |
| `/api/doc/redoc/` | ReDoc |
| `/admin/` | Django admin |

---

## Filtering

Every list endpoint accepts query parameters. They can be combined freely.

**Airports**

```
?city=kyiv            closest big city, case-insensitive substring
?name=boryspil        airport name, case-insensitive substring
```

**Routes**

```
?source=3,5           departure airport ids
?destination=8        arrival airport ids
?from_city=kyiv       departure city
?to_city=frankfurt    arrival city
?min_distance=1000    distance in km, inclusive
?max_distance=3000    distance in km, inclusive
```

**Crew**

```
?name=kov             matches first name OR last name
```

**Airplane types**

```
?name=wide            type name substring
```

**Airplanes**

```
?name=boeing          airplane name substring
?airplane_type=1,2    airplane type ids
?min_seats=200        rows * seats_in_row, calculated in SQL
?max_seats=400
```

**Flights**

```
?routes=2,5                   route ids
?airplane_type=2              airplane type ids
?crew=5,18                    crew member ids
?date=2026-11-12              exact departure date
?date_from=2026-11-10         departure on or after
?date_to=2026-11-15           departure on or before
?from_city=kyiv               departure city
?to_city=seoul                arrival city
?available=true               only flights with free seats
```

**Orders**

```
?date_from=2026-11-01         created on or after
?date_to=2026-11-30           created on or before
```

**Tickets**

```
?flight=14,23                 flight ids
?order=3                      order ids
```

Example of a combined query:

```
GET /api/airport-service/flights/?from_city=kyiv&date_from=2026-11-10&available=true
```

---

## Authentication and permissions

Authentication uses JWT. The access token lives 10 minutes, the refresh token
3 days.

1. Register or use an existing account.
2. `POST /api/user/token/` with `email` and `password`.
3. Send the access token in every request:

```
Authorization: Bearer <access_token>
```

Access rules are enforced by a custom permission class,
`IsAdminAllOrIsAuthenticatedReadOnly`:

| Role | Read | Write |
|---|---|---|
| Anonymous | no | no |
| Authenticated user | yes | no |
| Staff / superuser | yes | yes |

Orders and tickets are an exception: both viewsets override the permission
class with `IsAuthenticated`, because a passenger has to be able to buy a
ticket. On the data level `OrderViewSet.get_queryset()` returns only the orders
of the current user, and `perform_create()` attaches the order to the token
owner, so a client cannot create an order on behalf of someone else.

Rate limits: 100 requests per day for anonymous clients, 1000 for
authenticated ones. Pagination is `LimitOffsetPagination` with a default limit
of 5; pass `?limit=` and `?offset=` to change it.

---

## Design decisions

This section documents the non-obvious choices made while building the project.

**Separate serializers per action.** Each resource has up to three
serializers: a write serializer, a lightweight list serializer and a detailed
retrieve serializer with nested objects. A list of flights returns related
objects as ids; the detail view expands the route with both airports, the
airplane with its type and the full crew. This keeps list payloads small
without losing detail where it matters.

**Query optimization against N+1.** `get_queryset()` applies
`select_related()` for foreign keys and `prefetch_related()` for many-to-many
relations, and only for the actions that actually need them. Before the
optimization the flight list issued 171 queries; afterwards it issues a
constant number regardless of how many flights are in the database.

**Related querysets for browsable API forms.** `PrimaryKeyRelatedField` in
`FlightSerializer` and `TicketSerializer` receives a queryset that already has
`select_related()`. Without it, rendering the HTML form in the browsable API
calls `__str__()` on every option, and each call hits the database for the
related route, airports and airplane.

**`tickets_available` computed in SQL.** The number of free seats is annotated
with `F("airplane__rows") * F("airplane__seats_in_row") - Count("tickets",
distinct=True)`. Nothing is counted in Python. `distinct=True` is essential:
filtering by crew joins a many-to-many table and would otherwise multiply the
ticket count.

**`seats` filters are annotated too.** `Airplane.seats` is a Python property
with no column behind it, so `?min_seats=` builds an annotation with `F()`
instead of filtering a non-existent field.

**Unique seats per flight.** `Ticket` has a `UniqueConstraint` on
`(flight, row, seat)` rather than a `unique=True` on `seat`. A seat number is
only meaningful within a single flight, so the database enforces exactly that.

**Seat validation in one place.** `Ticket.validate_seat()` is a static
method that checks the row and the seat against the capacity of the airplane.
The model calls it from `clean()` and runs `full_clean()` inside `save()`, so
invalid data cannot be written through the ORM; the serializer calls the same
method from `validate()`, so the API answers 400 with a field-level message
instead of 500. The unique constraint covers duplicates, this covers range.

**Image upload as a separate action.** Images are uploaded through
`POST .../{id}/upload-image/` with `MultiPartParser`, not through the regular
update endpoint. Mixing `multipart/form-data` with the nested JSON of the
detail serializer makes both harder to use, and a dedicated action keeps the
write serializer clean.

**Custom user model from the start.** `user.User` inherits `AbstractUser`,
drops `username` and uses `email` as `USERNAME_FIELD`, with a matching custom
manager. Swapping the user model after the first migration is painful, so it
was done before the initial `migrate`.

**Explicit ordering on every queryset.** Pagination over an unordered queryset
produces `UnorderedObjectListWarning` and can repeat or skip rows between
pages. Flights are ordered by `departure_time`, other resources by `id`.

**OS-independent upload paths.** `image_path()` returns a string with forward
slashes rather than a `pathlib.Path`. On Windows a `Path` would produce
backslashes, which break the URL when the same database is served from Linux.
File names combine a slug of the object name with a UUID, so uploads never
collide. `slugify(..., allow_unicode=True)` keeps Cyrillic names readable, and
falls back to the model name when the title contains no sluggable characters.

**Manual filters over django-filter.** Filtering is implemented in
`get_queryset()` with explicit ORM calls. It is more verbose than
`django-filter` but makes the generated SQL obvious, which was the point for a
learning project. Each filter is documented for the OpenAPI schema with
`@extend_schema_view`, since drf-spectacular cannot detect manual filters on
its own.

**Health check before migrations.** `depends_on` alone only controls start
order, not readiness. The database service declares a `pg_isready` health
check and the application waits for `condition: service_healthy`, otherwise
the first `migrate` fails with "connection refused".

**No `makemigrations` at container start.** Migrations are generated during
development and committed to the repository. Generating them at runtime would
produce a different migration set on every machine.

**Non-root container user.** The image creates `my_user` and switches to it,
so the application does not run as root inside the container.

---

## Environment variables

Create a `.env` file in the project root:

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

Two notes:

`POSTGRES_HOST` is `localhost` for a local run. Inside Docker Compose it is
overridden to `db` in `docker-compose.yaml`, so the same file works for both.

Avoid `$` in `SECRET_KEY`. Docker Compose interpolates variables inside `.env`
and would silently replace `$name` sequences with an empty string. Generate a
safe key with:

```
python -c "import secrets; print(secrets.token_urlsafe(50))"
```

---

## Getting started with Docker

Clone the repository:

```
git clone https://github.com/<your-account>/airport-service-api.git
```

Enter the project directory:

```
cd airport-service-api
```

Create the `.env` file described above:

```
copy .env.sample .env
```

Build the images and start the containers:

```
docker compose up --build
```

In a second terminal, create a superuser:

```
docker compose exec app python manage.py createsuperuser
```

The API is now available at `http://127.0.0.1:8000/`.

Stop everything:

```
docker compose down
```

---

## Getting started locally

Clone the repository:

```
git clone https://github.com/<your-account>/airport-service-api.git
```

Enter the project directory:

```
cd airport-service-api
```

Create a virtual environment:

```
python -m venv venv
```

Activate it on Windows:

```
venv\Scripts\activate
```

Activate it on macOS or Linux:

```
source venv/bin/activate
```

Install the dependencies:

```
pip install -r requirements.txt
```

Create the `.env` file described above, then apply the migrations:

```
python manage.py migrate
```

Create a superuser:

```
python manage.py createsuperuser
```

Start the development server:

```
python manage.py runserver
```

---

## Running tests

Run the whole suite:

```
python manage.py test
```

Run the tests of a single app:

```
python manage.py test airport
```

Run one module:

```
python manage.py test airport.tests.test_views
```

Inside Docker:

```
docker compose exec app python manage.py test
```

The suite covers only project-specific logic: computed properties, the upload
path builder, seat validation and the unique seat constraint, serializer
switching per action, every filter, the `tickets_available` annotation, the
permission matrix, the custom user manager and the JWT flow.

Check code style:

```
flake8
```

Format the code:

```
black .
```

---

## API documentation

Interactive documentation is generated from the code by drf-spectacular, with
summaries, descriptions and every filter parameter documented.

Swagger UI:

```
http://127.0.0.1:8000/api/doc/swagger/
```

ReDoc:

```
http://127.0.0.1:8000/api/doc/redoc/
```

Raw OpenAPI schema:

```
http://127.0.0.1:8000/api/schema/
```
