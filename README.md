# SlotBook

Appointment scheduling for independent hosts.

SlotBook is a Calendly-like application designed to help a single host offer appointment types,
share available times and manage bookings. Guests can choose a time without creating an account,
while the host manages their schedule through an administrator interface.

**Status: in development.** This repository currently contains frontend and backend scaffolding,
a PostgreSQL development environment and the API contract. The booking and administrator
journeys described below are planned features.

## Planned features

- **Appointment catalog** — browse appointment types with descriptions and durations.
- **Simple booking** — choose an available date and time, enter contact details and receive
  an on-screen confirmation.
- **Schedule management** — configure weekly working hours and block dates for each activity.
- **Booking administration** — sign in to review and cancel appointments.
- **Timezone-aware availability** — display times in the visitor's timezone and handle daylight
  saving transitions.
- **Conflict protection** — prevent overlapping confirmed bookings, including concurrent requests.
- **Responsive interface** — use the booking and administration flows on desktop and mobile.

The initial scope focuses on scheduling for one host. Payments, calendar synchronization and
external integrations are outside the initial release.

## Technology stack

| Area | Technologies |
| --- | --- |
| Frontend | React 19, TypeScript, Vite 7, Node.js 22 |
| Backend | Python 3.12, FastAPI |
| Data access and migrations | SQLAlchemy 2, Alembic |
| Database | PostgreSQL 16 |
| API definitions | TypeSpec → OpenAPI → generated TypeScript definitions |
| Testing | pytest, HTTPX; planned Playwright end-to-end coverage |
| Infrastructure | Docker Compose; planned GitHub Actions CI |

The API contract provides a shared definition for frontend and backend development. OpenAPI
and TypeScript declarations are generated from [TypeSpec](contracts/main.tsp).

## Local development preview

Install Docker with Compose v2 and start the Docker engine. From the repository root:

```sh
cp .env.example .env
# Configure local development values in .env.
docker compose up --build
```

Keep `.env` out of version control. The supplied configuration is for local development.

- [Frontend preview](http://localhost:5173)
- [API health check](http://localhost:8000/health)
- [Development API documentation](http://localhost:8000/docs)

The preview currently shows the frontend scaffold and API health endpoint. Booking, login and
schedule management are not available yet. PostgreSQL runs on the internal Compose network.

## Learn more

- [Product scope](docs/PRD.md)
- [Application architecture](docs/ARCHITECTURE.md)
- [API definition](contracts/main.tsp)
- [Generated OpenAPI](contracts/tsp-output/@typespec/openapi3/openapi.yaml)
