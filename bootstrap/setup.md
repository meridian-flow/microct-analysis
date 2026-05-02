# microct-analysis bootstrap

This package requires the local `jupyter-workbench` and `mouse-ct` packages. Visualization helpers also require the `pyvista` and `trame` stack provided through those dependencies.

Run these checks after creating or updating the environment:

```bash
uv run python -c "from jupyter_workbench import SessionService, ExecutionService, SnapshotService; print('workbench ok')"
uv run python -c "import mouse_ct; print('mouse-ct ok')"
uv run python -c "import pyvista, trame; print('viz ok')"
```

If any check fails, stop before running notebooks or skills. Install or link the missing package, then rerun all checks. Do not continue with partial bootstrap state because later notebook failures may look like analysis bugs instead of environment problems.


## Explain-then-apply protocol

Every domain correction requires a plain-language explanation before it runs. The explanation must say what will change, why the change addresses the review finding, and which artifact/component/parameter is affected. Use `microct_analysis.workflows.explain.correction_code()` to print and display the explanation before executing correction code, and keep the resulting record in the notebook.

Non-technical feedback is always translated before action. If the user says “that looks wrong,” points at “this area,” or supplies an annotated screenshot, use `microct_analysis.workflows.feedback.translate_visual_feedback()` or `translate_screenshot_feedback()` to convert the observation into inspectable domain operations. Do not require the user to name thresholds, masks, landmarks, or ROI parameters.

The notebook is the decision record. Preserve explanation cells, translated feedback, screenshots, stable component/landmark IDs, and accepted parameter notes so another agent can understand what changed without reopening the live scene.

## First-wedge workflow examples

Open a segmentation review session:

```bash
jupyter-workbench open --session-id seg-review
jupyter-workbench exec --session-id seg-review "$(uv run python - <<'PY'
from microct_analysis.workflows.review import segmentation_setup_code
print(segmentation_setup_code('/path/to/dicom-or-scan'))
PY
)"
```

Poll durable visualization events:

```bash
jupyter-workbench exec --session-id seg-review "$(uv run python - <<'PY'
from microct_analysis.workflows.review import event_poll_code
print(event_poll_code('seg-review', cursor=0, timeout=10.0))
PY
)"
```

Capture a review screenshot:

```bash
jupyter-workbench exec --session-id seg-review "$(uv run python - <<'PY'
from microct_analysis.workflows.review import screenshot_code
print(screenshot_code('seg-review', '.jupyter-workbench', 'segmentation-review-1.png'))
PY
)"
```

Create a landmark-picking scene from retained component indices:

```bash
jupyter-workbench open --session-id landmark-picking
jupyter-workbench exec --session-id landmark-picking "$(uv run python - <<'PY'
from microct_analysis.workflows.review import landmark_picking_code
print(landmark_picking_code([1, 2, 3, 4], 'scan-demo'))
PY
)"
```

For cleanup-only work, no live visualization is required:

```bash
jupyter-workbench lineage --session-id seg-review
jupyter-workbench snapshot --session-id seg-review
```

Then use `microct_analysis.notebook_tasks.cleanup` helpers to identify dead-end cells and cells that preserve review decisions.
