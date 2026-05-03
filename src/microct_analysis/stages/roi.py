"""ROI definition and extraction stage driver."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from microct_analysis.domain.artifact_contracts import screenshot_path


def run_roi(
    landmark_artifacts: dict[str, str],
    segmentation_artifacts: dict[str, str],
    workflow_roi_definitions: list[dict[str, Any]],
    output_dir: str = "roi",
) -> dict[str, Any]:
    """Define workflow-relative ROI regions and emit boundaries plus mask paths."""

    output_root = Path(output_dir)
    masks_root = output_root / "masks"
    masks_root.mkdir(parents=True, exist_ok=True)

    positions = _load_json(landmark_artifacts.get("positions"))
    orientation_frame = _load_json(landmark_artifacts.get("orientation_frame"))
    landmarks = {item["id"]: item for item in positions.get("landmarks", [])}
    spacing = _triple(positions.get("spacing", (1.0, 1.0, 1.0)))

    roi_entries: list[dict[str, Any]] = []
    roi_masks: dict[str, str] = {}
    for definition in workflow_roi_definitions:
        roi = compute_roi_boundary(definition, landmarks, spacing)
        roi_entries.append(roi)
        mask_path = masks_root / f"{roi['id']}.json"
        _write_json(mask_path, {"roi_id": roi["id"], "bounds_voxel": roi["bounds_voxel"], "source_labels": segmentation_artifacts})
        roi_masks[roi["id"]] = str(mask_path)

    payload = {
        "rois": roi_entries,
        "orientation_frame": orientation_frame,
        "source_artifacts": {"landmarks": dict(landmark_artifacts), "segmentation": dict(segmentation_artifacts)},
        "overlay": {
            "scene": "persistent",
            "visible": True,
            "description": "ROI boundaries should be drawn as boxes in the analyst-owned PyVista scene.",
        },
    }
    _write_json(output_root / "roi_definitions.json", payload)

    confidence = "high" if all(entry["anchor_landmark"] in landmarks for entry in roi_entries) else "medium"
    return {
        "stage": "roi",
        "confidence": confidence,
        "evidence": _evidence(roi_entries, confidence),
        "recommended_action": {"high": "proceed", "medium": "flag", "low": "pause"}[confidence],
        "artifacts": {
            "roi_definitions": str(output_root / "roi_definitions.json"),
            "roi_masks": roi_masks,
            "screenshots": [screenshot_path("roi", 1)],
        },
    }


def compute_roi_boundary(
    definition: dict[str, Any], landmarks: dict[str, dict[str, Any]], spacing: tuple[float, float, float]
) -> dict[str, Any]:
    """Compute one ROI box from a landmark anchor and workflow offsets."""

    roi_id = str(definition.get("id") or definition.get("name"))
    anchor_id = str(
        definition.get("anchor_landmark")
        or definition.get("growth_plate_landmark")
        or definition.get("relative_to")
        or "growth_plate"
    )
    anchor = landmarks.get(anchor_id, {"voxel": [0.0, 0.0, 0.0], "physical": [0.0, 0.0, 0.0]})
    anchor_voxel = _triple(anchor.get("voxel", (0.0, 0.0, 0.0)))
    anchor_physical = _triple(anchor.get("physical", anchor_voxel))

    offsets_um = _axis_offsets(definition.get("offsets_um") or definition.get("growth_plate_offsets_um") or {})
    size_um = _axis_size(definition.get("size_um") or definition.get("extent_um") or definition.get("dimensions_um") or {})
    start_physical = tuple(anchor_physical[index] + offsets_um[index] for index in range(3))
    end_physical = tuple(start_physical[index] + size_um[index] for index in range(3))
    start_voxel = tuple(start_physical[index] / spacing[index] for index in range(3))
    end_voxel = tuple(end_physical[index] / spacing[index] for index in range(3))

    return {
        "id": roi_id,
        "anchor_landmark": anchor_id,
        "positioning": "growth-plate-relative" if "growth_plate" in anchor_id or "growth_plate_offsets_um" in definition else "landmark-relative",
        "offsets_um": list(offsets_um),
        "size_um": list(size_um),
        "bounds_physical": [[min(start_physical[i], end_physical[i]), max(start_physical[i], end_physical[i])] for i in range(3)],
        "bounds_voxel": [[min(start_voxel[i], end_voxel[i]), max(start_voxel[i], end_voxel[i])] for i in range(3)],
    }


def _axis_offsets(raw: dict[str, Any]) -> tuple[float, float, float]:
    return (
        float(raw.get("z", raw.get("superior_inferior", raw.get("inferior", 0.0)))),
        float(raw.get("y", raw.get("anterior_posterior", 0.0))),
        float(raw.get("x", raw.get("medial_lateral", 0.0))),
    )


def _axis_size(raw: dict[str, Any]) -> tuple[float, float, float]:
    return (
        float(raw.get("z", raw.get("height", 1000.0))),
        float(raw.get("y", raw.get("depth", 1000.0))),
        float(raw.get("x", raw.get("width", 1000.0))),
    )


def _evidence(rois: list[dict[str, Any]], confidence: str) -> str:
    detail = "; ".join(f"{roi['id']} from {roi['anchor_landmark']} offsets {roi['offsets_um']} µm" for roi in rois)
    if confidence == "high":
        return f"Computed workflow-defined ROI boundaries and prepared persistent-scene overlays: {detail}."
    return f"Computed ROI boundaries with fallback anchor coordinates; review overlays before measurement: {detail}."


def _load_json(path: str | None) -> dict[str, Any]:
    if not path or not Path(path).exists():
        return {}
    return json.loads(Path(path).read_text())


def _triple(raw: Any) -> tuple[float, float, float]:
    values = list(raw)
    if len(values) != 3:
        raise ValueError("expected three coordinate values")
    return (float(values[0]), float(values[1]), float(values[2]))


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
