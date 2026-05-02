"""Interactive review workflow helpers using jupyter-workbench and mouse-ct."""

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


def segmentation_setup_code(scan_path: str, output_dir: str = "microct-output") -> str:
    """Generate jupyter-workbench exec code for segmentation scene setup."""
    return dedent(
        f"""
        # Kernel exec code: this runs inside the jupyter-workbench kernel via
        # `jupyter-workbench exec`, not in microct-analysis library code.
        # DurableEventLog is the shipped in-kernel implementation available there.
        from pathlib import Path
        import numpy as np
        import pyvista as pv
        from skimage import measure
        from jupyter_workbench.adapters.visualization.event_log import DurableEventLog
        from jupyter_workbench.adapters.visualization.pyvista_trame import PyVistaTrameHelper
        from mouse_ct import artifacts
        from mouse_ct.picker_domain import build_scene
        from mouse_ct.types import Component

        scan_path = Path({scan_path!r})
        output_dir = Path({output_dir!r})
        if not output_dir.exists():
            raise FileNotFoundError(f"Pipeline output directory not found: {{output_dir}}")

        manifest = artifacts.load_manifest(output_dir) if artifacts.manifest_path(output_dir).exists() else None
        component_summary = artifacts.read_json_artifact(output_dir, 'artifacts/components.json')
        segmentation = artifacts.read_json_artifact(output_dir, 'artifacts/segmentation.json')
        stage = artifacts.load_stage_summary(output_dir, 'segmentation')
        components_payload = component_summary.get('retained', [])
        scan_fingerprint = component_summary.get('scan_fingerprint_id', str(scan_path))

        def _component_from_payload(payload):
            return Component(
                index=int(payload['index']),
                voxel_count=int(payload['voxel_count']),
                centroid_zyx=tuple(float(v) for v in payload['centroid_zyx']),
                centroid_mm=tuple(float(v) for v in payload.get('centroid_mm', payload['centroid_zyx'])),
                bbox_zyx=tuple(tuple(int(v) for v in axis) for axis in payload['bbox_zyx']),
                edge_faces=tuple(payload.get('edge_faces', ())),
            )

        def _load_array(relative_path):
            path = output_dir / relative_path
            if not path.exists():
                return None
            if path.suffix == '.npy':
                return np.load(path)
            if path.suffix == '.npz':
                data = np.load(path)
                return data[data.files[0]]
            return None

        def _mesh_for_component(component, labels):
            if labels is None:
                return None
            mask = (labels == component.index).astype(np.uint8)
            if int(mask.sum()) == 0:
                return None
            try:
                verts, faces, _, _ = measure.marching_cubes(mask, level=0.5, step_size=2)
            except (ValueError, RuntimeError) as exc:
                print({{'warning': 'component mesh unavailable', 'component_index': component.index, 'reason': str(exc)}})
                return None
            face_block = np.hstack([np.full((faces.shape[0], 1), 3, dtype=faces.dtype), faces])
            return pv.PolyData(verts, face_block)

        def _centroid_marker(component):
            center = tuple(reversed(component.centroid_zyx))
            radius = max(1.0, float(component.voxel_count) ** (1 / 3) / 4)
            return pv.Sphere(radius=radius, center=center)

        component_objects = [_component_from_payload(c) for c in components_payload]
        scene = build_scene(
            components=component_objects,
            initial={{}},
            anchor_indices=(None, None),
            max_meshes=min(24, len(component_objects)),
            scan_fingerprint=scan_fingerprint,
        )
        components_by_id = {{p.component_id: p.component for p in scene.pickables}}

        labels = _load_array(segmentation.get('labels', '')) if segmentation.get('labels') else None
        if labels is None:
            print({{'warning': 'real label volume unavailable; using centroid markers as fallback'}})

        plotter = pv.Plotter()
        mesh_count = 0
        marker_count = 0
        for pickable in scene.pickables:
            mesh = _mesh_for_component(pickable.component, labels)
            if mesh is None:
                mesh = _centroid_marker(pickable.component)
                marker_count += 1
            else:
                mesh_count += 1
            plotter.add_mesh(mesh, color=pickable.initial_color, name=pickable.actor_name, pickable=True)
        plotter.add_axes()
        plotter.add_text(scene.help_text, name='picker-help', font_size=10)

        events = DurableEventLog('.jupyter-workbench', 'seg-review')
        viz = PyVistaTrameHelper('.jupyter-workbench')
        viz.register_pick_callback('seg-review', plotter, events)
        viz.register_key_callback('seg-review', plotter, events)
        viz.register_camera_callback('seg-review', plotter, events)
        plotter.show(jupyter_backend='trame')
        print({{'scene': 'segmentation-review', 'pickables': len(scene.pickables), 'meshes': mesh_count, 'centroid_markers': marker_count, 'manifest': manifest, 'stage': stage.get('status')}})
        """
    ).strip()


