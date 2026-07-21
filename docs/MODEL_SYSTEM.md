---
id: DOC-MODEL-SYSTEM
canonicalFor: model-and-cli-runtime
status: active
owners: [engineering, product]
readWhen:
  - adding a model provider
  - changing local-only behavior
  - configuring model installation or routing
related:
  - docs/ARCHITECTURE.md
  - docs/SECURITY.md
  - docs/CONCURRENCY_MODEL.md
  - docs/TEST_PLAN.md
supersedes: []
---

# Model and Agent Runtime System

## Purpose

Define how Autonomous Apps discovers, configures, invokes, evaluates, and schedules cloud models, local models, and CLI coding agents.

## Current summary

All model and CLI execution is routed through controlled adapters. Users select exact models or policies per role and workflow step. Local-only mode is enforced by code. Model output is untrusted until validated.

## Runtime categories

- Cloud model provider.
- OpenAI-compatible endpoint.
- Local model runtime such as Ollama.
- CLI coding agent.
- Deterministic command worker for builds, tests, Git, browsers, or Xcode.

## Model descriptor

Each model record includes internal ID, provider/runtime, model name, local/cloud classification, capabilities, context/output limits, effort controls, cost metadata, installed/running state, host, measured performance, reliability history, source/license metadata, and allowed data classifications. Published claims and measured behavior remain distinct.

## Model policy

A role or task may specify exact model, providers, local-only/cloud-only, preferred/fallback sequence, capabilities, minimum context, effort, output limits, cost, timeout, retry, and diversity for review. Fallback may not weaken privacy or exact-model constraints.

## Routing modes

- **Exact:** use one model or fail.
- **Role default:** use the role’s versioned policy.
- **Policy-based:** choose an allowed capable model.
- **Evaluated:** later choose from historical accepted outcomes, with an explanation.

## Local-only enforcement

When active:

- Cloud model adapters and cloud embeddings are unavailable.
- Prompts and attachments cannot reach external model endpoints.
- CLI environments are sanitized so provider variables do not silently redirect to cloud inference.
- Prompt/source telemetry is disabled.
- Violations produce policy-denied and audit events.

Git, package registries, model downloads, and other network integrations have separate policies.

## Initial Ollama integration

V1 supports runtime health, installed model listing, model pull with progress, cancellation, removal with confirmation, streaming generation, OpenAI-compatible access where appropriate, benchmark runs, and recovery. The app does not assume every model supports tools, long context, vision, or coding.

## Runtime installation

V1 manages models through an installed runtime or guided installation. Managed runtime downloading and updating are deferred until signed-source, checksum, rollback, ownership, and distribution concerns are reviewed.

## Model discovery and installation

Users can browse curated definitions, enter exact model names, add custom endpoints, inspect source/license, see size/resource guidance, confirm downloads, watch progress, health-check, benchmark, and assign models. The app never downloads or removes a model without explicit action.

## Benchmarking

Measure time to first token, tokens per second, reliable context, structured-output validity, tool validity, coding acceptance, review quality, memory, and failure rate. Results bind to model, runtime, host, quantization, context, and benchmark-suite version.

## Model evaluation

Track first-pass acceptance, repair loops, invalid output, tool errors, review escapes, cost per accepted task, latency, and human intervention by task type. The system does not silently train or fine-tune on user source code.

## CLI adapter contract

An adapter declares executable discovery, version, non-interactive and PTY behavior, prompt delivery, working directory, environment, model selection, output parsing, cancellation, exit interpretation, change detection, resume support, and supported platforms.

Each run receives a unique worktree, process, scoped environment, output limit, timeout, resource record, and cancellation state. CLI sessions never share an interactive terminal.

## Agent output contract

May include summary, plan, findings, questions, decisions requested, files changed, commands/tests run, checks not run, risks, proposed change request, and completion recommendation. Schema validation precedes workflow transitions.

## Independent reviewers

Consequential work uses a different run and role and, when useful, a different model family or provider. Diversity reduces correlated failure but never replaces deterministic checks.

## Context assembly

Retrieve only task-relevant rules, project context, feature contract, task, decisions, interfaces, source/tests, failures, tools, and policy. Store provenance and a context-manifest hash. Exclude unrelated content and raw secrets.

## Prompt and transcript retention

Store template/version, context manifest, and transcripts according to project policy. Redact secrets. Transcripts are not canonical decisions unless converted into a decision or change record.

## Provider failure handling

Classify authentication, rate limit, quota, timeout, network, outage, invalid response, tool mismatch, refusal, content limit, and cancellation. Retries require idempotence and budget.

## Cost and budgets

Record model usage and cost where available, local runtime duration/resource use, CLI runtime, repair cost, and cost per accepted task. Budgets may apply per run, task, workflow, day, project, provider, or parent subtree.

## Security rules

No raw secrets in prompts; no model approves its own elevated permission; destructive or externally visible actions require policy; model commands are untrusted; downloads require consent; non-loopback custom endpoints require TLS unless explicitly approved for development.
