"""Segmentation stage driver — executed via ``jupyter-workbench exec --file``."""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path
from typing import Any, cast

import numpy as np
from scipy import ndimage

from microct_analysis.domain.artifact_contracts import screenshot_path
from microct_analysis.processing.calibration import analyze_histogram, derive_thresholds
from microct_analysis.processing.io import save_nifti, save_provenance
from microct_analysis.processing.preprocess import median_filter
from microct_analysis.processing.sanity import check_bone_volume_ordering
from microct_analysis.processing.segmentation import extract_label, seed_from_region, watershed_segment
from microct_analysis.processing.threshold import binary_mask
from microct_analysis.processing.types import LabelVolume, ScanVolume, SegmentationResult, Thresholds

BONE_ORDER = ("femur", "tibia", "fibula", "patella")
CONFUNDER_LABELS = {
    "sesamoid": "Sesamoid bones near joints may be misidentified as additional structures.",
    "articular-bridging-suspected": "Osteophytes or bridging may connect adjacent bones.",
    "partial-bone-at-scan-boundary": "Partial bones at scan boundaries may bias assignments.",
}


def run_segmentation(
    volume: Any,
    spacing: tuple[float, ...],
    thresholds: dict[str, Any] | Thresholds | None,
    workflow_thresholds: dict[str, Any] | None,
    output_dir: str = "segmentation",
) -> dict[str, Any]:
    """Run local preprocessing, thresholding, seeded watershed, and reporting."""

    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    workflow_thresholds = workflow_thresholds or {}
    spacing_zyx = _spacing_zyx(spacing)
    scan = _scan_from_inputs(volume, spacing_zyx)

    try:
        derived, threshold_flags = _derive_or_fallback_thresholds(scan.data, thresholds)
        threshold_observations = compare_thresholds(derived, workflow_thresholds)
        filtered = median_filter(scan.data)
        mask = binary_mask(filtered, derived.bone_soft_tissue)
        labels, assignments, component_infos = _segment_or_use_labels(filtered, mask, workflow_thresholds, spacing_zyx)
    except _NeedsSeeds as exc:
        _write_json(output_root / "seeds.json", exc.seeds)
        _write_json(output_root / "structure_assignments.json", {"status": "needs-seeds", "reason": exc.reason})
        save_provenance({"status": "needs-seeds", "reason": exc.reason, "flags": exc.flags}, output_root / "metadata.json")
        return _report(
            status="needs-seeds",
            confidence="low",
            evidence=f"Structure identification ambiguous; seed curation required. {exc.reason}",
            output_root=output_root,
            flags=exc.flags,
            structure_assignments={},
            threshold_observations=[],
            confounders=[],
        )
    except Exception as exc:  # noqa: BLE001 - stage report captures failures.
        return _failure_report(output_root, f"segmentation failed: {exc}")

    confounders = detect_confounders(component_infos, [], scan.data.shape)
    sanity_warnings = check_bone_volume_ordering(labels)
    flags = threshold_flags + (["workflow-threshold-discrepancy"] if threshold_observations else []) + confounders + sanity_warnings

    save_nifti(labels.data, output_root / "labels.nii.gz", scan.affine)
    result = SegmentationResult(labels, assignments, threshold_observations, "high")
    _write_json(
        output_root / "structure_assignments.json",
        {"status": "ready", "assignments": assignments, "flags": flags},
    )
    save_provenance(
        {
            "status": "ready",
            "spacing": spacing_zyx,
            "thresholds": _jsonable(derived),
            "threshold_observations": threshold_observations,
            "structure_assignments": assignments,
            "flags": flags,
            "result": _jsonable(result),
        },
        output_root / "metadata.json",
    )
    _write_json(output_root / "seeds.json", _auto_seed_payload(component_infos))

    confidence = confidence_for_segmentation(
        threshold_observations=threshold_observations,
        confounders=confounders,
        sanity_warnings=sanity_warnings,
    )
    return _report(
        status="ready",
        confidence=confidence,
        evidence=_evidence(confidence, threshold_observations, confounders, sanity_warnings),
        output_root=output_root,
        flags=flags,
        structure_assignments=assignments,
        threshold_observations=threshold_observations,
        confounders=confounders,
    )


def compare_thresholds(derived: Thresholds, workflow_thresholds: dict[str, Any]) -> list[str]:
    """Return discrepancy notes comparing derived and workflow thresholds."""

    observations: list[str] = []
    tolerance = float(workflow_thresholds.get("tolerance_fraction", 0.15))
    fields = {"mask": "bone_soft_tissue", "marker": "subchondral_cortical", "bone_soft_tissue": "bone_soft_tissue"}
    for workflow_field, threshold_field in fields.items():
        expected = _threshold_value(workflow_thresholds, workflow_field)
        if expected is None:
            continue
        actual = float(getattr(derived, threshold_field))
        delta_fraction = abs(actual - float(expected)) / max(abs(float(expected)), 1.0)
        if delta_fraction > tolerance:
            observations.append(
                f"{workflow_field} threshold derived {actual:.3g} differs from workflow {float(expected):.3g} "
                f"by {delta_fraction:.1%} (> {tolerance:.0%})."
            )
    return observations


