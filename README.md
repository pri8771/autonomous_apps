# Autonomous Apps

A private multi-agent app factory for planning, building, reviewing, testing, and delivering iOS and web applications with cloud and local LLMs.

## North-star outcome

Given a well-specified feature, the factory should produce a reviewed, tested pull request through asynchronous parallel work by multiple agents.

## Initial golden path

1. Create a project and connect a repository.
2. Enter a feature specification.
3. Generate and approve a dependency-aware task graph.
4. Run coding agents in isolated Git worktrees.
5. Fan completed work out to independent reviewers and tests.
6. Repair failures automatically within bounded limits.
7. Record discoveries as formal change requests.
8. Integrate approved branches and open a final pull request.
9. Record planning omissions, estimate errors, and rework for future learning.

## Planned monorepo

```text
apps/
  dashboard/
  api/
  worker/
  cli/
packages/
  project-graph/
  scheduler/
  agent-runtime/
  model-gateway/
  git-runtime/
  workflow-engine/
  evidence-engine/
  policy-engine/
  shared-types/
docs/
planning/
roles/
prompts/
templates/
workflows/
```

## Current status

Bootstrap and architecture definition. No production code has been selected or implemented yet.
