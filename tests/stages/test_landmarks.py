from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from microct_analysis.stages.landmarks_orientation import compute_orientation_frame, run_landmarks_orientation


def test_landmark_positions_written_from_label_centroid_and_extrema(tmp_path: Path) -> None:
    labels = np.zeros((5, 5, 5), dtype=np.uint8)
    labels[1:4, 2:4, 1:3] = 7
    label_path = tmp_path / "labels.npy"
    np.save(label_path, labels)
    assignments_path = tmp_path / "structure_assignments.json"
    assignments_path.write_text(json.dumps({"assignments": {"femur": 7}, "spacing": [10, 20, 30]}))

    report = run_landmarks_orientation(
        {"labels": str(label_path), "structure_assignments": str(assignments_path)},
        [
            {"id": "femur_center", "structure": "femur", "method": "centroid"},
            {"id": "growth_plate", "structure": "femur", "method": "distal"},
        ],
        {"axes": {"superior_inferior": {"from": "femur_center", "to": "growth_plate"}}, "target_plane": "frontal"},
        output_dir=str(tmp_path / "landmarks"),
    )

    positions = json.loads((tmp_path / "landmarks" / "positions.json").read_text())
    assert report["confidence"] == "high"
    assert positions["landmarks"][0]["voxel"] == [2.0, 2.5, 1.5]
    assert positions["landmarks"][0]["physical"] == [20.0, 50.0, 45.0]
    assert positions["landmarks"][1]["voxel"][0] == 3.0


def test_orientation_transform_records_axis_explanation_and_translation() -> None:
    frame = compute_orientation_frame(
        [
            {"id": "origin", "physical": [10.0, 0.0, 0.0]},
            {"id": "distal", "physical": [20.0, 0.0, 0.0]},
        ],
        {
            "origin_landmark": "origin",
            "target_plane": "frontal",
            "axes": {"superior_inferior": {"from": "origin", "to": "distal"}},
        },
    )

    assert frame["translation"] == [-10.0, -0.0, -0.0]
    assert frame["axes"]["superior_inferior"] == [1.0, 0.0, 0.0]
    assert "workflow frontal plane" in frame["explanation"]
    assert "superior-inferior now follows" in frame["explanation"]
