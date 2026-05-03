"""Segmentation stage driver — executed via ``jupyter-workbench exec --file``.

Runs threshold derivation, segmentation, structure identification, and artifact
emission for the analyst-owned workbench session.  Imports from ``mouse_ct`` are
limited to the public stage-driver surface defined by the package architecture.
"""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path
from types import ModuleType
from typing import Any

import numpy as np

from mouse_ct.io.calibration import analyze_histogram, derive_thresholds
from mouse_ct.io.output import write_metadata, write_nifti_labels
from mouse_ct.processing.markers import (
    FovPrefilterConfig,
    extract_components,
    fov_prefilter,
    heuristic_assign,
    paint_and_verify,
    propose_auto_seeds,
)
from mouse_ct.processing.preprocess import median_filter
from mouse_ct.processing.threshold import apply as apply_threshold
from mouse_ct.processing.watershed import prune_to_seed_cc, run as run_watershed
from mouse_ct.types import LoadedScan, Provenance, Thresholds
from mouse_ct.verify.sanity import check as sanity_check

from microct_analysis.domain.artifact_contracts import screenshot_path


CONFUNDER_LABELS = {
    "sesamoid": "Sesamoid bones near joints may be misidentified as additional structures.",
    "articular-bridging-suspected": "Osteophytes or bridging may connect adjacent bones.",
    "aged-fused-growth-plate": "Aged or fused growth plate may change expected morphology.",
    "eroded-intercondylar-notch": "Eroded intercondylar notch may alter structure boundaries.",
    "partial-bone-at-scan-boundary": "Partial bones at scan boundaries may bias assignments.",
}


def run_segmentation(
    volume: Any,
    spacing: tuple[float, ...],
    thresholds: dict[str, Any] | Thresholds | None,
    workflow_thresholds: dict[str, Any] | None,
    output_dir: str = "segmentation",
) -> dict[str, Any]:
    """Run segmentation pipeline and return a structured stage report.

    ``thresholds`` may contain scanner/profile values supplied by intake.  The
    driver derives histogram thresholds, compares them to workflow thresholds,
    executes marker extraction and structure identification, and routes
    ambiguous identity to ``needs-seeds`` rather than guessing.
    """

    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    spacing_zyx = _spacing_zyx(spacing)
    scan = _scan_from_inputs(volume, spacing_zyx, thresholds)
    workflow_thresholds = workflow_thresholds or {}

    flags: list[str] = []
    observations: list[str] = []
    try:
        derived, _histogram, derive_flags = _derive_or_fallback_thresholds(scan.volume, thresholds)
        flags.extend(derive_flags)
    except Exception as exc:  # noqa: BLE001 - stage report should capture failure.
        return _failure_report(output_root, f"threshold derivation failed: {exc}")

    threshold_observations = compare_thresholds(derived, workflow_thresholds)
    observations.extend(threshold_observations)
    if threshold_observations:
        flags.append("workflow-threshold-discrepancy")

    filtered = median_filter(scan.volume)
    mask, marker_binary = apply_threshold(filtered, derived)
    min_voxels = int(workflow_thresholds.get("min_marker_voxels", 500))
    cc_array, components, total_raw = extract_components(marker_binary, spacing_zyx, min_voxels)
    components, prefiltered = fov_prefilter(
        components,
        cc_array,
        marker_binary.shape,
        FovPrefilterConfig(
            enabled=bool(workflow_thresholds.get("fov_prefilter_enabled", True)),
            margin_voxels=int(workflow_thresholds.get("fov_prefilter_margin_voxels", 3)),
        ),
    )
    confounders = detect_confounders(components, prefiltered, marker_binary.shape)
    observations.extend(confounders)

    try:
        assignments = heuristic_assign(components, marker_binary.shape[0])
        marker_labeling = paint_and_verify(cc_array, assignments, spacing_zyx)
    except Exception as exc:  # noqa: BLE001 - mouse_ct raises LoadError for ambiguity.
        reason = str(exc)
        flags.append(_flag_from_exception(exc))
        seeds = propose_auto_seeds(components, marker_binary.shape[0])
        _write_json(output_root / "seeds.json", _jsonable(seeds))
        _write_json(output_root / "structure_assignments.json", {"status": "needs-seeds", "reason": reason})
        write_metadata(
            output_root / "metadata.json",
            scan,
            None,
            flags + confounders,
            status="needs-seeds",
            components=components,
            prefiltered=prefiltered,
            total_raw_components=total_raw,
        )
        return _report(
            status="needs-seeds",
            confidence="low",
            evidence=f"Structure identification ambiguous; seed curation required. {reason}",
            output_root=output_root,
            flags=flags,
            structure_assignments={},
            threshold_observations=threshold_observations,
            confounders=confounders,
        )

    bone_labels = run_watershed(filtered, marker_labeling.labeled_markers, mask, spacing_zyx)
    bone_labels, pruning_stats, pruning_flags = prune_to_seed_cc(
        bone_labels,
        marker_labeling.labeled_markers,
        spacing_zyx,
    )
    flags.extend(pruning_flags)
    sanity_warnings = sanity_check(bone_labels, scan)
    flags.extend(sanity_warnings)
    observations.extend(sanity_warnings)

    label_path = output_root / "labels.nii.gz"
    write_nifti_labels(label_path, bone_labels.volume, scan)
    assignment_payload = {
        "status": "ready",
        "assignments": marker_labeling.bone_assignments,
        "per_bone": {name: _jsonable(stats) for name, stats in bone_labels.per_bone.items()},
        "flags": flags + confounders,
    }
    _write_json(output_root / "structure_assignments.json", assignment_payload)
    write_metadata(
        output_root / "metadata.json",
        scan,
        bone_labels,
        flags + confounders,
        status="ready",
        components=components,
        prefiltered=prefiltered,
        total_raw_components=total_raw,
        pruning_stats=pruning_stats,
    )

    confidence = confidence_for_segmentation(
        threshold_observations=threshold_observations,
        confounders=confounders,
        sanity_warnings=sanity_warnings,
    )
    evidence = _evidence(confidence, threshold_observations, confounders, sanity_warnings)
    return _report(
        status="ready",
        confidence=confidence,
        evidence=evidence,
        output_root=output_root,
        flags=flags,
        structure_assignments=marker_labeling.bone_assignments,
        threshold_observations=threshold_observations,
        confounders=confounders,
    )


