from __future__ import annotations

import ast
import contextlib
import io
import sys
import types

import pytest

from microct_analysis.workflows.review import (
    event_poll_code,
    landmark_picking_code,
    screenshot_code,
    segmentation_setup_code,
)


def test_segmentation_setup_code_contains_required_review_hooks(compile_snippet) -> None:
    snippet = segmentation_setup_code("/data/scan-a.nii.gz", output_dir="pipeline-output")
    compile_snippet(snippet, filename="segmentation_setup_code.py")

    assert "scan_path = Path('/data/scan-a.nii.gz')" in snippet
    assert "output_dir = Path('pipeline-output')" in snippet
    assert "DurableEventLog('.jupyter-workbench', 'seg-review')" in snippet
    assert "viz.register_pick_callback('seg-review', plotter, events)" in snippet
    assert "viz.register_key_callback('seg-review', plotter, events)" in snippet
    assert "viz.register_camera_callback('seg-review', plotter, events)" in snippet
    assert "scan_fingerprint = component_summary.get('scan_fingerprint_id', str(scan_path))" in snippet


def test_landmark_picking_code_contains_requested_filters_and_hooks(compile_snippet) -> None:
    snippet = landmark_picking_code(
        component_indices=[3, 5, 8],
        scan_fingerprint="scan-123",
        output_dir="review-output",
    )
    compile_snippet(snippet, filename="landmark_picking_code.py")

    assert "requested_component_indices = [3, 5, 8]" in snippet
    assert "requested_scan_fingerprint = 'scan-123'" in snippet
    assert "output_dir = Path('review-output')" in snippet
    assert "wanted = set(requested_component_indices)" in snippet
    assert "DurableEventLog('.jupyter-workbench', 'landmark-picking')" in snippet
    assert "viz.register_pick_callback('landmark-picking', plotter, events)" in snippet
    assert "viz.register_key_callback('landmark-picking', plotter, events)" in snippet
    assert "viz.register_camera_callback('landmark-picking', plotter, events)" in snippet


def test_event_poll_code_compiles_and_uses_session_cursor_timeout(compile_snippet) -> None:
    snippet = event_poll_code("review-42", cursor=17, timeout=9.5)
    compile_snippet(snippet, filename="event_poll_code.py")

    assert "DurableEventLog('.jupyter-workbench', 'review-42')" in snippet
    assert "events.wait(17, timeout=9.5)" in snippet
    assert "print({'events': new_events, 'cursor': cursor, 'timed_out': timed_out})" in snippet


def test_screenshot_code_compiles_and_calls_capture_with_filename(compile_snippet) -> None:
    snippet = screenshot_code("review-42", ".jupyter-workbench", "scene-final")
    compile_snippet(snippet, filename="screenshot_code.py")

    assert "from jupyter_workbench.adapters.visualization.screenshots import capture_screenshot" in snippet
    assert "shot = capture_screenshot('review-42', '.jupyter-workbench', 'scene-final', plotter=plotter)" in snippet
    assert "print(shot)" in snippet


def test_event_poll_code_executes_against_mocked_workbench(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[int, float]] = []

    class FakeDurableEventLog:
        def __init__(self, root_dir: str, session_id: str) -> None:
            assert root_dir == ".jupyter-workbench"
            assert session_id == "review-42"

        def wait(self, cursor: int, timeout: float = 30.0):
            calls.append((cursor, timeout))
            return ([{"seq": 18, "type": "pick.point", "payload": {"point_id": 7}}], 19, False)

    event_log_module = types.ModuleType("jupyter_workbench.adapters.visualization.event_log")
    setattr(event_log_module, "DurableEventLog", FakeDurableEventLog)
    workbench_module = types.ModuleType("jupyter_workbench")
    setattr(workbench_module, "__path__", [])
    adapters_module = types.ModuleType("jupyter_workbench.adapters")
    setattr(adapters_module, "__path__", [])
    visualization_module = types.ModuleType("jupyter_workbench.adapters.visualization")
    setattr(visualization_module, "__path__", [])
    monkeypatch.setitem(sys.modules, "jupyter_workbench", workbench_module)
    monkeypatch.setitem(sys.modules, "jupyter_workbench.adapters", adapters_module)
    monkeypatch.setitem(sys.modules, "jupyter_workbench.adapters.visualization", visualization_module)
    monkeypatch.setitem(sys.modules, "jupyter_workbench.adapters.visualization.event_log", event_log_module)

    snippet = event_poll_code("review-42", cursor=17, timeout=9.5)
    compiled = compile(ast.parse(snippet, filename="event_poll_code.py", mode="exec"), "event_poll_code.py", "exec")
    stdout = io.StringIO()

    with contextlib.redirect_stdout(stdout):
        exec(compiled, {"__name__": "__main__"})

    assert calls == [(17, 9.5)]
    printed = ast.literal_eval(stdout.getvalue().strip())
    assert printed == {
        "events": [{"seq": 18, "type": "pick.point", "payload": {"point_id": 7}}],
        "cursor": 19,
        "timed_out": False,
    }


def test_screenshot_code_executes_against_mocked_workbench(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, str, str, object]] = []

    def fake_capture_screenshot(session_id: str, root_dir: str, filename: str, plotter: object) -> str:
        calls.append((session_id, root_dir, filename, plotter))
        return f"{root_dir}/{session_id}/{filename}.png"

    screenshots_module = types.ModuleType("jupyter_workbench.adapters.visualization.screenshots")
    setattr(screenshots_module, "capture_screenshot", fake_capture_screenshot)
    workbench_module = types.ModuleType("jupyter_workbench")
    setattr(workbench_module, "__path__", [])
    adapters_module = types.ModuleType("jupyter_workbench.adapters")
    setattr(adapters_module, "__path__", [])
    visualization_module = types.ModuleType("jupyter_workbench.adapters.visualization")
    setattr(visualization_module, "__path__", [])
    monkeypatch.setitem(sys.modules, "jupyter_workbench", workbench_module)
    monkeypatch.setitem(sys.modules, "jupyter_workbench.adapters", adapters_module)
    monkeypatch.setitem(sys.modules, "jupyter_workbench.adapters.visualization", visualization_module)
    monkeypatch.setitem(sys.modules, "jupyter_workbench.adapters.visualization.screenshots", screenshots_module)

    snippet = screenshot_code("review-42", ".jupyter-workbench", "scene-final")
    compiled = compile(ast.parse(snippet, filename="screenshot_code.py", mode="exec"), "screenshot_code.py", "exec")
    plotter = object()
    stdout = io.StringIO()

    with contextlib.redirect_stdout(stdout):
        exec(compiled, {"__name__": "__main__", "plotter": plotter})

    assert calls == [("review-42", ".jupyter-workbench", "scene-final", plotter)]
    assert stdout.getvalue().strip() == ".jupyter-workbench/review-42/scene-final.png"
