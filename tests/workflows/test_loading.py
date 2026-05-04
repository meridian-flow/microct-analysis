from __future__ import annotations

from pathlib import Path

import pytest

from microct_analysis.workflows.loading import find_workflow, load_workflow, validate_workflow
from microct_analysis.workflows.schema import extract_landmarks, parse_frontmatter


VALID_FRONTMATTER = """---
workflow_id: mouse-knee
study_type: oa
thresholds:
  bone: 220
landmarks:
  - name: growth_plate
roi_definitions:
  - name: tibial_roi
measurements:
  - name: distance
orientation_protocol:
  axes: anatomical
acceptance_checks:
  segmentation:
    - name: labels
sources:
  - paper
---
# Body
"""


def test_parse_frontmatter_extracts_yaml_and_body() -> None:
    frontmatter, body = parse_frontmatter(VALID_FRONTMATTER)
    assert frontmatter["workflow_id"] == "mouse-knee"
    assert frontmatter["thresholds"] == {"bone": 220}
    assert body == "# Body\n"


def test_parse_frontmatter_rejects_missing_frontmatter() -> None:
    with pytest.raises(ValueError):
        parse_frontmatter("# Body only\n")


def test_validate_workflow_catches_missing_required_fields() -> None:
    assert validate_workflow({"workflow_id": "only-id"}) == [
        "thresholds",
        "landmarks",
        "roi_definitions",
        "measurements",
        "orientation_protocol",
        "acceptance_checks",
        "sources",
    ]


def test_find_workflow_matches_by_workflow_id(tmp_path: Path) -> None:
    workflow_dir = tmp_path / "workflows" / "mouse-knee-dir"
    workflow_dir.mkdir(parents=True)
    workflow_path = workflow_dir / "workflow.md"
    workflow_path.write_text(VALID_FRONTMATTER, encoding="utf-8")

    assert find_workflow("mouse-knee", tmp_path / "workflows") == workflow_path
    assert load_workflow(workflow_path)["study_type"] == "oa"


def test_loading_accepts_current_landmark_domain_schema() -> None:
    workflow, _body = parse_frontmatter(
        """---
workflow_id: mouse-knee
thresholds: {bone: 220}
landmarks:
  - id: intercondylar_groove_midpoint
    structure: femur
    domain: femoral_3d_surface
    geometric_method: saddle_point
  - id: growth_plate_proximal
    structure: tibia
    domain: tibial_2d_slice
    geometric_method: slice_boundary
roi_definitions: [{name: tibial_roi}]
measurements: [{name: width, kind: distance}]
orientation_protocol: {target_plane: frontal}
acceptance_checks: {landmarks: []}
sources: [{citation: fixture}]
---
# Body
"""
    )

    landmarks = extract_landmarks(workflow)

    assert [item["domain"] for item in landmarks] == ["femoral_3d_surface", "tibial_2d_slice"]
