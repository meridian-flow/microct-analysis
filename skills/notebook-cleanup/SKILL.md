---
name: notebook-cleanup
description: Clean and compact micro-CT analysis notebooks while preserving lineage and review artifacts.
---

# Notebook Cleanup

Use this skill for cheap post-review cleanup. It does not require an active visualization. Work from durable `jupyter-workbench` lineage, snapshots, screenshots, and mouse-CT artifacts.

## Goals

- Remove dead-end exploration cells and noisy repeated execution.
- Preserve decisions, explanations, accepted parameters, screenshot references, and artifact paths.
- Keep enough lineage that another agent can understand why thresholds, landmarks, and ROI parameters changed.

## Workflow

1. Inspect lineage and snapshot:

```bash
jupyter-workbench lineage --session-id <session-id>
jupyter-workbench snapshot --session-id <session-id>
```

2. Read visualization status, recent events, screenshot paths, active scene summary, and artifact references. Do not require the trame browser scene to be live.

3. Identify cells to keep:
   - final pipeline setup and accepted parameters,
   - artifact loads/writes from `mouse_ct.artifacts`,
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

6. When `jupyter-workbench derive` is implemented, create a clean derived notebook instead of mutating the source notebook in place. Until then, write a cleanup plan listing cells to keep/remove and reasons.

7. Verify that the clean notebook still references durable artifacts: manifest, component summary, segmentation summary, landmark candidates, ROI/measurement outputs, and screenshots.

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