def detect_confounders(components: list[Any], prefiltered: list[Any], shape: tuple[int, int, int]) -> list[str]:
    """Detect known segmentation confounder signals from component geometry."""

    observations: list[str] = []
    if prefiltered or any(getattr(component, "edge_faces", ()) for component in components):
        observations.append(CONFUNDER_LABELS["partial-bone-at-scan-boundary"])
    if len(components) > 4:
        observations.append(CONFUNDER_LABELS["sesamoid"])
    z_extent = shape[0]
    for component in components:
        bbox = getattr(component, "bbox_zyx", None)
        if bbox is None:
            continue
        (zmin, zmax), _, _ = bbox
        if zmax - zmin > z_extent / 2 and zmin < z_extent / 3 and zmax > 2 * z_extent / 3:
            observations.append(CONFUNDER_LABELS["articular-bridging-suspected"])
            break
    return list(dict.fromkeys(observations))


def confidence_for_segmentation(*, threshold_observations: list[str], confounders: list[str], sanity_warnings: list[str]) -> str:
    if any("articular" in warning or "ambiguous" in warning for warning in sanity_warnings):
        return "low"
    if sanity_warnings or threshold_observations or confounders:
        return "medium"
    return "high"


@dataclasses.dataclass(frozen=True)
class _ComponentInfo:
    index: int
    voxel_count: int
    centroid_zyx: tuple[float, float, float]
    bbox_zyx: tuple[tuple[int, int], tuple[int, int], tuple[int, int]]
    edge_faces: tuple[str, ...]


class _NeedsSeeds(Exception):
    def __init__(self, reason: str, seeds: dict[str, Any], flags: list[str]) -> None:
        super().__init__(reason)
        self.reason = reason
        self.seeds = seeds
        self.flags = flags


def _derive_or_fallback_thresholds(volume: np.ndarray, thresholds: dict[str, Any] | Thresholds | None) -> tuple[Thresholds, list[str]]:
    manual = _thresholds_from_input(thresholds)
    if manual is not None:
        return manual, ["manual-thresholds-used"]
    scanner = thresholds.get("scanner", "scanco") if isinstance(thresholds, dict) else "scanco"
    _ = analyze_histogram(volume)
    return derive_thresholds(volume, scanner=str(scanner)), []


def _segment_or_use_labels(
    filtered: np.ndarray, mask: np.ndarray, workflow_thresholds: dict[str, Any], spacing: tuple[float, float, float]
) -> tuple[LabelVolume, dict[str, int], list[_ComponentInfo]]:
    labeled_input = workflow_thresholds.get("labels") if "labels" in workflow_thresholds else workflow_thresholds.get("labeled_input")
    if labeled_input is not None:
        data = np.asarray(labeled_input, dtype=np.uint16)
        assignments = _assign_from_labels(data)
        if len(assignments) < 2:
            raise _NeedsSeeds("labeled input contains too few structures", {}, ["ambiguous-bone-identity"])
        return LabelVolume(data=data, spacing=spacing, label_map=assignments), assignments, _components_from_labels(data)

    components = _components_from_mask(mask)
    if len(components) < 2:
        raise _NeedsSeeds("fewer than two bone-like components found", _auto_seed_payload(components), ["ambiguous-bone-identity"])
    assignments = {name: component.index for name, component in zip(BONE_ORDER, components, strict=False)}
    seed_points = {
        name: tuple(int(round(v)) for v in component.centroid_zyx) for name, component in zip(assignments, components, strict=False)
    }
    seeds = seed_from_region(filtered, mask, seed_points)
    grown = watershed_segment(filtered, seeds, mask).astype(np.uint16)
    # Exercise extract_label and normalize labels to assignment IDs.
    normalized = np.zeros_like(grown, dtype=np.uint16)
    for label_id in assignments.values():
        normalized[extract_label(grown, label_id)] = label_id
    return LabelVolume(data=normalized, spacing=spacing, label_map=assignments), assignments, components


def _components_from_mask(mask: np.ndarray) -> list[_ComponentInfo]:
    labeled, count = cast(tuple[np.ndarray, int], ndimage.label(mask))
    components = [_component_info(labeled, index) for index in range(1, count + 1)]
    return sorted(components, key=lambda item: item.voxel_count, reverse=True)


def _components_from_labels(labels: np.ndarray) -> list[_ComponentInfo]:
    return sorted(
        (_component_info(labels == label_id, int(label_id)) for label_id in np.unique(labels) if int(label_id) != 0),
        key=lambda item: item.voxel_count,
        reverse=True,
    )


