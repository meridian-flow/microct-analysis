"""Intake stage driver — executed via jupyter-workbench exec --file."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from microct_analysis.domain.artifact_contracts import IntakeArtifacts
from microct_analysis.processing.calibration import analyze_histogram, derive_thresholds
from microct_analysis.processing.dicom import LoadError, load_dicom
from microct_analysis.processing.types import ScanVolume

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


def _normalize_scanner(manufacturer: str) -> str:
    if "scanco" in manufacturer.lower():
        return "scanco"
    return "unknown"


def run_intake(dicom_path: str, output_dir: str = ".") -> dict[str, Any]:
    """Load and validate a DICOM scan, then write intake artifacts."""

    artifacts = IntakeArtifacts()
    root = Path(output_dir)
    (root / "intake").mkdir(parents=True, exist_ok=True)

    try:
        volume: ScanVolume = load_dicom(Path(dicom_path))
    except LoadError:
        raise

    provenance = dict(volume.provenance)
    provenance["command"] = f"intake {dicom_path} --output-dir {output_dir}"
    provenance["pipeline_version"] = PIPELINE_VERSION
    manufacturer = str(provenance.get("manufacturer") or "")
    scanner = _normalize_scanner(manufacturer)
    histogram = analyze_histogram(volume.data)
    thresholds = derive_thresholds(volume.data, scanner=scanner)
    threshold_flags = [] if scanner == "scanco" else ["unknown-scanner-profile"]

    metadata: dict[str, Any] = {
        "dicom_path": str(dicom_path),
        "spacing": _json_ready(volume.spacing),
        "original_spacing": _json_ready(list(volume.spacing)),
        "affine": _json_ready(volume.affine),
        "manufacturer": provenance.get("manufacturer", ""),
        "model": provenance.get("model", ""),
        "voxel_count": int(volume.data.size),
        "provenance": _json_ready(provenance),
        "scanner": scanner,
        "scanner_profile": scanner,
        "histogram": _json_ready(histogram),
        "threshold_analysis": _json_ready(histogram),
        "derived_thresholds": _json_ready(thresholds),
        "threshold_flags": threshold_flags,
        "scan_volume_contract": ScanVolume.__name__,
        "loaded_scan_contract": ScanVolume.__name__,
    }

    (root / artifacts.volume_metadata).write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    orientation_report = (
        "# Intake orientation report\n\n"
        "Loaded scan through local `microct_analysis.processing.dicom.load_dicom` and derived "
        "initial thresholds through local calibration helpers.\n\n"
        f"- DICOM input: `{dicom_path}`\n"
        f"- Spacing: `{metadata['spacing']}`\n"
        f"- Manufacturer: `{metadata['manufacturer']}`\n"
        f"- Model: `{metadata['model']}`\n"
        f"- Scanner profile: `{metadata['scanner_profile']}`\n"
        "- Resampling: deferred to Phase 2; no resampled volume is emitted by intake.\n"
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
