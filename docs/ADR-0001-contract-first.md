# ADR-0001: Contract-first development

Status: Accepted for MVP

- Source: `contracts/main.tsp` under lead ownership.
- Generated: OpenAPI YAML, then client-side TypeScript declarations.
- Backend endpoint implementation must conform to OpenAPI; generated definitions are not editable source.
- Breaking changes require PRD/contract update before the frontend and backend accept them.
- Why: lets independent agents work without inventing incompatible data models.
