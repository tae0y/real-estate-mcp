---
name: api-architect
description: "API architect for designing and generating external service integration code. Use when building REST API clients, service integrations, or applying resilience patterns (circuit breaker, bulkhead, throttling, backoff). Generates fully implemented code across service/manager/resilience layers."
---

# API Architect

Design and generate fully implemented API client code in a 3-layer architecture.

## Workflow

Collect the following before generating code. Once all mandatory items are confirmed, generate immediately.

### Mandatory
- **Language** (e.g. Python, Java, TypeScript)
- **API endpoint URL**
- **REST methods** (at least one: GET, GET all, POST, PUT, DELETE)

### Optional
- DTOs for request/response — if omitted, generate mock DTOs based on API name
- API name
- Resilience: circuit breaker, bulkhead, throttling, backoff
- Test cases

## 3-Layer Design

| Layer | Responsibility |
|-------|---------------|
| **Service** | Basic HTTP requests and responses |
| **Manager** | Abstraction over Service for ease of configuration and testing |
| **Resilience** | Applies requested resilience patterns, calls Manager |

## Code Generation Rules

- Fully implement all layers — no stubs, comments in lieu of code, or templates
- Use the most popular resilience framework for the requested language
- Generate mock DTOs from the API name if not provided
- Never say "implement other methods similarly" — write all methods in full
