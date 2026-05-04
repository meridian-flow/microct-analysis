from __future__ import annotations

import pytest

from microct_analysis.domain.seed_curation import SeedState, apply_workbench_events


def test_seed_state_requires_femur_and_tibia_by_default() -> None:
    state = SeedState()

    assert not state.is_valid()
    assert state.missing_bones() == {"femur", "tibia"}

    state.assign(1, "femur")
    assert not state.is_valid()
    assert state.missing_bones() == {"tibia"}

    state.assign(2, "tibia")
    assert state.is_valid()
    assert state.missing_bones() == set()


def test_assigning_same_bone_clears_previous_component() -> None:
    state = SeedState()

    state.assign(1, "femur")
    state.assign(3, "femur")

    assert state.assignments == {3: "femur"}


def test_unassigned_removes_component_assignment() -> None:
    state = SeedState(assignments={1: "femur", 2: "tibia"})

    state.assign(1, "unassigned")

    assert state.assignments == {2: "tibia"}
    assert not state.is_valid()


def test_to_seeds_dict_exports_durable_artifact_shape() -> None:
    state = SeedState(assignments={2: "tibia", 1: "femur"})

    assert state.to_seeds_dict() == {
        "schema_version": 1,
        "assignments": {
            "femur": {"component_index": 1},
            "tibia": {"component_index": 2},
        },
        "required_bones": ["femur", "tibia"],
        "missing_bones": [],
        "status": "ready",
    }


def test_from_seed_dict_round_trips_exported_state() -> None:
    payload = {
        "schema_version": 1,
        "assignments": {"femur": {"component_index": 4}, "tibia": {"component_index": 8}},
        "required_bones": ["femur", "tibia"],
    }

    state = SeedState.from_seed_dict(payload)

    assert state.assignments == {4: "femur", 8: "tibia"}
    assert state.is_valid()


def test_seed_state_rejects_unknown_bone_and_negative_component() -> None:
    state = SeedState()

    with pytest.raises(ValueError, match="unknown bone label"):
        state.assign(1, "talus")
    with pytest.raises(ValueError, match="component_index"):
        state.assign(-1, "femur")


def test_workbench_events_assign_stable_segmentation_component_labels() -> None:
    state = SeedState()

    updated, active_bone, operations = apply_workbench_events(
        state,
        [
            {"type": "pick", "payload": {"component_index": 7}},
            {"type": "key", "key": "2"},
            {"type": "pick", "payload": {"component_id": 8}},
        ],
    )

    assert active_bone == "tibia"
    assert [(op.component_index, op.bone_label) for op in operations] == [(7, "femur"), (8, "tibia")]
    assert updated.assignments == {7: "femur", 8: "tibia"}
    assert updated.to_seeds_dict()["status"] == "ready"
