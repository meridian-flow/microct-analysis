"""Intake stage driver — executed via jupyter-workbench exec --file.

Loads DICOM data, validates, orients, and records metadata. This file runs
inside the jupyter-workbench kernel, so it may import from the mouse_ct public
surface and microct_analysis helpers.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from mouse_ct.io.calibration import analyze_histogram, derive_thresholds
from mouse_ct.io.dicom_load import LoadError, load
from mouse_ct.io.resample import to_isotropic
from mouse_ct.profiles import detect
from mouse_ct.types import LoadedScan

from microct_analysis.domain.artifact_contracts import IntakeArtifacts

PIPELINE_VERSION = "microct-analysis-intake-v1"


def _json_ready(value: Any) -> Any:
    """Convert common dataclass, array, and scalar objects to JSON values."""

    if hasattr(value, "__dataclass_fields__"):
        return {field: _json_ready(getattr(value, field)) for field in value.__dataclass_fields__}
    if hasattr(value, "tolist"):
        return value.tolist()
    if isinstance(value, dict):
        return {str(key): _json_ready(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_ready(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def run_intake(dicom_path: str, output_dir: str = ".") -> dict[str, Any]:
    """Load, validate, and orient a DICOM scan.

    Args:
        dicom_path: Path to DICOM directory or file.
        output_dir: Where to write intake artifacts.

    Returns:
        Volume metadata dict with spacing, affine, provenance, scanner profile,
        and initial threshold observations.
    """

    artifacts = IntakeArtifacts()
    root = Path(output_dir)
    intake_dir = root / "intake"
    intake_dir.mkdir(parents=True, exist_ok=True)

    command = f"intake {dicom_path} --output-dir {output_dir}"
    try:
        volume, spacing, affine, provenance, manufacturer, model = load(
            Path(dicom_path),
            command=command,
            pipeline_version=PIPELINE_VERSION,
        )
    except LoadError:
        raise

    profile = detect(manufacturer, model)
    resampled_volume, resampled_spacing = to_isotropic(volume, spacing)
    histogram = analyze_histogram(resampled_volume)
    thresholds, threshold_analysis, threshold_flags = derive_thresholds(resampled_volume, profile)

    # The architecture's public surface includes LoadedScan as the future stable
    # domain type. Current mouse-ct returns tuple fields, so this annotation keeps
    # the stage driver aligned with the public contract without depending on
    # internal implementation objects.
    loaded_scan_contract: type[LoadedScan] = LoadedScan

    metadata: dict[str, Any] = {
        "dicom_path": str(dicom_path),
        "spacing": _json_ready(resampled_spacing),
        "original_spacing": _json_ready(spacing),
        "affine": _json_ready(affine),
        "manufacturer": manufacturer,
        "model": model,
        "voxel_count": int(resampled_volume.size),
        "provenance": _json_ready(provenance),
        "scanner_profile": getattr(profile, "KEY", str(profile)),
        "histogram": _json_ready(histogram),
        "derived_thresholds": _json_ready(thresholds),
        "threshold_analysis": _json_ready(threshold_analysis),
        "threshold_flags": _json_ready(threshold_flags),
        "loaded_scan_contract": loaded_scan_contract.__name__,
    }

    metadata_path = root / artifacts.volume_metadata
    metadata_path.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    orientation_report = (
        "# Intake orientation report\n\n"
        "Loaded scan through `mouse_ct.io.dicom_load.load`, detected scanner profile, "
        "and resampled to isotropic spacing with `mouse_ct.io.resample.to_isotropic`.\n\n"
        f"- DICOM input: `{dicom_path}`\n"
        f"- Original spacing: `{metadata['original_spacing']}`\n"
        f"- Resampled spacing: `{metadata['spacing']}`\n"
        f"- Manufacturer: `{manufacturer}`\n"
        f"- Model: `{model}`\n"
    )
    (root / artifacts.orientation_report).write_text(orientation_report, encoding="utf-8")

    return metadata


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run microCT intake stage")
    parser.add_argument("dicom_path")
    parser.add_argument("--output-dir", default=".")
    args = parser.parse_args()
    print(json.dumps(run_intake(args.dicom_path, args.output_dir), indent=2, sort_keys=True))
