"""Landmark placement and orientation correction stage driver."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from microct_analysis.domain.artifact_contracts import screenshot_path

_AXIS_NAMES = {0: "superior-inferior", 1: "anterior-posterior", 2: "medial-lateral"}


def run_landmarks_orientation(
    segmentation_artifacts: dict[str, str],
    workflow_landmarks: list[dict[str, Any]],
    workflow_orientation: dict[str, Any],
    output_dir: str = "landmarks",
) -> dict[str, Any]:
    """Place workflow landmarks, compute orientation frame, and emit artifacts."""

    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)

    labels = _load_label_volume(segmentation_artifacts.get("labels"))
    assignments = _load_json(segmentation_artifacts.get("structure_assignments"))
    spacing = _spacing_from_artifacts(segmentation_artifacts, assignments)

    positions = {
        "landmarks": [
            _compute_landmark(definition, labels, assignments, spacing) for definition in workflow_landmarks
        ],
        "coordinate_system": "volume_zyx",
        "spacing": list(spacing),
        "source_artifacts": dict(segmentation_artifacts),
    }

    orientation_frame = compute_orientation_frame(positions["landmarks"], workflow_orientation)
    _write_json(output_root / "positions.json", positions)
    _write_json(output_root / "orientation_frame.json", orientation_frame)

    confidence, evidence = _landmark_confidence(positions["landmarks"], orientation_frame)
    return {
        "stage": "landmarks",
        "confidence": confidence,
        "evidence": evidence,
        "recommended_action": _recommended_action(confidence),
        "artifacts": {
            "positions": str(output_root / "positions.json"),
            "orientation_frame": str(output_root / "orientation_frame.json"),
            "screenshots": [screenshot_path("landmarks", 1)],
        },
    }


def compute_orientation_frame(landmarks: list[dict[str, Any]], workflow_orientation: dict[str, Any]) -> dict[str, Any]:
    """Compute target orientation vectors and plain-language axis-change explanation."""

    by_id = {item["id"]: np.asarray(item["physical"], dtype=float) for item in landmarks}
    axes: dict[str, list[float]] = {}
    for axis_name, spec in (workflow_orientation.get("axes") or {}).items():
        vector = _axis_vector(spec, by_id)
        axes[axis_name] = _unit(vector).round(8).tolist()

    if not axes:
        axes = {
            "superior_inferior": [1.0, 0.0, 0.0],
            "anterior_posterior": [0.0, 1.0, 0.0],
            "medial_lateral": [0.0, 0.0, 1.0],
        }

    target_plane = str(workflow_orientation.get("target_plane", "frontal"))
    transform = {
        "type": "landmark-derived-rigid-orientation",
        "target_plane": target_plane,
        "axes": axes,
        "translation": _translation(workflow_orientation, by_id),
        "rotation_matrix": _rotation_matrix(axes),
        "explanation": explain_axis_changes(axes, target_plane),
        "source_landmarks": sorted(by_id),
    }
    return transform


def explain_axis_changes(axes: dict[str, list[float]], target_plane: str) -> str:
    """Explain orientation correction in operator-facing language."""

    pieces = [f"Aligned the specimen to the workflow {target_plane} plane."]
    for axis_name, vector in axes.items():
        dominant = int(np.argmax(np.abs(np.asarray(vector, dtype=float))))
        direction = "positive" if vector[dominant] >= 0 else "negative"
        readable = axis_name.replace("_", "-")
        pieces.append(f"{readable} now follows the {direction} {_AXIS_NAMES[dominant]} volume direction.")
    return " ".join(pieces)


def _compute_landmark(
    definition: dict[str, Any], labels: np.ndarray | None, assignments: dict[str, Any], spacing: tuple[float, float, float]
) -> dict[str, Any]:
    landmark_id = str(definition.get("id") or definition.get("name"))
    structure = str(definition.get("structure") or definition.get("target_structure") or "")
    method = str(definition.get("method", "centroid"))
    label_value = _label_for_structure(structure, assignments, definition)
    voxel = _position_from_definition(definition, labels, label_value, method)
    physical = tuple(float(voxel[index]) * spacing[index] for index in range(3))
    return {
        "id": landmark_id,
        "structure": structure,
        "method": method,
        "label": label_value,
        "voxel": [float(value) for value in voxel],
        "physical": [float(value) for value in physical],
        "confidence": "high" if labels is not None or "voxel" in definition or "physical" in definition else "medium",
    }


def _position_from_definition(
    definition: dict[str, Any], labels: np.ndarray | None, label_value: int | None, method: str
) -> tuple[float, float, float]:
    if "voxel" in definition:
        return _triple(definition["voxel"])
    if "physical" in definition:
        return _triple(definition["physical"])
    if labels is None or label_value is None:
        return (0.0, 0.0, 0.0)
    coords = np.argwhere(labels == label_value)
    if coords.size == 0:
        return (0.0, 0.0, 0.0)
    if method in {"superior", "proximal"}:
        return _triple(coords[np.argmin(coords[:, 0])])
    if method in {"inferior", "distal", "growth_plate"}:
        return _triple(coords[np.argmax(coords[:, 0])])
    return _triple(coords.mean(axis=0))


def _axis_vector(spec: Any, landmarks: dict[str, np.ndarray]) -> np.ndarray:
    if isinstance(spec, dict) and "from" in spec and "to" in spec:
        return landmarks[str(spec["to"])] - landmarks[str(spec["from"])]
    if isinstance(spec, dict) and "vector" in spec:
        return np.asarray(spec["vector"], dtype=float)
    if isinstance(spec, (list, tuple)):
        return np.asarray(spec, dtype=float)
    raise ValueError(f"unsupported orientation axis spec: {spec!r}")


def _unit(vector: np.ndarray) -> np.ndarray:
    norm = float(np.linalg.norm(vector))
    if norm == 0:
        raise ValueError("orientation axis vector has zero length")
    return vector / norm


def _rotation_matrix(axes: dict[str, list[float]]) -> list[list[float]]:
    rows = list(axes.values())[:3]
    identity = ([1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0])
    while len(rows) < 3:
        rows.append(identity[len(rows)])
    return rows


def _translation(workflow_orientation: dict[str, Any], landmarks: dict[str, np.ndarray]) -> list[float]:
    origin_id = workflow_orientation.get("origin_landmark")
    if origin_id and str(origin_id) in landmarks:
        return (-landmarks[str(origin_id)]).round(8).tolist()
    return [0.0, 0.0, 0.0]


def _landmark_confidence(landmarks: list[dict[str, Any]], orientation_frame: dict[str, Any]) -> tuple[str, str]:
    weak = [item["id"] for item in landmarks if item.get("confidence") != "high"]
    if weak:
        return "medium", f"Computed landmarks, but {', '.join(weak)} used fallback coordinates."
    return "high", "Landmarks placed from workflow definitions and orientation transform recorded. " + orientation_frame["explanation"]


def _recommended_action(confidence: str) -> str:
    return {"high": "proceed", "medium": "flag", "low": "pause"}[confidence]


def _load_label_volume(path: str | None) -> np.ndarray | None:
    if not path:
        return None
    label_path = Path(path)
    if not label_path.exists() or label_path.suffix not in {".npy", ".npz", ".json"}:
        return None
    if label_path.suffix == ".npy":
        return np.load(label_path)
    if label_path.suffix == ".npz":
        data = np.load(label_path)
        return data[data.files[0]]
    return np.asarray(json.loads(label_path.read_text()))


def _load_json(path: str | None) -> dict[str, Any]:
    if not path or not Path(path).exists():
        return {}
    return json.loads(Path(path).read_text())


def _spacing_from_artifacts(segmentation_artifacts: dict[str, str], assignments: dict[str, Any]) -> tuple[float, float, float]:
    raw = segmentation_artifacts.get("spacing") or assignments.get("spacing") or (1.0, 1.0, 1.0)
    return _triple(raw)


def _label_for_structure(structure: str, assignments: dict[str, Any], definition: dict[str, Any]) -> int | None:
    if "label" in definition:
        return int(definition["label"])
    mapping = assignments.get("assignments", assignments)
    value = mapping.get(structure) if isinstance(mapping, dict) else None
    return int(value) if isinstance(value, int | float | str) and str(value).lstrip("-").isdigit() else None


def _triple(raw: Any) -> tuple[float, float, float]:
    values = list(raw)
    if len(values) != 3:
        raise ValueError("expected three coordinate values")
    return (float(values[0]), float(values[1]), float(values[2]))


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
