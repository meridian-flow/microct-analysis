---
name: roi-measurement
description: Support region-of-interest measurement workflows for preclinical micro-CT analysis.
---

# ROI Measurement

Use this skill after segmentation and landmark/seed picking have produced stable components or landmark candidates. The goal is to define an ROI, let the user inspect or adjust it, run measurement, and preserve provenance.

## Workflow

1. Attach to the existing review session or open one:

```bash
jupyter-workbench open --session-id roi-measurement
```

2. Load segmentation results, confirmed assignments, and landmark candidates from `mouse_ct.artifacts`. Use stable component/landmark IDs in the ROI name and notes.

3. Define the ROI from landmark positions and segmented masks. Make box dimensions explicit: origin, axes, extents, voxel spacing, and whether the ROI was squared or expanded to a standard margin.

4. Render the 3D scene with:
   - segmented bone/component actors,
   - a translucent ROI box or clipped volume,
   - landmark glyphs and labels,
   - optional mask overlay for threshold inspection.

5. Register slider callbacks for tunable parameters such as threshold, ROI margin, smoothing, or minimum component size with kernel exec code only; library workflows should call `jupyter-workbench exec` rather than importing adapters:

```python
# Kernel exec code run via `jupyter-workbench exec`, not a microct-analysis library import.
from jupyter_workbench.adapters.visualization.event_log import DurableEventLog
from jupyter_workbench.adapters.visualization.pyvista_trame import PyVistaTrameHelper

events = DurableEventLog('.jupyter-workbench', 'roi-measurement')
viz = PyVistaTrameHelper('.jupyter-workbench')
viz.register_slider_callback('roi-measurement', plotter, events, (0.0, 10.0), 'roi-margin-mm')
viz.register_slider_callback('roi-measurement', plotter, events, (0.0, 5000.0), 'mask-threshold')
viz.register_camera_callback('roi-measurement', plotter, events)
```

6. Poll the event log with a cursor. For slider events, explain the proposed parameter change before rerunning measurement. Example: “Increasing ROI margin includes more proximal cortex but may add adjacent soft tissue.”

7. Run the measurement pipeline stage only after the user accepts the ROI/parameter state. Record inputs: segmentation artifact paths, landmark IDs, ROI geometry, thresholds, and slider values.

8. Report measurements as structured results: value, unit, ROI ID, source component/landmark IDs, parameter set, and artifact paths. If the domain package provides an explanation payload, include its summary and next steps; otherwise write a concise plain-language rationale.

9. Capture screenshots of the final ROI overlay and any user-requested alternate parameter states.

## Corrections

When the user says the ROI is off, do not immediately rerun the full workflow. First identify whether the error is landmark placement, segmentation threshold, ROI geometry, or measurement configuration. Fix the earliest incorrect source, regenerate downstream artifacts, and explain the dependency chain.

## Explain-then-apply

- Before changing ROI margin, threshold, smoothing, clipping, or measurement parameters, explain what physical region will grow/shrink or which voxels will be included/excluded.
- Report measurements in plain language alongside technical values: value, unit, ROI ID, source components/landmarks, and what the value means physically.
- When a user questions a measurement, translate the concern into the earliest likely source operation: landmark correction, segmentation threshold, ROI geometry, or measurement configuration. Do not require the user to name that parameter.
- Use `microct_analysis.workflows.explain.explain_correction()` / `correction_code()` for accepted corrections so the notebook records what changed and why before rerunning measurement.
- After rerun, explain the dependency chain: which upstream artifact changed and which measurement result changed because of it.
