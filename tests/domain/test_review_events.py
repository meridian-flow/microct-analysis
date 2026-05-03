from __future__ import annotations

from microct_analysis.domain.review_events import SeedAssignmentOp, translate_events, translate_key_event, translate_pick_event


def test_translate_key_event_maps_palette_keys() -> None:
    assert translate_key_event({"type": "key", "key": "1"}) == "femur"
    assert translate_key_event({"event_type": "keyboard", "payload": {"key": "5"}}) == "unassigned"
    assert translate_key_event({"type": "key", "key": "x"}) is None


def test_translate_pick_event_uses_active_bone_for_known_component() -> None:
    op = translate_pick_event({"type": "pick", "component_index": 3}, "tibia")

    assert op == SeedAssignmentOp(component_index=3, bone_label="tibia", source_event_type="pick")


def test_translate_pick_event_ignores_non_pick_or_unknown_component() -> None:
    assert translate_pick_event({"type": "key", "component_index": 3}, "tibia") is None
    assert translate_pick_event({"type": "pick"}, "tibia") is None
    assert translate_pick_event({"type": "pick", "component_index": 3}, "unknown") is None


def test_translate_pick_event_accepts_nested_payload_shape() -> None:
    op = translate_pick_event({"event_type": "mesh_pick", "payload": {"actor": {"component_id": "7"}}}, "patella")

    assert op == SeedAssignmentOp(component_index=7, bone_label="patella", source_event_type="pick")


def test_translate_events_tracks_palette_state() -> None:
    operations, active_bone = translate_events(
        [
            {"type": "pick", "component_index": 1},
            {"type": "key", "key": "2"},
            {"type": "pick", "payload": {"component_index": 4}},
            {"type": "key", "key": "5"},
            {"type": "pick", "component_index": 9},
        ]
    )

    assert operations == [
        SeedAssignmentOp(component_index=1, bone_label="femur", source_event_type="pick"),
        SeedAssignmentOp(component_index=4, bone_label="tibia", source_event_type="pick"),
        SeedAssignmentOp(component_index=9, bone_label="unassigned", source_event_type="pick"),
    ]
    assert active_bone == "unassigned"
