"""Measurement reporting — JSON, markdown, and QC evidence packaging."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from .models import MeasurementResult


def results_to_json(results: list[MeasurementResult], workflow_id: str, session_id: str) -> dict[str, Any]:
    """Package measurement results as structured JSON."""

    return {
        "workflow_id": workflow_id,
        "session_id": session_id,
        "results": [
            {
                "name": result.name,
                "value": result.value,
                "unit": result.unit,
                "kind": result.spec.kind,
                "domain": result.spec.domain,
                "method": result.inputs.get("method") or result.spec.algorithm,
                "spec": asdict(result.spec),
                "inputs": result.inputs,
                "qc_evidence": result.qc_evidence,
            }
            for result in results
        ],
    }


def results_to_markdown(results: list[MeasurementResult]) -> str:
    """Format measurement results as a markdown summary table with provenance."""

    lines = [
        "| Measurement | Value | Unit | Method | Inputs | Formula |",
        "| --- | ---: | --- | --- | --- | --- |",
    ]
    lines.extend(
        (
            f"| {result.name} | {result.value:.6g} | {result.unit} | "
            f"{_method(result)} | {_input_refs(result)} | {_formula(result)} |"
        )
        for result in results
    )
    return "\n".join(lines) + "\n"


def _method(result: MeasurementResult) -> str:
    return str(result.inputs.get("method") or result.spec.algorithm or result.spec.kind)


def _input_refs(result: MeasurementResult) -> str:
    if result.inputs.get("slice_count") is not None:
        return (
            f"boundaries: {_mapping_keys(result.inputs.get('boundaries'))}; "
            f"slice_count: {result.inputs['slice_count']}"
        )
    if result.spec.roi:
        return f"roi: {result.spec.roi}"
    if result.inputs.get("points") is not None:
        return f"landmarks: {_mapping_keys(result.inputs['points'])}"
    if result.inputs.get("boundaries") is not None:
        return f"boundaries: {_mapping_keys(result.inputs['boundaries'])}"
    if result.spec.numerator and result.spec.denominator:
        return f"components: {result.spec.numerator}, {result.spec.denominator}"
    return "—"


def _mapping_keys(value: Any) -> str:
    if isinstance(value, dict):
        return ", ".join(str(key) for key in value)
    if isinstance(value, list):
        return ", ".join(str(item) for item in value)
    return str(value)


def _formula(result: MeasurementResult) -> str:
    if result.spec.numerator and result.spec.denominator:
        return f"{result.spec.numerator} / {result.spec.denominator}"
    if result.inputs.get("slice_count") is not None:
        return f"{result.inputs['slice_count']} slices × {result.inputs.get('slice_thickness')} mm"
    return result.spec.kind


def build_qc_payload(results: list[MeasurementResult]) -> dict[str, Any]:
    """Build QC evidence payload mapping each result to its measurement location."""

    return {
        "qc_overlays": [
            {
                "measurement": result.name,
                "evidence": result.qc_evidence,
                "inputs": result.inputs,
                "frame": result.spec.frame,
                "projection": result.spec.projection,
                "roi": result.spec.roi,
                "domain": result.spec.domain,
                "method": result.inputs.get("method") or result.spec.algorithm,
                "slice_count": result.inputs.get("slice_count"),
                "exact_multiple": result.inputs.get("exact_multiple"),
            }
            for result in results
        ]
    }
