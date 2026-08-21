# Technical Plan: {{SPEC_NAME}}

> **Target Spec**: `.workflow/specs/active/{{SPEC_NAME}}/spec.md`  
> **Architecture Invariants**: `.workflow/memory/workflow_methodology.md` & `coding_preferences.md`

## 1. Technical Architecture & Topology
<!-- High-level module architecture, layer boundaries, and interaction flow. -->

## 2. Data Models, Schemas & State Contracts
<!-- Define exact types, models, database schemas, and validation rules. -->
```typescript
// Data models, types, and DTOs
```

## 3. Interfaces & Component Contracts
- `functionName(params: InputType): OutputType` — Detailed behavioral contract.

## 4. Dependencies & Library Selection
- **Ecosystem Libraries**: Conforming to project_context.md and repository rules.
- **External Services & Drivers**: Rationale for library choices without technical drift.

## 5. Security, Performance & Scalability
- **OWASP Compliance**: Input sanitization, authentication gates, secret protection.
- **Performance Invariants**: Latency budgets, database indexing, caching strategies.