def compare_thresholds(derived: Thresholds, workflow_thresholds: dict[str, Any]) -> list[str]:
    """Return discrepancy notes comparing derived and workflow thresholds."""

    observations: list[str] = []
    tolerance = float(workflow_thresholds.get("tolerance_fraction", 0.15))
    for field in ("mask", "marker"):
        expected = _threshold_value(workflow_thresholds, field)
        if expected is None:
            continue
        actual = float(getattr(derived, field))
        denominator = max(abs(float(expected)), 1.0)
        delta_fraction = abs(actual - float(expected)) / denominator
        if delta_fraction > tolerance:
            observations.append(
                f"{field} threshold derived {actual:.3g} differs from workflow {float(expected):.3g} "
                f"by {delta_fraction:.1%} (> {tolerance:.0%})."
            )
    return observations


def detect_confounders(components: list[Any], prefiltered: list[Any], shape: tuple[int, int, int]) -> list[str]:
    """Detect known segmentation confounder signals from component geometry."""

    observations: list[str] = []
    if prefiltered:
        observations.append("Partial bones at scan boundaries may bias assignments.")

    for component in components:
        edge_faces = set(getattr(component, "edge_faces", ()))
        if edge_faces:
            observations.append("Partial bones at scan boundaries may bias assignments.")
            break

    if len(components) > 4:
        observations.append("Sesamoid bones near joints may be misidentified as additional structures.")

    z_extent = shape[0]
    for component in components:
        (zmin, zmax), _, _ = component.bbox_zyx
        span = zmax - zmin
        if span > z_extent / 2 and zmin < z_extent / 3 and zmax > 2 * z_extent / 3:
            observations.append("Osteophytes or bridging may connect adjacent bones.")
            break

    return list(dict.fromkeys(observations))


