"""Seed curation state management."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


KNOWN_BONES = {"femur", "tibia", "patella", "fibula", "unassigned"}


@dataclass
class SeedState:
    """Mutable seed assignment state during curation."""

    assignments: dict[int, str] = field(default_factory=dict)
    required_bones: set[str] = field(default_factory=lambda: {"femur", "tibia"})

    def assign(self, component_index: int, bone_label: str) -> None:
        """Assign a component to a bone."""

        if bone_label not in KNOWN_BONES:
            raise ValueError(f"unknown bone label: {bone_label}")
        if component_index < 0:
            raise ValueError("component_index must be >= 0")
        if bone_label == "unassigned":
            self.assignments.pop(component_index, None)
            return
        for idx, label in list(self.assignments.items()):
            if label == bone_label and idx != component_index:
                del self.assignments[idx]
        self.assignments[component_index] = bone_label

    def is_valid(self) -> bool:
        """Check if all required bones have assignments."""

        assigned_bones = set(self.assignments.values())
        return self.required_bones.issubset(assigned_bones)

    def missing_bones(self) -> set[str]:
        """Return required bones that are not yet assigned."""

        return self.required_bones - set(self.assignments.values())

    def to_seeds_dict(self) -> dict[str, Any]:
        """Export as a durable seeds artifact dict."""

        return {
            "schema_version": 1,
            "assignments": {
                bone_label: {"component_index": component_index}
                for component_index, bone_label in sorted(self.assignments.items())
            },
            "required_bones": sorted(self.required_bones),
            "missing_bones": sorted(self.missing_bones()),
            "status": "ready" if self.is_valid() else "incomplete",
        }

    @classmethod
    def from_seed_dict(cls, payload: dict[str, Any]) -> SeedState:
        """Build curation state from a persisted seed artifact dict."""

        state = cls(required_bones=set(payload.get("required_bones", {"femur", "tibia"})))
        raw_assignments = payload.get("assignments", {})
        if not isinstance(raw_assignments, dict):
            return state
        for bone_label, value in raw_assignments.items():
            component_index = value.get("component_index") if isinstance(value, dict) else value
            if isinstance(bone_label, str) and component_index is not None:
                state.assign(int(component_index), bone_label)
        return state
