# App Factory Rules

## Planning

1. Every requirement maps to one or more tasks.
2. Every task has acceptance criteria, inputs, outputs, dependencies, expected scope, and required reviews.
3. Plans are dependency graphs, not flat backlogs.
4. Planning uses independent decomposition, adversarial review, synthesis, and compilation.
5. Plans are versioned; accepted changes never overwrite history.

## Execution

1. Every coding task runs in an isolated Git worktree and branch.
2. Agents never modify `main` directly.
3. Workers claim ready tasks independently; there are no global rounds.
4. A worker that finishes early immediately claims other compatible ready work.
5. Parallelism is constrained by dependencies, expected file scope, worker capacity, and work-in-progress limits.
6. Agents communicate asynchronously by default. Bounded deliberation is reserved for high-value uncertainty.

## Verification

1. Agent statements are not evidence.
2. Builds, tests, diffs, screenshots, logs, and independent reviews are evidence.
3. The author cannot be the only reviewer.
4. Reviews and tests fan out in parallel when possible.
5. Required evidence must pass before a task is accepted.
6. Repair attempts are bounded and preserve complete diagnostics.

## Changes

1. Newly discovered work becomes a formal change request.
2. Change requests classify the cause, impact, affected work, and proposed graph update.
3. Only affected work pauses; unrelated work continues.
4. Accepted changes update the graph atomically and create a new plan version.

## Learning

1. Every unplanned task, missed dependency, estimate error, and rework event is recorded.
2. Planning omissions are distinguished from true scope changes and implementation defects.
3. Repeated mistakes become explicit planning rules.
4. Lessons are scoped as project-local, template-level, or factory-wide.
