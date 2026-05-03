"""Domain event translation for seed curation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


BONE_PALETTE: dict[str, str] = {
    "1": "femur",
    "2": "tibia",
    "3": "patella",
    "4": "fibula",
    "5": "unassigned",
}
KNOWN_BONES = set(BONE_PALETTE.values())


@dataclass(frozen=True)
class SeedAssignmentOp:
    """A seed assignment operation translated from a workbench event."""

    component_index: int
    bone_label: str
    source_event_type: str


def translate_pick_event(event: dict[str, Any], active_bone: str) -> SeedAssignmentOp | None:
    """Translate a generic pick event into a seed assignment operation.

    Returns ``None`` if the event is not a pick on a known component.  The
    workbench owns the generic event contract, so this translator accepts the
    observed flat shape (``component_index`` on the event) plus common nested
    payload shapes without redefining the upstream event schema.
    """

    if _event_type(event) != "pick" or active_bone not in KNOWN_BONES:
        return None
    component_index = _component_index(event)
    if component_index is None:
        return None
    return SeedAssignmentOp(component_index=component_index, bone_label=active_bone, source_event_type="pick")


def translate_key_event(event: dict[str, Any]) -> str | None:
    """Translate a key event into a bone palette switch.

    Returns the new active bone label or ``None`` if not a palette key.
    Keys: 1=femur, 2=tibia, 3=patella, 4=fibula, 5=unassigned.
    """

    if _event_type(event) != "key":
        return None
    key = _first_string(event, ("key", "key_value", "value", "text"))
    if key is None:
        payload = event.get("payload")
        if isinstance(payload, dict):
            key = _first_string(payload, ("key", "key_value", "value", "text"))
    if key is None:
        return None
    return BONE_PALETTE.get(key.strip())


def translate_events(events: list[dict[str, Any]], active_bone: str = "femur") -> tuple[list[SeedAssignmentOp], str]:
    """Process a batch of events, returning operations and final active bone."""

    operations: list[SeedAssignmentOp] = []
    current_bone = active_bone if active_bone in KNOWN_BONES else "femur"
    for event in events:
        palette_bone = translate_key_event(event)
        if palette_bone is not None:
            current_bone = palette_bone
            continue
        operation = translate_pick_event(event, current_bone)
        if operation is not None:
            operations.append(operation)
    return operations, current_bone


def _event_type(event: dict[str, Any]) -> str | None:
    value = _first_string(event, ("type", "event_type", "name"))
    if value is None:
        return None
    normalized = value.lower().removeprefix("mouse_").removeprefix("keyboard_")
    if "pick" in normalized:
        return "pick"
    if normalized in {"key", "keypress", "key_press", "keyboard"} or "key" in normalized:
        return "key"
    return normalized


def _component_index(event: dict[str, Any]) -> int | None:
    for container in (event, event.get("payload"), event.get("data"), event.get("picked")):
        if not isinstance(container, dict):
            continue
        for key in ("component_index", "component", "component_id", "label", "actor_index"):
            if key in container:
                return _to_int(container[key])
        actor = container.get("actor")
        if isinstance(actor, dict):
            for key in ("component_index", "component", "component_id", "label"):
                if key in actor:
                    return _to_int(actor[key])
    return None


def _first_string(values: dict[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = values.get(key)
        if isinstance(value, str):
            return value
    return None


def _to_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
