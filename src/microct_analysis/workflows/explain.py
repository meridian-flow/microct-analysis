"""Explain-then-apply protocol enforcement."""

from __future__ import annotations

from dataclasses import dataclass
from textwrap import dedent
from typing import Any

@dataclass(frozen=True)
class ExplanationRecord:
    """Record of an explanation before a domain operation."""

    what_changed: str
    why: str
    domain_context: dict[str, Any]

    def to_text(self) -> str:
        """Return a plain-language explanation suitable for notebook output."""
        return f"What will change: {self.what_changed}\nWhy: {self.why}"


def explain_correction(operation_type: str, parameters: dict[str, Any], before_state: dict[str, Any], after_state: dict[str, Any]) -> ExplanationRecord:
    """Generate a plain-language explanation for a domain correction."""
    if operation_type in {"adjust_threshold", "threshold_adjustment"}:
        old_value = _number(before_state.get("threshold", parameters.get("old_value", 0.0)))
        new_value = _number(after_state.get("threshold", parameters.get("new_value", old_value)))
        return explain_threshold_change(old_value, new_value, str(parameters.get("reason", "the visual review suggested it")))
    if operation_type in {"reassign_component", "component_reassignment"}:
        return explain_assignment_change(
            str(parameters.get("component_id", after_state.get("component_id", "selected component"))),
            _optional_str(before_state.get("label", parameters.get("old_label"))),
            str(after_state.get("label", parameters.get("new_label", "unassigned"))),
        )
    if operation_type in {"landmark_decision", "add_landmark", "remove_landmark"}:
        return explain_landmark_decision(
            str(parameters.get("landmark_name", after_state.get("landmark_name", "landmark"))),
            bool(after_state.get("accepted", parameters.get("accepted", True))),
            str(parameters.get("reason", "the landmark review supported this decision")),
        )
    return ExplanationRecord(
        what_changed=str(parameters.get("summary", f"Apply {operation_type.replace('_', ' ')}.")),
        why=str(parameters.get("reason", "This correction follows the current review finding.")),
        domain_context={"operation_type": operation_type, "parameters": parameters, "before_state": before_state, "after_state": after_state},
    )


def explain_threshold_change(old_value: float, new_value: float, reason: str) -> ExplanationRecord:
    """Explain a threshold parameter adjustment."""
    direction = "raise" if new_value > old_value else "lower" if new_value < old_value else "keep"
    what_changed = f"The threshold will {direction} from {old_value:g} to {new_value:g}."
    effect = {
        "raise": "This usually removes faint noise and soft-tissue fragments.",
        "lower": "This usually includes fainter bone that may have been clipped or missing.",
        "keep": "The numeric threshold is unchanged; only the review record will be updated.",
    }[direction]
    payload = {
        "action": "threshold-adjustment",
        "summary": what_changed,
        "rationale": (reason, effect),
        "details": {"old_value": old_value, "new_value": new_value, "direction": direction},
    }
    return ExplanationRecord(what_changed, f"{reason} {effect}", {"explanation_payload": payload})


def explain_assignment_change(component_id: str, old_label: str | None, new_label: str) -> ExplanationRecord:
    """Explain a bone/structure assignment change."""
    if new_label == "unassigned":
        what_changed = f"Component {component_id} will be left unassigned."
        why = "It will not be used as a seed for a named bone unless it is selected again."
    elif old_label and old_label != new_label:
        what_changed = f"Component {component_id} will move from {old_label} to {new_label}."
        why = "One component can seed only one structure, so changing the label clears the earlier assignment."
    else:
        what_changed = f"Component {component_id} will be assigned to {new_label}."
        why = "This makes the selected component the seed for that structure in downstream labeling."
    return ExplanationRecord(
        what_changed,
        why,
        {"explanation_action": "component-reassignment", "component_id": component_id, "old_label": old_label, "new_label": new_label},
    )


def explain_landmark_decision(landmark_name: str, accepted: bool, reason: str) -> ExplanationRecord:
    """Explain a landmark accept/reject decision."""
    decision = "accepted" if accepted else "rejected"
    what_changed = f"The {landmark_name} landmark candidate will be {decision}."
    why = f"The candidate was {decision} because {reason}"
    payload = {
        "action": "landmark-decision",
        "summary": what_changed,
        "rationale": (reason,),
        "details": {"landmark_id": landmark_name, "landmark_name": landmark_name, "accepted": accepted},
    }
    return ExplanationRecord(what_changed, why, {"explanation_payload": payload})


def correction_code(explanation: ExplanationRecord, exec_code: str) -> str:
    """Wrap domain correction code with a user-visible explanation and notebook record."""
    text = explanation.to_text()
    prelude = dedent(
        f"""
        from IPython.display import Markdown, display

        explanation_text = {text!r}
        explanation_context = {explanation.domain_context!r}
        display(Markdown("### Correction explanation\\n" + explanation_text.replace("\\n", "\\n\\n")))
        print(explanation_text)
        correction_explanations = globals().setdefault('correction_explanations', [])
        correction_explanations.append({{'text': explanation_text, 'context': explanation_context}})
        """
    ).strip()
    return f"{prelude}\n\n{exec_code.strip()}"


def _number(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _optional_str(value: Any) -> str | None:
    return None if value is None else str(value)
