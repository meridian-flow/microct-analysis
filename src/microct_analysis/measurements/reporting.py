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
                "spec": asdict(result.spec),
                "inputs": result.inputs,
                "qc_evidence": result.qc_evidence,
            }
            for result in results
        ],
    }


def results_to_markdown(results: list[MeasurementResult]) -> str:
    """Format measurement results as a markdown summary table."""

    lines = ["| Measurement | Value | Unit |", "| --- | ---: | --- |"]
    lines.extend(f"| {result.name} | {result.value:.6g} | {result.unit} |" for result in results)
    return "\n".join(lines) + "\n"


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
            }
            for result in results
        ]
    }
