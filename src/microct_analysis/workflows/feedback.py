"""Non-technical user feedback translation to domain operations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class DomainOperation:
    """A concrete domain operation derived from user feedback."""

    operation_type: str
    parameters: dict[str, Any]
    explanation: str


@dataclass(frozen=True)
class FeedbackTranslation:
    """Translation of user feedback into domain operations."""

    original_feedback: str
    interpreted_intent: str
    domain_operations: list[DomainOperation]
    explanation: str


def translate_visual_feedback(feedback: str, current_stage: str, context: dict[str, Any]) -> FeedbackTranslation:
    """Translate non-technical visual feedback into concrete review operations."""
    normalized = feedback.strip().lower()
    if _mentions_wrong_bone(normalized):
        component_id = _context_value(context, "component_id", "selected_component_id")
        target_label = _valid_bone_label(
            _infer_bone_label(normalized) or _context_value(context, "suggested_label", "active_bone")
        )
        old_label = _context_value(context, "old_label", "current_label")
        if target_label is None:
            operations = [
                DomainOperation(
                    "inspect_region",
                    {
                        "stage": current_stage,
                        "component_id": component_id,
                        "region": _context_value(context, "region", "picked_region"),
                    },
                    "Inspect the selected component and ask the user which bone it should be before reassigning it.",
                )
            ]
        else:
            operations = [
                DomainOperation(
                    "reassign_component",
                    {"component_id": component_id, "old_label": old_label, "new_label": target_label},
                    f"Move the selected component from {old_label or 'its current label'} to {target_label}.",
                )
            ]
        intent = "The user is questioning a bone identity assignment."
    elif "missing" in normalized or "gap" in normalized or "hole" in normalized:
        operations = [
            DomainOperation("adjust_threshold", {"direction": "lower", "stage": current_stage}, "Lower the threshold or add the missing region so faint bone is included instead of excluded."),
            DomainOperation("inspect_region", {"region": _context_value(context, "region", "picked_region")}, "Inspect the marked area against the mask overlay before changing parameters."),
        ]
        intent = "The user sees bone or ROI content that should be included but is absent."
    elif "noise" in normalized or "speck" in normalized or "too much" in normalized:
        operations = [DomainOperation("adjust_threshold", {"direction": "raise", "stage": current_stage}, "Raise the threshold or filtering strength so small soft-tissue/noise fragments are removed.")]
        intent = "The user sees extra fragments that should not be part of the analysis."
    elif "too small" in normalized or "shrunk" in normalized or "clipped" in normalized:
        operations = [DomainOperation("adjust_boundary", {"direction": "expand", "stage": current_stage}, "Expand the segmented boundary or lower the threshold so more of the bone is included.")]
        intent = "The user thinks the segmented structure is under-sized or clipped."
    elif "too big" in normalized or "bleeding" in normalized or "leaking" in normalized:
        operations = [DomainOperation("adjust_boundary", {"direction": "shrink", "stage": current_stage}, "Tighten the segmented boundary or raise the threshold so adjacent tissue is excluded.")]
        intent = "The user thinks the segmented structure includes too much surrounding material."
    elif "left" in normalized or "right" in normalized or "this area" in normalized or "that looks wrong" in normalized:
        operations = [DomainOperation("inspect_region", {"stage": current_stage, "region": _context_value(context, "region", "picked_region")}, "Inspect the visible region, component summary, and QC flags before choosing a parameter change.")]
        intent = "The user is pointing to a visual problem without naming a parameter."
    else:
        operations = [DomainOperation("inspect_current_stage", {"stage": current_stage}, "Review the current artifacts, picks, and QC flags to identify the likely domain correction.")]
        intent = "The feedback is non-specific, so the next safe step is inspection before correction."
    return FeedbackTranslation(feedback, intent, operations, _translation_explanation(intent, operations))


def translate_screenshot_feedback(screenshot_path: str, user_comment: str, current_stage: str) -> FeedbackTranslation:
    """Translate screenshot-based feedback into operations for the agent to verify visually."""
    context: dict[str, Any] = {"screenshot_path": screenshot_path, "region": "annotated screenshot area"}
    translation = translate_visual_feedback(user_comment or "screenshot annotation", current_stage, context)
    operations: list[DomainOperation] = [
        DomainOperation("inspect_screenshot_annotation", {"screenshot_path": screenshot_path, "stage": current_stage}, "Compare the annotated screenshot area with the live scene and durable artifacts."),
        *translation.domain_operations,
    ]
    if not any(operation.operation_type == "inspect_region" for operation in operations):
        operations.append(
            DomainOperation(
                "inspect_region",
                {"region": "annotated screenshot area"},
                "Inspect the marked screenshot region against the live scene before applying the correction.",
            )
        )
    intent = f"The user supplied a screenshot to point at a {current_stage} review concern."
    return FeedbackTranslation(user_comment, intent, operations, _translation_explanation(intent, operations))


def _translation_explanation(intent: str, operations: list[DomainOperation]) -> str:
    actions = " ".join(operation.explanation for operation in operations)
    return f"I interpret this as: {intent} I will translate it into domain steps: {actions}"


def _context_value(context: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = context.get(key)
        if value is not None:
            return value
    return None


def _mentions_wrong_bone(feedback: str) -> bool:
    return "wrong bone" in feedback or "not the" in feedback or "that's the" in feedback or "that is the" in feedback


def _infer_bone_label(feedback: str) -> str | None:
    for bone in ("femur", "tibia", "patella", "fibula"):
        if bone in feedback:
            return bone
    return None


def _valid_bone_label(label: Any) -> str | None:
    if isinstance(label, str) and label.lower() in {"femur", "tibia", "patella", "fibula"}:
        return label.lower()
    return None