def landmark_picking_code(
    component_indices: list[int] | None = None,
    scan_fingerprint: str | None = None,
    output_dir: str = "microct-output",
) -> str:
    """Generate jupyter-workbench exec code for landmark picking scene setup."""
    return dedent(
        f"""
        # Kernel exec code: this runs inside the jupyter-workbench kernel via
        # `jupyter-workbench exec`, not in microct-analysis library code.
        # DurableEventLog is the shipped in-kernel implementation available there.
        from pathlib import Path
        import numpy as np
        import pyvista as pv
        from skimage import measure
        from jupyter_workbench.adapters.visualization.event_log import DurableEventLog
        from jupyter_workbench.adapters.visualization.pyvista_trame import PyVistaTrameHelper
        from mouse_ct import artifacts
        from mouse_ct.picker_domain import build_scene, initial_state
        from mouse_ct.types import Component, SeedAssignment

        output_dir = Path({output_dir!r})
        requested_component_indices = {component_indices!r}
        requested_scan_fingerprint = {scan_fingerprint!r}
        if not output_dir.exists():
            raise FileNotFoundError(f"Pipeline output directory not found: {{output_dir}}")

        component_summary = artifacts.read_json_artifact(output_dir, 'artifacts/components.json')
        segmentation = artifacts.read_json_artifact(output_dir, 'artifacts/segmentation.json')
        scan_fingerprint = requested_scan_fingerprint or component_summary.get('scan_fingerprint_id', 'unknown-scan')
        components_payload = component_summary.get('retained', [])
        if requested_component_indices is not None:
            wanted = set(requested_component_indices)
            components_payload = [c for c in components_payload if int(c['index']) in wanted]

        def _component_from_payload(payload):
            return Component(
                index=int(payload['index']),
                voxel_count=int(payload['voxel_count']),
                centroid_zyx=tuple(float(v) for v in payload['centroid_zyx']),
                centroid_mm=tuple(float(v) for v in payload.get('centroid_mm', payload['centroid_zyx'])),
                bbox_zyx=tuple(tuple(int(v) for v in axis) for axis in payload['bbox_zyx']),
                edge_faces=tuple(payload.get('edge_faces', ())),
            )

        def _load_array(relative_path):
            path = output_dir / relative_path
            if not path.exists():
                return None
            if path.suffix == '.npy':
                return np.load(path)
            if path.suffix == '.npz':
                data = np.load(path)
                return data[data.files[0]]
            return None

        def _mesh_for_component(component, labels):
            if labels is None:
                return None
            mask = (labels == component.index).astype(np.uint8)
            if int(mask.sum()) == 0:
                return None
            try:
                verts, faces, _, _ = measure.marching_cubes(mask, level=0.5, step_size=2)
            except (ValueError, RuntimeError) as exc:
                print({{'warning': 'component mesh unavailable', 'component_index': component.index, 'reason': str(exc)}})
                return None
            face_block = np.hstack([np.full((faces.shape[0], 1), 3, dtype=faces.dtype), faces])
            return pv.PolyData(verts, face_block)

        def _centroid_marker(component):
            center = tuple(reversed(component.centroid_zyx))
            radius = max(1.0, float(component.voxel_count) ** (1 / 3) / 4)
            return pv.Sphere(radius=radius, center=center)

        component_objects = [_component_from_payload(c) for c in components_payload]
        components_by_index = {{c.index: c for c in component_objects}}

        initial_assignments = {{}}
        candidates_path = output_dir / 'artifacts/landmark-candidates.json'
        if candidates_path.exists():
            candidates = artifacts.read_json_artifact(output_dir, 'artifacts/landmark-candidates.json')
            for candidate in candidates.get('candidates', []):
                comp = components_by_index.get(int(candidate['component_index']))
                if comp is not None:
                    initial_assignments[candidate['landmark_name']] = SeedAssignment(
                        component_index=comp.index,
                        voxel_count=comp.voxel_count,
                        centroid_zyx=comp.centroid_zyx,
                    )

        anchor_indices = (
            initial_assignments.get('femur').component_index if 'femur' in initial_assignments else None,
            initial_assignments.get('tibia').component_index if 'tibia' in initial_assignments else None,
        )
        scene = build_scene(
            components=component_objects,
            initial=initial_assignments,
            anchor_indices=anchor_indices,
            max_meshes=min(32, len(component_objects)),
            scan_fingerprint=scan_fingerprint,
        )
        picker_state = initial_state(scene, initial_assignments)
        components_by_id = {{p.component_id: p.component for p in scene.pickables}}

        labels = _load_array(segmentation.get('labels', '')) if segmentation.get('labels') else None
        if labels is None:
            print({{'warning': 'real label volume unavailable; using centroid markers as fallback'}})

        plotter = pv.Plotter()
        mesh_count = 0
        marker_count = 0
        for pickable in scene.pickables:
            mesh = _mesh_for_component(pickable.component, labels)
            if mesh is None:
                mesh = _centroid_marker(pickable.component)
                marker_count += 1
            else:
                mesh_count += 1
            plotter.add_mesh(mesh, color=pickable.initial_color, name=pickable.actor_name, pickable=True)
        plotter.add_text(scene.help_text, name='picker-help', font_size=10)
        plotter.add_axes()

        events = DurableEventLog('.jupyter-workbench', 'landmark-picking')
        viz = PyVistaTrameHelper('.jupyter-workbench')
        viz.register_pick_callback('landmark-picking', plotter, events)
        viz.register_key_callback('landmark-picking', plotter, events)
        viz.register_camera_callback('landmark-picking', plotter, events)
        plotter.show(jupyter_backend='trame')
        print({{'scene': 'landmark-picking', 'active_bone': picker_state.active_bone, 'pickables': len(scene.pickables), 'initial_assignments': sorted(initial_assignments), 'meshes': mesh_count, 'centroid_markers': marker_count}})
        """
    ).strip()


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
