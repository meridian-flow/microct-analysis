---
name: landmark-picking
description: Guide interactive landmark and seed-component picking for micro-CT analysis notebooks.
---

# Landmark Picking

Use this skill when the user must assign femur, tibia, patella, or fibula seed components, correct an assignment, or confirm landmark candidates in a micro-CT notebook.

## Principles

- Use `mouse_ct.picker_domain` as the authority for palette order, stable IDs, state transitions, and validation.
- Use component IDs and landmark IDs in all notes; never rely only on “the red blob.”
- Explain every assignment or correction with the `PickerTransition.explanation` / `explanation_payload` returned by `handle_event()`.
- Keep the scene live in the existing `jupyter-workbench` kernel.

## Setup

1. Open or attach to a session:

```bash
jupyter-workbench open --session-id landmark-picking
```

2. Load component summaries and landmark candidates from `mouse_ct.artifacts`.
3. Build the scene:

```python
from mouse_ct.picker_domain import build_scene, initial_state
scene = build_scene(
    components=component_objects,
    initial=initial_assignments,
    anchor_indices=(anchor_femur_idx, anchor_tibia_idx),
    max_meshes=32,
    scan_fingerprint=scan_fingerprint,
)
picker_state = initial_state(scene, initial_assignments)
components_by_id = {p.component_id: p.component for p in scene.pickables}
```

4. Render all pickable components and, when useful, a translucent reference volume. Register pick, key, camera, and optional toggle callbacks with `DurableEventLog` and `PyVistaTrameHelper`.

## Interaction loop

1. Show the trame scene and ask the user to inspect it.
2. Poll events from the durable event log.
3. Convert event records into domain events:
   - Pick: `PickerEvent(type='pick', component_id=<stable id>)`
   - Palette switch: `PickerEvent(type='key', active_palette='femur'|'tibia'|'patella'|'fibula'|'unassigned')`
   - Reference volume: `PickerEvent(type='toggle', reference_volume=True|False)`
4. Apply the transition:

```python
from mouse_ct.picker_domain import PickerEvent, handle_event
transition = handle_event(picker_state, event, components_by_id=components_by_id)
picker_state = transition.state
print(transition.explanation)
```

5. Update actor color when `transition.color_component_id` and `transition.color` are present.
6. Explain the decision in plain language before asking for the next pick.
7. Capture screenshots after anchor assignments, after user corrections, and before final confirmation.

## Palette and confirmation

Keyboard shortcuts follow `picker_domain.PALETTE_ORDER`: `1` femur, `2` tibia, `3` patella, `4` fibula, `5` unassigned. Use `unassigned` to clear an accidental pick.

Validate before saving:

```python
transition = handle_event(
    picker_state,
    PickerEvent(type='confirm_assignments'),
    components_by_id=components_by_id,
)
print(transition.explanation)
```

If `transition.confirmed_assignments` is absent, report the missing required bones and keep the scene open. If present, write landmark candidates and screenshot references to durable artifacts.