def _component_info(labeled: np.ndarray, index: int) -> _ComponentInfo:
    coords = np.argwhere(labeled == index) if labeled.dtype.kind in "iu" else np.argwhere(labeled)
    mins = coords.min(axis=0)
    maxs = coords.max(axis=0) + 1
    shape = labeled.shape
    edge_faces = []
    for axis, name in enumerate("zyx"):
        if mins[axis] == 0:
            edge_faces.append(f"{name}_min")
        if maxs[axis] == shape[axis]:
            edge_faces.append(f"{name}_max")
    return _ComponentInfo(
        index=index,
        voxel_count=int(coords.shape[0]),
        centroid_zyx=tuple(float(v) for v in coords.mean(axis=0)),  # type: ignore[return-value]
        bbox_zyx=tuple((int(mins[i]), int(maxs[i])) for i in range(3)),  # type: ignore[assignment]
        edge_faces=tuple(edge_faces),
    )


def _assign_from_labels(labels: np.ndarray) -> dict[str, int]:
    components = _components_from_labels(labels)
    return {name: component.index for name, component in zip(BONE_ORDER, components, strict=False)}


def _auto_seed_payload(components: list[Any]) -> dict[str, Any]:
    return {
        "status": "auto-proposed",
        "seeds": [
            {"component_index": c.index, "voxel_count": c.voxel_count, "centroid_zyx": list(c.centroid_zyx)} for c in components
        ],
    }


def _scan_from_inputs(volume: Any, spacing: tuple[float, float, float]) -> ScanVolume:
    array = np.asarray(volume, dtype=np.float32)
    affine = np.eye(4, dtype=np.float64)
    affine[0, 0], affine[1, 1], affine[2, 2] = spacing[2], spacing[1], spacing[0]
    return ScanVolume(data=array, spacing=spacing, affine=affine, provenance={"source": "workbench-session"})


def _thresholds_from_input(thresholds: dict[str, Any] | Thresholds | None) -> Thresholds | None:
    if isinstance(thresholds, Thresholds):
        return thresholds
    if not isinstance(thresholds, dict):
        return None
    bone = _threshold_value(thresholds, "bone_soft_tissue") or _threshold_value(thresholds, "mask")
    cortical = _threshold_value(thresholds, "subchondral_cortical") or _threshold_value(thresholds, "marker")
    if bone is None or cortical is None:
        return None
    return Thresholds(bone_soft_tissue=int(bone), subchondral_cortical=int(cortical))


def _threshold_value(values: dict[str, Any], field: str) -> float | None:
    for key in (field, f"{field}_threshold"):
        if key in values and not isinstance(values[key], dict):
            return float(values[key])
    nested = values.get(field)
    if isinstance(nested, dict):
        for key in ("value", "threshold"):
            if key in nested:
                return float(nested[key])
    return None


def _spacing_zyx(spacing: tuple[float, ...]) -> tuple[float, float, float]:
    if len(spacing) != 3:
        raise ValueError("spacing must contain z, y, x values")
    return (float(spacing[0]), float(spacing[1]), float(spacing[2]))


def _report(*, status: str, confidence: str, evidence: str, output_root: Path, flags: list[str], structure_assignments: dict[str, int], threshold_observations: list[str], confounders: list[str]) -> dict[str, Any]:
    recommended_action = "pause" if confidence == "low" else "flag" if confidence == "medium" else "proceed"
    return {
        "stage": "segmentation",
        "status": status,
        "confidence": confidence,
        "evidence": evidence,
        "recommended_action": recommended_action,
        "artifacts": {
            "labels": str(output_root / "labels.nii.gz"),
            "structure_assignments": str(output_root / "structure_assignments.json"),
            "seeds": str(output_root / "seeds.json"),
            "screenshots": [screenshot_path("segmentation", 1)],
        },
        "structure_assignments": structure_assignments,
        "threshold_observations": threshold_observations,
        "confounders": confounders,
        "flags": flags,
    }


def _failure_report(output_root: Path, evidence: str) -> dict[str, Any]:
    _write_json(output_root / "structure_assignments.json", {"status": "failed", "evidence": evidence})
    return _report(status="failed", confidence="low", evidence=evidence, output_root=output_root, flags=["segmentation-failed"], structure_assignments={}, threshold_observations=[], confounders=[])


def _evidence(confidence: str, threshold_observations: list[str], confounders: list[str], sanity_warnings: list[str]) -> str:
    if confidence == "high":
        return "Segmentation completed; thresholds, structure assignments, and sanity checks agree."
    parts = ["Segmentation completed with observations."]
    parts.extend(threshold_observations)
    parts.extend(confounders)
    parts.extend(sanity_warnings)
    return " ".join(parts)


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_jsonable(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _jsonable(value: Any) -> Any:
    if dataclasses.is_dataclass(value):
        return {field.name: _jsonable(getattr(value, field.name)) for field in dataclasses.fields(value)}
    if isinstance(value, dict):
        return {str(key): _jsonable(val) for key, val in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    return value
