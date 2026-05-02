---
name: segmentation-review
description: Review micro-CT segmentation artifacts and explain quality-control findings using jupyter-workbench and mouse-ct.
---

# Segmentation Review

Use this skill when a user needs to inspect a micro-CT segmentation result, adjust segmentation parameters, or explain why a component/mask looks right or wrong. Use the `pyvista-interactive` skill for the generic jupyter-workbench + PyVista mechanics; this skill adds the mouse-CT domain workflow.

## Ground rules

- Work in a durable `jupyter-workbench` session; do not launch a separate visualization runtime.
- Explain every threshold, component, mask, or parameter change in plain language before applying it.
- Track objects by stable `mouse_ct.picker_domain.component_id(...)`, not actor order or visual color alone.
- Prefer notebook-friendly artifacts from `mouse_ct.artifacts` before rerunning expensive segmentation.
- If the user says “that looks wrong,” stop, summarize the observed issue, propose one correction, then execute only after the user agrees.

## Workflow

1. Open a session:

```bash
jupyter-workbench open --session-id seg-review
```

2. Execute setup code that loads the DICOM/scan, runs or resumes the mouse-CT segmentation stage, and writes/loads artifact summaries. Keep `components`, `thresholds`, `scan_fingerprint`, `scene`, `components_by_id`, `events`, and `plotter` in kernel memory.

3. Build the review scene with `mouse_ct.picker_domain.build_scene(...)`. Render each retained component as a color-coded PyVista actor named with its stable component ID. Show rejected/prefiltered components separately or as translucent gray when the review question concerns pruning.

4. Register durable callbacks:

```python
from jupyter_workbench.adapters.visualization.event_log import DurableEventLog
from jupyter_workbench.adapters.visualization.pyvista_trame import PyVistaTrameHelper

events = DurableEventLog('.jupyter-workbench', 'seg-review')
viz = PyVistaTrameHelper('.jupyter-workbench')
viz.register_pick_callback('seg-review', plotter, events)
viz.register_key_callback('seg-review', plotter, events)
viz.register_camera_callback('seg-review', plotter, events)
plotter.show(jupyter_backend='trame')
```

5. Ask the user to inspect the browser URL from the `visualization_delta`. Do not replace visual review with text-only summaries when a live scene is available.

6. Poll events from a caller-owned cursor. Translate picks through `components_by_id` and artifact summaries: component ID, voxel count, centroid, bbox, edge faces, retained/prefiltered status, and any stage flags.

7. Explain observations using `mouse_ct.explanations`: threshold rationale for threshold changes, component reassignment rationale for picked components, and next-look guidance for QC flags.

8. Apply corrections by rerunning the smallest needed pipeline step with adjusted parameters. Rebuild the scene with the same stable IDs where possible, then explain what changed.

9. Capture screenshots at decision points:

```python
from jupyter_workbench.adapters.visualization.screenshots import capture_screenshot
shot = capture_screenshot('seg-review', '.jupyter-workbench', 'segmentation-review-1.png', plotter=plotter)
print(shot)
```

10. Repeat inspect → poll → explain → adjust → screenshot until the user approves, then close the session.

```bash
jupyter-workbench close --session-id seg-review
```

## Artifact inspection

Load durable summaries instead of guessing from visuals:

```python
from mouse_ct import artifacts
manifest = artifacts.load_manifest(output_dir)
components = artifacts.read_json_artifact(output_dir, 'artifacts/components.json')
segmentation = artifacts.read_json_artifact(output_dir, 'artifacts/segmentation.json')
stage = artifacts.load_stage_summary(output_dir, 'segmentation')
```

Use `stage['flags']`, retained/prefiltered counts, masks, labels, and QC image paths in explanations. If a requested helper is named `artifacts.stage_summary()` in older instructions, use the current public equivalent `artifacts.load_stage_summary(output_dir, stage)`.

## Explain-then-apply

- Before ANY threshold, component pruning, mask, or segmentation parameter change, explain in plain language what will change and why it addresses the observed visual issue.
- Use `microct_analysis.workflows.feedback.translate_visual_feedback()` for non-technical feedback such as “that looks wrong,” “too much noise,” “this area is missing,” or screenshot annotations. Translate the feedback into domain operations before naming parameters.
- Use `microct_analysis.workflows.explain.explain_correction()` / `correction_code()` when applying accepted corrections so the notebook records the explanation before the code runs.
- After the change, explain what actually happened: which artifact or component changed, what visual difference to expect, and whether the same stable component IDs were preserved.
- If translation is uncertain, investigate the current scene, component summary, QC flags, and screenshots first; propose one correction and wait for agreement before applying it.
