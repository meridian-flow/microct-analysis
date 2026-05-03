---
name: mct-visual-review
description: Semi-HITL visual review mechanics and policy for microCT analysis stages.
---

# MCT Visual Review

Reusable semi-HITL visual review loop for micro-CT analysis specialists.

## Mechanics

- Capture screenshots at decision points using `jupyter-workbench exec` snippets.
- Use screenshot path format `<stage>/screenshot_<NNN>.png` with zero-padded counters.
- Poll durable event logs with a caller-owned cursor.
- Translate generic workbench events into concrete domain operations before acting.
- Refresh only affected actors after parameter changes; rebuild the full scene only when composition changes.
- Load stage-relevant reference images from the workflow file and compare against current screenshots.

## Policy

### Confidence assignment

- `high`: workflow checks and visual evidence agree → proceed silently.
- `medium`: usable output with caveats → proceed and flag.
- `low`: ambiguous or blocked interpretation → pause and ask the user.

Stage-specific acceptance checks from the workflow file participate in confidence decisions.

### Explain then apply

- Before any corrective mutation, explain expected physical and visual impact in plain language.
- Use `microct_analysis.workflows.explain.explain_correction()` and `correction_code()` to record explanation + applied change.
- After execution, summarize what changed and what the reviewer should now see.

### Feedback handling

- Translate non-technical feedback with:
  - `microct_analysis.workflows.feedback.translate_visual_feedback()`
  - `microct_analysis.workflows.feedback.translate_screenshot_feedback()`
- Do not require users to name technical parameters.

## Out of scope for this skill

This skill does **not** own:

- session choreography and spawn sequencing,
- anatomy knowledge,
- protocol constants,
- stage execution sequences.

Those belong to agent prompts and workflow files.
