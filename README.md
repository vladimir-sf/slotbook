# SlotBook — Spec-Driven Multi-Agent Starter

An educational, **unimplemented** Calendly-style appointment booking app. This repository contains the
contract, architecture decisions, and **running frontend/backend foundations**, not a completed booking product.
The objective is to have 3 implementation agents build the features *after* you review the spec.

## Stack
- React + TypeScript + Vite
- FastAPI + PostgreSQL + SQLAlchemy + Alembic (ORM/migrations are implementation tasks)
- TypeSpec → OpenAPI → TypeScript types
- Docker Compose; pytest, Playwright; GitHub Actions (tests/CI are implementation tasks)
- GitHub Spec Kit with Codex CLI

## 1. Initialize and inspect

Prerequisites: Git, Docker Desktop (running), Python >=3.11, Node >=20, uv, Codex CLI.

If you unpacked this starter directly, run inside its directory:

```sh
git init
git add . && git commit -m 'Initial contract-first starter'
uv tool install specify-cli
specify init --here --force --integration codex
# Carefully review the diff before committing Spec Kit's generated files.
git add . && git commit -m 'Initialize GitHub Spec Kit for Codex'
```

`specify init --here --force` acknowledges the existing non-empty directory. It may modify
README/instructions; review the diff rather than assuming a non-destructive merge.

## 2. Start the foundation

```sh
cp .env.example .env
# Dev-only secrets; never commit .env
# Docker Desktop must be running.
docker compose up --build
```

- Frontend: http://localhost:5173
- API health: http://localhost:8000/health
- API docs: http://localhost:8000/docs
- PostgreSQL runs inside Docker only (no host port by default).

This merely starts the scaffold: real booking endpoints, database models and admin pages are intentionally not implemented.

## 3. Generate the contract

```sh
cd contracts
npm install
npm run build
cd ..
# Generated: contracts/tsp-output/@typespec/openapi3/openapi.yaml
cd frontend
npm install
npm run generate:api
cd ..
```

The generated `frontend/src/api/schema.d.ts` provides types, not an HTTP client.
The frontend agent must implement an actual client. Change `contracts/main.tsp`, not the generated artifacts.

## 4. Run the spec workflow BEFORE the agents code

Launch `codex` in the project root. Codex's Spec Kit commands use a `$` prefix:

```text
$speckit-constitution Define quality, privacy, test, architectural, and contract ownership principles from AGENTS.md.
$speckit-specify Implement the SlotBook MVP described in docs/PRD.md. Focus on observable behavior, especially competing bookings and timezone behavior.
$speckit-clarify Identify underspecified booking/authentication/timezone cases. Propose safe defaults, and pause at decision points.
$speckit-plan Use docs/ARCHITECTURE.md, contracts/main.tsp, FastAPI, React/TS, PostgreSQL, and Docker Compose.
$speckit-tasks Decompose by agent-owned areas and explicit integration milestones.
$speckit-analyze Check the PRD, plan, TypeSpec and tasks for consistency.
```

Review and freeze the approved contract before implementation. The Spec Kit artifacts may need to be
updated to match the provided hand-authored documents. `$speckit-implement` is **not**
part of this initial review phase; distribute accepted tasks first.

## 5. Launch specialized agents

Read `docs/AGENT_TASKS.md` and `docs/AGENT_PROMPTS.md`. Start one Codex session per agent;
use separate Git worktrees so the sessions cannot unknowingly edit the same checkout:

```sh
git worktree add ../slotbook-frontend -b feat/frontend
git worktree add ../slotbook-backend  -b feat/backend
git worktree add ../slotbook-quality  -b feat/quality
```

Launch `codex` independently in each worktree. **Each branch starts from the approved, committed contract.**
Agents commit their own edits; the human/lead reviews and merges branches to the integration branch.
The worktrees do not automatically share uncommitted edits or commits.

## 6. Basic checks

```sh
python -m compileall backend/app
# After installing Python requirements:
# cd backend && pytest -q
# After npm install in contracts:
# cd contracts && npm run build
# After npm install in frontend:
# cd frontend && npm run build
```

Quality agent implements tests and CI. `scripts/verify.sh` runs the available local checks after dependencies are installed.

## Safety notes

- `.env.example` credentials are *development-only*. Supply secrets and TLS for any deployment.
- Admin authentication, booking conflicts and time zones are **blocking acceptance criteria**.
- Never let agents deploy, push to protected branches, or modify production secrets without approval.
- Check the actual OpenAPI diff for breaking changes before merging.
