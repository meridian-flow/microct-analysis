"""DICOM loading for micro-CT scan directories."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import numpy as np
import pydicom
from pydicom.dataset import FileDataset

from microct_analysis.processing.types import ScanVolume


class LoadError(Exception):
    """Raised when a DICOM directory cannot be loaded as a scan volume."""


def load_dicom(path: Path) -> ScanVolume:
    """Load all ``.dcm`` files from a directory as a float32 z/y/x volume."""

    scan_dir = Path(path)
    if not scan_dir.is_dir():
        raise LoadError(f"DICOM path is not a directory: {scan_dir}")

    files = sorted(scan_dir.glob("*.dcm"))
    if not files:
        raise LoadError(f"No .dcm files found in directory: {scan_dir}")

    try:
        datasets = [pydicom.dcmread(file) for file in files]
    except Exception as exc:  # pragma: no cover - pydicom exception types vary by input
        raise LoadError(f"Failed to read DICOM files from {scan_dir}: {exc}") from exc

    try:
        ordered = sorted(datasets, key=_slice_sort_key)
        data = np.stack([_pixel_array(ds).astype(np.float32, copy=False) for ds in ordered], axis=0)
        spacing = _spacing(ordered)
        affine = _affine(ordered, spacing)
    except Exception as exc:
        raise LoadError(f"Failed to build DICOM volume from {scan_dir}: {exc}") from exc

    return ScanVolume(data=data, spacing=spacing, affine=affine, provenance=_provenance(ordered))


def _pixel_array(dataset: FileDataset) -> np.ndarray:
    slope = float(getattr(dataset, "RescaleSlope", 1.0))
    intercept = float(getattr(dataset, "RescaleIntercept", 0.0))
    return dataset.pixel_array.astype(np.float32) * slope + intercept


def _slice_sort_key(dataset: FileDataset) -> tuple[int, float, str]:
    instance = getattr(dataset, "InstanceNumber", None)
    instance_key = int(instance) if instance is not None else 0
    position = getattr(dataset, "ImagePositionPatient", None)
    position_key = float(position[2]) if position is not None and len(position) >= 3 else 0.0
    uid_key = str(getattr(dataset, "SOPInstanceUID", ""))
    return (instance_key, position_key, uid_key)


def _spacing(datasets: list[FileDataset]) -> tuple[float, float, float]:
    first = datasets[0]
    pixel_spacing = getattr(first, "PixelSpacing", None)
    if pixel_spacing is None or len(pixel_spacing) < 2:
        raise LoadError("DICOM metadata missing PixelSpacing")

    y_spacing = float(pixel_spacing[0])
    x_spacing = float(pixel_spacing[1])
    return (_slice_spacing(datasets), y_spacing, x_spacing)


def _slice_spacing(datasets: list[FileDataset]) -> float:
    if len(datasets) > 1:
        positions = [getattr(ds, "ImagePositionPatient", None) for ds in datasets]
        if all(position is not None and len(position) >= 3 for position in positions):
            valid_positions = cast(list[list[float] | tuple[float, float, float]], positions)
            deltas = np.diff([float(position[2]) for position in valid_positions])
            nonzero = np.abs(deltas[np.nonzero(deltas)])
            if nonzero.size:
                return float(np.median(nonzero))

    first = datasets[0]
    for attr in ("SpacingBetweenSlices", "SliceThickness"):
        value = getattr(first, attr, None)
        if value is not None:
            return float(value)
    raise LoadError("DICOM metadata missing slice spacing")


def _affine(datasets: list[FileDataset], spacing: tuple[float, float, float]) -> np.ndarray:
    z_spacing, y_spacing, x_spacing = spacing
    affine = np.eye(4, dtype=np.float64)
    affine[0, 0] = x_spacing
    affine[1, 1] = y_spacing
    affine[2, 2] = z_spacing

    origin = getattr(datasets[0], "ImagePositionPatient", None)
    if origin is not None and len(origin) >= 3:
        affine[:3, 3] = [float(origin[0]), float(origin[1]), float(origin[2])]
    return affine


def _provenance(datasets: list[FileDataset]) -> dict[str, Any]:
    first = datasets[0]
    return {
        "manufacturer": str(getattr(first, "Manufacturer", "")),
        "model": str(getattr(first, "ManufacturerModelName", "")),
        "acquisition_date": str(getattr(first, "AcquisitionDate", "")),
        "slice_count": len(datasets),
    }
