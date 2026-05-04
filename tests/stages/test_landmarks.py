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


def test_pca_orientation_applied_when_tibia_label_present(tmp_path: Path) -> None:
    labels = np.zeros((9, 9, 9), dtype=np.uint8)
    labels[3:5, 1:4, 2:8] = 3
    label_path = tmp_path / "labels.npy"
    np.save(label_path, labels)
    assignments_path = tmp_path / "structure_assignments.json"
    assignments_path.write_text(json.dumps({"assignments": {"tibia": 3}, "spacing": [1.0, 1.0, 1.0]}))

    report = run_landmarks_orientation(
        {"labels": str(label_path), "structure_assignments": str(assignments_path)},
        [{"id": "lateral_tibial_condyle_edge", "structure": "tibia", "domain": "tibial_2d_slice"}],
        {"target_plane": "frontal"},
        output_dir=str(tmp_path / "landmarks"),
    )

    frame = json.loads((tmp_path / "landmarks" / "orientation_frame.json").read_text())
    oriented = np.load(tmp_path / "landmarks" / "oriented_labels.npy")
    assert report["confidence"] == "high"
    assert frame["pca_orientation"]["applied"] is True
    assert frame["pca_orientation"]["label_interpolation_order"] == 0
    assert frame["pca_orientation"]["intensity_interpolation_order"] == 1
    assert oriented.shape == labels.shape
    assert np.count_nonzero(oriented == 3) >= 3


def test_pca_orientation_fallback_marks_tibial_landmarks_low_confidence(tmp_path: Path) -> None:
    labels = np.zeros((5, 5, 5), dtype=np.uint8)
    labels[2, 2, 2] = 3
    label_path = tmp_path / "labels.npy"
    np.save(label_path, labels)
    assignments_path = tmp_path / "structure_assignments.json"
    assignments_path.write_text(json.dumps({"assignments": {"tibia": 3}, "spacing": [1.0, 1.0, 1.0]}))

    report = run_landmarks_orientation(
        {"labels": str(label_path), "structure_assignments": str(assignments_path)},
        [{"id": "articular_surface_proximal", "structure": "tibia", "domain": "tibial_2d_slice"}],
        {"target_plane": "frontal"},
        output_dir=str(tmp_path / "landmarks"),
    )

    positions = json.loads((tmp_path / "landmarks" / "positions.json").read_text())
    report_text = (tmp_path / "landmarks" / "orientation_report.md").read_text()
    assert report["confidence"] == "low"
    assert positions["landmarks"][0]["confidence"] == "low"
    assert positions["landmarks"][0]["requires_user_confirmation"] is True
    assert "PyVista" in report_text


def test_oriented_tibial_landmark_differs_from_unoriented_asymmetric_volume(tmp_path: Path) -> None:
    labels = np.zeros((9, 9, 9), dtype=np.uint8)
    labels[3:5, 1:4, 2:8] = 3
    label_path = tmp_path / "labels.npy"
    np.save(label_path, labels)
    assignments_path = tmp_path / "structure_assignments.json"
    assignments_path.write_text(json.dumps({"assignments": {"tibia": 3}, "spacing": [1.0, 1.0, 1.0]}))

    run_landmarks_orientation(
        {"labels": str(label_path), "structure_assignments": str(assignments_path)},
        [{"id": "articular_surface_proximal", "structure": "tibia", "domain": "tibial_2d_slice"}],
        {"target_plane": "frontal"},
        output_dir=str(tmp_path / "landmarks"),
    )

    positions = json.loads((tmp_path / "landmarks" / "positions.json").read_text())
    oriented = np.load(tmp_path / "landmarks" / "oriented_labels.npy")
    original_articular_z = int(np.flatnonzero((labels == 3).reshape(labels.shape[0], -1).sum(axis=1))[0])
    assert not np.array_equal(oriented, labels)
    assert positions["landmarks"][0]["voxel"][0] != float(original_articular_z)
