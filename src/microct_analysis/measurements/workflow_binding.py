"""Compile workflow measurement definitions into typed specs."""

from __future__ import annotations

from typing import Any

from microct_analysis.workflows.schema import extract_measurements

from .models import MeasurementSpec

_ALLOWED_KINDS = {
    "distance",
    "surface_distance",
    "slice_distance",
    "frontal_projected_width",
    "ratio",
    "slice_count",
    "boundary_slice_count",
    "volume",
    "roi_stat",
}
_ALLOWED_DOMAINS = {"femoral_3d_surface", "tibial_2d_slice", "derived", "trabecular_roi"}


def compile_measurement_specs(workflow: dict[str, Any]) -> list[MeasurementSpec]:
    """Compile the measurements section of a workflow into typed MeasurementSpec objects."""

    specs: list[MeasurementSpec] = []
    for item in extract_measurements(workflow):
        name = _required_str(item, "name")
        kind = _required_str(item, "kind")
        if kind not in _ALLOWED_KINDS:
            raise ValueError(f"unsupported measurement kind for {name}: {kind}")
        specs.append(
            MeasurementSpec(
                name=name,
                kind=kind,
                domain=_optional_domain(item),
                frame=_optional_str(item, "frame"),
                projection=_optional_str(item, "projection"),
                points=_optional_str_list(item, "points"),
                boundaries=_optional_str_list(item, "boundaries"),
                slice_selection=_optional_str(item, "slice_selection"),
                slice_thickness_mm=_optional_float(item, "slice_thickness_mm"),
                numerator=_optional_str(item, "numerator"),
                denominator=_optional_str(item, "denominator"),
                roi=_optional_str(item, "roi"),
                algorithm=_optional_str(item, "algorithm"),
                unit=str(item.get("unit", "mm")),
                acceptance=item.get("acceptance") if isinstance(item.get("acceptance"), dict) else None,
            )
        )
    return specs


def _required_str(item: dict[str, Any], field: str) -> str:
    value = item.get(field)
    if not isinstance(value, str) or not value:
        raise ValueError(f"measurement is missing required string field {field!r}")
    return value


def _optional_str(item: dict[str, Any], field: str) -> str | None:
    value = item.get(field)
    return str(value) if value is not None else None


def _optional_float(item: dict[str, Any], field: str) -> float | None:
    value = item.get(field)
    return float(value) if value is not None else None


def _optional_domain(item: dict[str, Any]) -> str | None:
    value = _optional_str(item, "domain")
    if value is not None and value not in _ALLOWED_DOMAINS:
        name = item.get("name", "<unknown>")
        raise ValueError(f"unsupported measurement domain for {name}: {value}")
    return value


def _optional_str_list(item: dict[str, Any], field: str) -> list[str] | None:
    value = item.get(field)
    if value is None:
        return None
    if not isinstance(value, list):
        raise ValueError(f"measurement field {field!r} must be a list")
    return [str(entry) for entry in value]
