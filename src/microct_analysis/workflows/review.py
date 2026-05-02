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


def segmentation_setup_code(scan_path: str) -> str:
    """Generate Python code for segmentation scene setup."""
    return dedent(
        f"""
        from pathlib import Path
        import pyvista as pv
        from jupyter_workbench.adapters.visualization.event_log import DurableEventLog
        from jupyter_workbench.adapters.visualization.pyvista_trame import PyVistaTrameHelper
        from mouse_ct import artifacts
        from mouse_ct.picker_domain import build_scene

        scan_path = Path({scan_path!r})
        output_dir = Path('microct-output')
        output_dir.mkdir(exist_ok=True)

        manifest = artifacts.load_manifest(output_dir) if artifacts.manifest_path(output_dir).exists() else None
        component_summary = artifacts.read_json_artifact(output_dir, 'artifacts/components.json')
        components = component_summary.get('retained', [])
        scan_fingerprint = component_summary.get('scan_fingerprint_id', str(scan_path))

        from types import SimpleNamespace
        component_objects = [SimpleNamespace(**c) for c in components]
        scene = build_scene(
            components=component_objects,
            initial={{}},
            anchor_indices=(None, None),
            max_meshes=min(24, len(component_objects)),
            scan_fingerprint=scan_fingerprint,
        )
        components_by_id = {{p.component_id: p.component for p in scene.pickables}}

        plotter = pv.Plotter()
        for pickable in scene.pickables:
            center = tuple(reversed(pickable.component.centroid_zyx))
            radius = max(1.0, float(pickable.component.voxel_count) ** (1 / 3) / 4)
            mesh = pv.Sphere(radius=radius, center=center)
            plotter.add_mesh(mesh, color=pickable.initial_color, name=pickable.actor_name, pickable=True)
        plotter.add_axes()
        plotter.add_text(scene.help_text, name='picker-help', font_size=10)

        events = DurableEventLog('.jupyter-workbench', 'seg-review')
        viz = PyVistaTrameHelper('.jupyter-workbench')
        viz.register_pick_callback('seg-review', plotter, events)
        viz.register_key_callback('seg-review', plotter, events)
        viz.register_camera_callback('seg-review', plotter, events)
        plotter.show(jupyter_backend='trame')
        print({{'scene': 'segmentation-review', 'pickables': len(scene.pickables), 'manifest': manifest}})
        """
    ).strip()


def landmark_picking_code(component_indices: list[int], scan_fingerprint: str) -> str:
    """Generate Python code for landmark picking scene setup."""
    return dedent(
        f"""
        import pyvista as pv
        from types import SimpleNamespace
        from jupyter_workbench.adapters.visualization.event_log import DurableEventLog
        from jupyter_workbench.adapters.visualization.pyvista_trame import PyVistaTrameHelper
        from mouse_ct.picker_domain import build_scene, initial_state

        component_indices = {component_indices!r}
        scan_fingerprint = {scan_fingerprint!r}
        component_objects = [
            SimpleNamespace(
                index=i,
                voxel_count=1,
                centroid_zyx=(float(i), 0.0, 0.0),
                centroid_mm=(float(i), 0.0, 0.0),
                bbox_zyx=((i, i + 1), (0, 1), (0, 1)),
                edge_faces=(),
            )
            for i in component_indices
        ]
        scene = build_scene(
            components=component_objects,
            initial={{}},
            anchor_indices=(None, None),
            max_meshes=len(component_objects),
            scan_fingerprint=scan_fingerprint,
        )
        picker_state = initial_state(scene, {{}})
        components_by_id = {{p.component_id: p.component for p in scene.pickables}}

        plotter = pv.Plotter()
        for pickable in scene.pickables:
            mesh = pv.Sphere(radius=1.0, center=tuple(reversed(pickable.component.centroid_zyx)))
            plotter.add_mesh(mesh, color=pickable.initial_color, name=pickable.actor_name, pickable=True)
        plotter.add_text(scene.help_text, name='picker-help', font_size=10)
        plotter.add_axes()

        events = DurableEventLog('.jupyter-workbench', 'landmark-picking')
        viz = PyVistaTrameHelper('.jupyter-workbench')
        viz.register_pick_callback('landmark-picking', plotter, events)
        viz.register_key_callback('landmark-picking', plotter, events)
        viz.register_camera_callback('landmark-picking', plotter, events)
        plotter.show(jupyter_backend='trame')
        print({{'scene': 'landmark-picking', 'active_bone': picker_state.active_bone, 'pickables': len(scene.pickables)}})
        """
    ).strip()


def event_poll_code(session_id: str, cursor: int, timeout: float = 30.0) -> str:
    """Generate Python code to poll events from the durable event log."""
    return dedent(
        f"""
        from jupyter_workbench.adapters.visualization.event_log import DurableEventLog

        events = DurableEventLog('.jupyter-workbench', {session_id!r})
        new_events, cursor, timed_out = events.wait({cursor}, timeout={timeout!r})
        print({{'events': new_events, 'cursor': cursor, 'timed_out': timed_out}})
        """
    ).strip()


def screenshot_code(session_id: str, root_dir: str, filename: str) -> str:
    """Generate Python code to capture a screenshot."""
    return dedent(
        f"""
        from jupyter_workbench.adapters.visualization.screenshots import capture_screenshot

        shot = capture_screenshot({session_id!r}, {root_dir!r}, {filename!r}, plotter=plotter)
        print(shot)
        """
    ).strip()
