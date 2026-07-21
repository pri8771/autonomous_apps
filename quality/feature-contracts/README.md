# Feature Contracts

Each durable product feature has one versioned JSON contract. The contract owns user outcome, production data source, states, error behavior, duplicate protection, persistence, layout, accessibility, prohibited behavior, and acceptance tests.

FEAT-001 through FEAT-014 define V1. FEAT-015 through FEAT-018 are post-V1 and may not be pulled into V1 without an approved product change.

A contract may move from `planned` only after product, architecture, quality, and security review as applicable. Implementation must update the contract when behavior changes.
