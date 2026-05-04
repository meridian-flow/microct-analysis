"""Interactive review workflow helpers using jupyter-workbench."""

from __future__ import annotations

from dataclasses import dataclass
from textwrap import dedent


@dataclass(frozen=True)
class ReviewSetup:
    """Configuration for an interactive review session."""

    scan_path: str
    session_id: str
    root_dir: str = ".jupyter-workbench"


@dataclass(frozen=True)
class ReviewState:
    """Current state of a review session."""

    session_id: str
    stage: str
    event_cursor: int = 0
    screenshot_count: int = 0


def _scene_code(
    session_name: str,
    output_dir: str,
    *,
    scan_path: str | None = None,
    component_indices: list[int] | None = None,
    scan_fingerprint: str | None = None,
) -> str:
    return dedent(
        f"""
        # Kernel exec code: this runs inside the jupyter-workbench kernel via
        # `jupyter-workbench exec`, not in microct-analysis library code.
        from pathlib import Path
        import json
        import nibabel as nib
        import numpy as np
        import pyvista as pv
        from skimage import measure
        from jupyter_workbench.adapters.visualization.event_log import DurableEventLog
        from jupyter_workbench.adapters.visualization.pyvista_trame import PyVistaTrameHelper

        scan_path = Path({scan_path!r})
        output_dir = Path({output_dir!r})
        requested_component_indices = {component_indices!r}
        requested_scan_fingerprint = {scan_fingerprint!r}
        if not output_dir.exists():
            raise FileNotFoundError(f"Pipeline output directory not found: {{output_dir}}")

        labels_path = output_dir / 'labels.nii.gz'
        if not labels_path.exists():
            labels_path = output_dir / 'segmentation' / 'labels.nii.gz'
        assignments_path = output_dir / 'structure_assignments.json'
        if not assignments_path.exists():
            assignments_path = output_dir / 'segmentation' / 'structure_assignments.json'
        if not labels_path.exists():
            raise FileNotFoundError(f"Segmentation labels not found: {{labels_path}}")

        labels = np.asarray(nib.load(str(labels_path)).get_fdata(), dtype=np.uint16)
        payload = json.loads(assignments_path.read_text()) if assignments_path.exists() else {{}}
        assignments = payload.get('assignments', payload)
        scan_fingerprint = requested_scan_fingerprint or str(scan_path)
        # legacy contract: scan_fingerprint = component_summary.get('scan_fingerprint_id', str(scan_path))
        requested = set(requested_component_indices) if requested_component_indices is not None else None
        if requested_component_indices is not None:
            wanted = set(requested_component_indices)

        def _mesh_for_label(label_id):
            mask = (labels == int(label_id)).astype(np.uint8)
            if int(mask.sum()) == 0:
                return None
            try:
                verts, faces, _, _ = measure.marching_cubes(mask, level=0.5, step_size=2)
            except (ValueError, RuntimeError) as exc:
                print({{'warning': 'label mesh unavailable', 'label_id': int(label_id), 'reason': str(exc)}})
                return None
            face_block = np.hstack([np.full((faces.shape[0], 1), 3, dtype=faces.dtype), faces])
            return pv.PolyData(verts, face_block)

        plotter = pv.Plotter()
        mesh_count = 0
        for name, label_id in sorted(assignments.items()):
            if requested is not None and int(label_id) not in requested:
                continue
            mesh = _mesh_for_label(label_id)
            if mesh is None:
                continue
            plotter.add_mesh(mesh, name=f"{{name}}-{{label_id}}", pickable=True, label=str(name))
            mesh_count += 1
        plotter.add_axes()
        plotter.add_text('Pick structures to review assignments. Keys/camera/picks are logged.', name='picker-help', font_size=10)

        events = DurableEventLog('.jupyter-workbench', {session_name!r})
        viz = PyVistaTrameHelper('.jupyter-workbench')
        viz.register_pick_callback({session_name!r}, plotter, events)
        viz.register_key_callback({session_name!r}, plotter, events)
        viz.register_camera_callback({session_name!r}, plotter, events)
        plotter.show(jupyter_backend='trame')
        print({{'scene': {session_name!r}, 'meshes': mesh_count, 'labels': str(labels_path), 'assignments': sorted(assignments), 'scan_fingerprint': scan_fingerprint}})
        """
    ).strip()


def segmentation_setup_code(scan_path: str, output_dir: str = "microct-output") -> str:
    """Generate jupyter-workbench exec code for segmentation scene setup."""
    return _scene_code("seg-review", output_dir, scan_path=scan_path)


def landmark_picking_code(
    component_indices: list[int] | None = None,
    scan_fingerprint: str | None = None,
    output_dir: str = "microct-output",
) -> str:
    """Generate jupyter-workbench exec code for landmark picking scene setup."""
    return _scene_code(
        "landmark-picking",
        output_dir,
        component_indices=component_indices,
        scan_fingerprint=scan_fingerprint,
    )


def event_poll_code(session_id: str, cursor: int, timeout: float = 30.0) -> str:
    """Generate jupyter-workbench exec code to poll the durable event log."""
    return dedent(
        f"""
        # Kernel exec code: this runs inside the jupyter-workbench kernel via
        # `jupyter-workbench exec`, not in microct-analysis library code.
        from jupyter_workbench.adapters.visualization.event_log import DurableEventLog

        events = DurableEventLog('.jupyter-workbench', {session_id!r})
        new_events, cursor, timed_out = events.wait({cursor}, timeout={timeout!r})
        print({{'events': new_events, 'cursor': cursor, 'timed_out': timed_out}})
        """
    ).strip()


def screenshot_code(session_id: str, root_dir: str, filename: str) -> str:
    """Generate jupyter-workbench exec code to capture a screenshot."""
    return dedent(
        f"""
        # Kernel exec code: this runs inside the jupyter-workbench kernel via
        # `jupyter-workbench exec`, not in microct-analysis library code.
        from jupyter_workbench.adapters.visualization.screenshots import capture_screenshot

        shot = capture_screenshot({session_id!r}, {root_dir!r}, {filename!r}, plotter=plotter)
        print(shot)
        """
    ).strip()
