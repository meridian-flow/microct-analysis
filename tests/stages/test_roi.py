from __future__ import annotations

import json
from pathlib import Path

from microct_analysis.stages.roi import compute_roi_boundary, run_roi


def test_compute_roi_boundary_applies_growth_plate_relative_offsets() -> None:
    roi = compute_roi_boundary(
        {
            "id": "proximal_tibia_trabecular",
            "growth_plate_landmark": "tibia_growth_plate",
            "growth_plate_offsets_um": {"z": 50, "y": -100, "x": -200},
            "size_um": {"z": 500, "y": 400, "x": 300},
        },
        {"tibia_growth_plate": {"voxel": [10, 20, 30], "physical": [100, 200, 300]}},
        (10.0, 10.0, 10.0),
    )

    assert roi["positioning"] == "growth-plate-relative"
    assert roi["bounds_physical"] == [[150.0, 650.0], [100.0, 500.0], [100.0, 400.0]]
    assert roi["bounds_voxel"] == [[15.0, 65.0], [10.0, 50.0], [10.0, 40.0]]


def test_run_roi_writes_definitions_masks_and_overlay_contract(tmp_path: Path) -> None:
    landmark_dir = tmp_path / "landmarks"
    landmark_dir.mkdir()
    positions_path = landmark_dir / "positions.json"
    frame_path = landmark_dir / "orientation_frame.json"
    positions_path.write_text(
        json.dumps(
            {
                "spacing": [5, 10, 20],
                "landmarks": [{"id": "growth_plate", "voxel": [2, 3, 4], "physical": [10, 30, 80]}],
            }
        )
    )
    frame_path.write_text(json.dumps({"target_plane": "frontal"}))

    report = run_roi(
        {"positions": str(positions_path), "orientation_frame": str(frame_path)},
        {"labels": "segmentation/labels.nii.gz"},
        [{"id": "tibia_roi", "growth_plate_landmark": "growth_plate", "growth_plate_offsets_um": {"z": 25}, "size_um": {"z": 100, "y": 200, "x": 400}}],
        output_dir=str(tmp_path / "roi"),
    )

    payload = json.loads((tmp_path / "roi" / "roi_definitions.json").read_text())
    assert report["confidence"] == "high"
    assert report["artifacts"]["roi_masks"]["tibia_roi"].endswith("roi/masks/tibia_roi.json")
    assert payload["overlay"]["scene"] == "persistent"
    assert payload["rois"][0]["bounds_voxel"] == [[7.0, 27.0], [3.0, 23.0], [4.0, 24.0]]
