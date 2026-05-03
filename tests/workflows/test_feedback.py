from __future__ import annotations

from microct_analysis.workflows.feedback import translate_screenshot_feedback, translate_visual_feedback


def test_wrong_bone_feedback_reassigns_to_explicit_label() -> None:
    translation = translate_visual_feedback(
        "This is the wrong bone — that's the tibia.",
        current_stage="landmark-review",
        context={"component_id": "component-7", "old_label": "femur"},
    )

    assert translation.interpreted_intent == "The user is questioning a bone identity assignment."
    assert [operation.operation_type for operation in translation.domain_operations] == ["reassign_component"]
    assert translation.domain_operations[0].parameters == {
        "component_id": "component-7",
        "old_label": "femur",
        "new_label": "tibia",
    }


def test_wrong_bone_feedback_without_target_label_falls_back_to_inspection() -> None:
    translation = translate_visual_feedback(
        "This is the wrong bone.",
        current_stage="landmark-review",
        context={"component_id": "component-3", "region": "left condyle"},
    )

    assert [operation.operation_type for operation in translation.domain_operations] == ["inspect_region"]
    assert translation.domain_operations[0].parameters == {
        "stage": "landmark-review",
        "component_id": "component-3",
        "region": "left condyle",
    }


def test_wrong_bone_feedback_ignores_invalid_suggested_label_and_falls_back_to_inspection() -> None:
    translation = translate_visual_feedback(
        "That is the wrong bone.",
        current_stage="landmark-review",
        context={"component_id": "component-3", "suggested_label": "humerus", "region": "left condyle"},
    )

    assert [operation.operation_type for operation in translation.domain_operations] == ["inspect_region"]
    assert translation.domain_operations[0].parameters["component_id"] == "component-3"
    assert translation.domain_operations[0].parameters["region"] == "left condyle"


def test_missing_gap_feedback_lowers_threshold_and_inspects_region() -> None:
    translation = translate_visual_feedback(
        "There is a gap where bone should be.",
        current_stage="segmentation",
        context={"picked_region": "proximal tibia"},
    )

    assert [operation.operation_type for operation in translation.domain_operations] == ["adjust_threshold", "inspect_region"]
    assert translation.domain_operations[0].parameters == {"direction": "lower", "stage": "segmentation"}
    assert translation.domain_operations[1].parameters == {"region": "proximal tibia"}


def test_noise_feedback_raises_threshold() -> None:
    translation = translate_visual_feedback(
        "There is too much speck noise around the mask.",
        current_stage="segmentation",
        context={},
    )

    assert [operation.operation_type for operation in translation.domain_operations] == ["adjust_threshold"]
    assert translation.domain_operations[0].parameters == {"direction": "raise", "stage": "segmentation"}


def test_vague_directional_feedback_inspects_region() -> None:
    translation = translate_visual_feedback(
        "The left side looks wrong.",
        current_stage="segmentation",
        context={"region": "left cortex"},
    )

    assert [operation.operation_type for operation in translation.domain_operations] == ["inspect_region"]
    assert translation.domain_operations[0].parameters == {
        "stage": "segmentation",
        "region": "left cortex",
    }


def test_screenshot_feedback_prepends_screenshot_inspection() -> None:
    translation = translate_screenshot_feedback(
        screenshot_path="shots/review-1.png",
        user_comment="This area is too big and leaking into soft tissue.",
        current_stage="segmentation",
    )

    assert translation.interpreted_intent == "The user supplied a screenshot to point at a segmentation review concern."
    assert [operation.operation_type for operation in translation.domain_operations] == [
        "inspect_screenshot_annotation",
        "adjust_boundary",
        "inspect_region",
    ]
    assert translation.domain_operations[0].parameters == {
        "screenshot_path": "shots/review-1.png",
        "stage": "segmentation",
    }
    assert translation.domain_operations[1].parameters == {"direction": "shrink", "stage": "segmentation"}
    assert "domain steps" in translation.explanation
