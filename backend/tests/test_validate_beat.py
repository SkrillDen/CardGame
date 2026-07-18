"""Exhaustive tests for the beating rule across every trump context.

Spades are a closed domain ONLY while they are not the trump: a spade is beaten
only by a higher spade, and a spade never beats a non-spade. When spades ARE the
trump they behave as a normal trump suit — any spade beats any non-spade, and a
higher spade beats a lower one.
"""

from game.engine import validate_beat, can_beat_any
from game.models import Card

C = Card.from_str


# ---------------------------------------------------------------------------
# Same non-spade suit
# ---------------------------------------------------------------------------

def test_same_suit_higher_rank_beats():
    assert validate_beat(C("7H"), C("9H"), trump="D") is True


def test_same_suit_equal_rank_does_not_beat():
    assert validate_beat(C("7H"), C("7H"), trump="D") is False


def test_same_suit_lower_rank_does_not_beat():
    assert validate_beat(C("9H"), C("7H"), trump="D") is False


# ---------------------------------------------------------------------------
# Trump interactions (non-spade)
# ---------------------------------------------------------------------------

def test_trump_beats_non_trump():
    assert validate_beat(C("7H"), C("6D"), trump="D") is True


def test_non_trump_cannot_beat_trump():
    assert validate_beat(C("7D"), C("AH"), trump="D") is False


def test_trump_vs_trump_higher_rank_wins():
    assert validate_beat(C("7D"), C("9D"), trump="D") is True
    assert validate_beat(C("9D"), C("7D"), trump="D") is False


def test_different_non_trump_suits_do_not_beat():
    assert validate_beat(C("7H"), C("9C"), trump="D") is False


# ---------------------------------------------------------------------------
# Spade immunity — being beaten (trump = H, D, C, S)
# ---------------------------------------------------------------------------

def test_spade_beaten_only_by_higher_spade_when_trump_is_heart():
    assert validate_beat(C("7S"), C("9S"), trump="H") is True


def test_spade_not_beaten_by_trump_heart():
    assert validate_beat(C("7S"), C("AH"), trump="H") is False


def test_spade_not_beaten_by_higher_non_spade_non_trump():
    assert validate_beat(C("7S"), C("AC"), trump="H") is False


def test_spade_not_beaten_by_higher_diamond_when_diamonds_trump():
    assert validate_beat(C("7S"), C("AD"), trump="D") is False


def test_spade_not_beaten_by_higher_club_when_clubs_trump():
    assert validate_beat(C("7S"), C("AC"), trump="C") is False


def test_spade_vs_lower_spade_when_spades_trump_only_higher_wins():
    # All spades are trump here; only a higher trump-spade beats a lower one.
    assert validate_beat(C("7S"), C("9S"), trump="S") is True
    assert validate_beat(C("9S"), C("7S"), trump="S") is False


def test_spade_not_beaten_by_heart_when_spades_trump():
    assert validate_beat(C("7S"), C("AH"), trump="S") is False


# ---------------------------------------------------------------------------
# Spade immunity — doing the beating
# ---------------------------------------------------------------------------

def test_spade_cannot_beat_non_spade():
    assert validate_beat(C("7H"), C("AS"), trump="H") is False


def test_spade_beats_non_spade_when_spades_trump():
    # When trump = Spades, spades are a normal trump: any spade beats a
    # non-spade (the closed-domain restriction no longer applies).
    assert validate_beat(C("7H"), C("AS"), trump="S") is True
    assert validate_beat(C("AH"), C("6S"), trump="S") is True


def test_spade_cannot_beat_trump_card():
    assert validate_beat(C("7D"), C("AS"), trump="D") is False


# ---------------------------------------------------------------------------
# can_beat_any helper
# ---------------------------------------------------------------------------

def test_can_beat_any_none_top_just_needs_a_card():
    assert can_beat_any([C("7H")], None, "D") is True
    assert can_beat_any([], None, "D") is False


def test_can_beat_any_finds_a_winner():
    assert can_beat_any([C("6H"), C("9H")], C("7H"), "D") is True
    assert can_beat_any([C("6H")], C("7H"), "D") is False


def test_can_beat_any_spade_top_needs_spade():
    assert can_beat_any([C("AH"), C("9S")], C("7S"), "H") is True
    assert can_beat_any([C("AH")], C("7S"), "H") is False