def confidence_for_segmentation(
    *,
    threshold_observations: list[str],
    confounders: list[str],
    sanity_warnings: list[str],
) -> str:
    """Build segmentation confidence from threshold agreement and assignment quality."""

    if any("articular" in warning or "ambiguous" in warning for warning in sanity_warnings):
        return "low"
    if sanity_warnings or threshold_observations or confounders:
        return "medium"
    return "high"


def _derive_or_fallback_thresholds(volume: np.ndarray, thresholds: dict[str, Any] | Thresholds | None) -> tuple[Thresholds, Any, list[str]]:
    profile = _profile_from_thresholds(thresholds)
    if profile is not None:
        return derive_thresholds(volume, profile)
    manual = _thresholds_from_input(thresholds)
    if manual is None:
        raise ValueError("no threshold profile or explicit mask/marker thresholds supplied")
    return manual, analyze_histogram(volume), ["manual-thresholds-used"]


def _scan_from_inputs(volume: Any, spacing: tuple[float, float, float], thresholds: dict[str, Any] | Thresholds | None) -> LoadedScan:
    array = np.asarray(volume, dtype=np.float32)
    threshold_obj = _thresholds_from_input(thresholds) or Thresholds(mask=0.0, marker=0.0, method="pending")
    provenance = Provenance(
        source_dir="workbench-session",
        n_slices=int(array.shape[0]),
        original_spacing=spacing,
        resampled_spacing=None,
        slice_uid_hash="unknown",
        pipeline_version="microct-analysis-stage-driver",
        command="jupyter-workbench exec --file segmentation.py",
        manufacturer_raw="unknown",
        model_raw="unknown",
        transfer_syntax_uid="unknown",
    )
    return LoadedScan(
        volume=array,
        spacing=spacing,
        affine=np.eye(4),
        scanner="workflow",
        manufacturer_raw="unknown",
        model_raw="unknown",
        thresholds=threshold_obj,
        provenance=provenance,
        flags=[],
    )


def _profile_from_thresholds(thresholds: dict[str, Any] | Thresholds | None) -> ModuleType | None:
    if isinstance(thresholds, dict):
        profile = thresholds.get("profile")
        if isinstance(profile, ModuleType):
            return profile
    return None


def _thresholds_from_input(thresholds: dict[str, Any] | Thresholds | None) -> Thresholds | None:
    if isinstance(thresholds, Thresholds):
        return thresholds
    if not isinstance(thresholds, dict):
        return None
    mask = _threshold_value(thresholds, "mask")
    marker = _threshold_value(thresholds, "marker")
    if mask is None or marker is None:
        return None
    return Thresholds(mask=float(mask), marker=float(marker), method=str(thresholds.get("method", "workflow")))


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


def _flag_from_exception(exc: Exception) -> str:
    flag = getattr(exc, "flag", None)
    if isinstance(flag, str):
        return flag
    text = str(exc)
    for known in ("ambiguous-bone-identity", "articular-bridging-suspected"):
        if known in text:
            return known
    return "segmentation-structure-identification-failed"


def _report(
    *,
    status: str,
    confidence: str,
    evidence: str,
    output_root: Path,
    flags: list[str],
    structure_assignments: dict[str, int],
    threshold_observations: list[str],
    confounders: list[str],
) -> dict[str, Any]:
    screenshot = screenshot_path("segmentation", 1)
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
            "screenshots": [screenshot],
        },
        "structure_assignments": structure_assignments,
        "threshold_observations": threshold_observations,
        "confounders": confounders,
        "flags": flags,
    }


def _failure_report(output_root: Path, evidence: str) -> dict[str, Any]:
    _write_json(output_root / "structure_assignments.json", {"status": "failed", "evidence": evidence})
    return _report(
        status="failed",
        confidence="low",
        evidence=evidence,
        output_root=output_root,
        flags=["segmentation-failed"],
        structure_assignments={},
        threshold_observations=[],
        confounders=[],
    )


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
    path.write_text(json.dumps(_jsonable(payload), indent=2, sort_keys=True))


def _jsonable(value: Any) -> Any:
    if dataclasses.is_dataclass(value):
        payload = dataclasses.asdict(value)  # type: ignore[arg-type]
        return {key: _jsonable(val) for key, val in payload.items()}
    if isinstance(value, dict):
        return {str(key): _jsonable(val) for key, val in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    return value
