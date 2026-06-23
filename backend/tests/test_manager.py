"""Manager integration tests covering room registry state."""

from game.manager import ConnectionManager


def test_dispatch_persists_started_room_for_followup_actions():
    manager = ConnectionManager()
    room_id = "r1"

    manager.create_room(room_id, "Alice")
    manager.join_room(room_id, "Bob")

    start_events = manager.dispatch(room_id, "p0", {"type": "start_game", "payload": {}})
    assert any(event["type"] == "game_started" for event in start_events)
    assert manager.get_room(room_id) is not None
    assert manager.get_room(room_id).started is True

    started_room = manager.get_room(room_id)
    current_player = started_room.current_player
    card = str(current_player.main_hand[0])

    play_events = manager.dispatch(
        room_id,
        current_player.id,
        {"type": "play_card", "payload": {"card": card}},
    )
    assert not any(
        event["type"] == "error" and event["payload"]["code"] == "not_started"
        for event in play_events
    )
