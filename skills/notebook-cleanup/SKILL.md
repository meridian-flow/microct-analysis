---
name: notebook-cleanup
description: Clean and compact micro-CT analysis notebooks while preserving lineage and review artifacts.
---

# Notebook Cleanup

Use this skill for cheap post-review cleanup. It does not require an active visualization. Work from durable `jupyter-workbench` lineage, snapshots, screenshots, event logs, and micro-CT artifacts.

## Handoff contract

The expensive analysis agent owns live review and visualization. Before handoff it should preserve accepted parameters, screenshots, event evidence, artifact manifests, and final explanations in the notebook or durable outputs. It may close the browser/trame session and live runtime resources.

The cleanup agent only needs:

- the session id,
- the `.jupyter-workbench/` durable root,
- the `jupyter-workbench` CLI.

Do not require PyVista, trame, a browser, or an active visualization kernel for cleanup. If visualization is degraded or closed, use `snapshot`, lineage, screenshots, and saved artifacts to understand what was done.

## Goals

- Remove dead-end exploration cells and noisy repeated execution.
- Preserve decisions, explanations, accepted parameters, screenshot references, and artifact paths.
- Keep enough lineage that another agent can understand why thresholds, landmarks, and ROI parameters changed.

## Workflow

1. Inspect lineage and snapshot:

```bash
jupyter-workbench lineage <session-id>
jupyter-workbench snapshot --session-id <session-id>
```

2. Read active notebook path, revisions, derived/compacted notebook history, visualization status, recent events, screenshot paths, active scene summary, and artifact references. Do not require the trame browser scene to be live.

3. Identify cells to keep:
   - final pipeline setup and accepted parameters,
   - artifact loads/writes from `microct_analysis.artifacts` or project artifact helpers,
   - `PickerTransition` / explanation payload outputs,
   - screenshot capture cells and paths,
   - final measurement report cells,
   - user correction notes and accepted rationale.

4. Identify dead ends:
   - cells explicitly marked abandoned/dead-end,
   - failed experiments superseded by a later accepted run,
   - duplicate display cells with no unique screenshot, event, or decision,
   - temporary debugging prints that do not explain the final result.

5. Use deterministic helpers when available:

```python
from microct_analysis.notebook_tasks.cleanup import identify_dead_ends, identify_review_cells
```

6. Derive a safe cleanup notebook before manual edits or additional cleanup notes:

```bash
jupyter-workbench derive <session-id>
```

`derive` writes a new derived notebook and leaves the source notebook unchanged.

7. Compact automatic dead ends:

```bash
jupyter-workbench compact <session-id>
```

Automatic compaction removes failed code cells that have later successful code cells. For reviewed cell indexes, remove exact cells instead:

```bash
jupyter-workbench compact <session-id> -c 3 -c 5 -c 7
```

8. Verify that the clean notebook still references durable artifacts: manifest, component summary, segmentation summary, landmark candidates, ROI/measurement outputs, screenshots, event summaries, and accepted explanations.

```bash
jupyter-workbench lineage <session-id>
jupyter-workbench snapshot --session-id <session-id>
```

Confirm the source notebook remains on disk and lineage records the derived/compacted relationship.

## Never remove

- Screenshot artifact references used in review documentation.
- Cells containing accepted threshold, component assignment, landmark decision, or measurement explanation payloads.
- The final artifact manifest load/write cell.
- User-visible decision summaries, even if the code that produced them was later compacted.

## Explain-then-apply

- Before removing cells, explain what each cell was for and why it can be removed without losing the accepted analysis story.
- Preserve markdown/display cells that document correction explanations, translated user feedback, `correction_explanations`, screenshots, and review decisions.
- If a cell contains an explanation but obsolete code, preserve or copy the explanation into the cleanup plan before removing the code cell.
- When user feedback is non-technical, keep the translated domain operation and plain-language rationale together so later readers understand the decision without replaying the live scene.
