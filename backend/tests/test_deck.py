"""Deck construction and dealing invariants."""

import random

import pytest

from game.deck import (
    build_deck,
    choose_initial_trump,
    choose_weighted_trump,
    deal_hands,
    INITIAL_TRUMP_CANDIDATES,
)
from game.models import Card


def test_build_deck_has_36_unique_cards():
    deck = build_deck()
    assert len(deck) == 36
    codes = {c.code for c in deck}
    assert len(codes) == 36  # no duplicates


def test_deck_covers_all_ranks_and_suits():
    deck = build_deck()
    for suit in ("S", "H", "D", "C"):
        for rank in range(6, 15):
            assert Card(suit, rank) in deck


def test_deal_hands_counts_for_two_players(rng):
    hidden, main, opener = deal_hands(2, rng)
    total_dealt = sum(len(h) for h in hidden) + sum(len(m) for m in main) + 1
    assert total_dealt == 36
    # 2 hidden each
    assert all(len(h) == 2 for h in hidden)
    # main total = 36 - 2N - 1 = 31
    main_total = sum(len(m) for m in main)
    assert main_total == 36 - 4 - 1


def test_deal_hands_counts_for_five_players(rng):
    hidden, main, opener = deal_hands(5, rng)
    assert all(len(h) == 2 for h in hidden)
    main_total = sum(len(m) for m in main)
    # 36 - 10 hidden - 1 opener = 25
    assert main_total == 25
    # No card dealt twice.
    seen = {opener.code}
    for h in hidden:
        for c in h:
            assert c.code not in seen
            seen.add(c.code)
    for m in main:
        for c in m:
            assert c.code not in seen
            seen.add(c.code)
    assert len(seen) == 36


@pytest.mark.parametrize("n", [2, 3, 4])
def test_deal_hands_equal_material_per_player(n):
    """Every player should be dealt the same total amount of material. Player 0
    auto-plays the opening card, so it is taken from their own hand — otherwise
    seat 0 ended up with extra cards (2 more than seat 1 in a 2-player game)."""
    hidden, main, opener = deal_hands(n, random.Random(5))
    # Material = hidden + main, plus the opener which came from player 0's hand.
    material = [len(hidden[i]) + len(main[i]) + (1 if i == 0 else 0) for i in range(n)]
    assert len(set(material)) == 1, f"unequal deal: {material}"


def test_deal_hands_opener_not_duplicated_in_hands():
    hidden, main, opener = deal_hands(2, random.Random(3))
    all_hand_codes = {c.code for h in hidden for c in h} | {c.code for m in main for c in m}
    assert opener.code not in all_hand_codes


def test_deal_hands_is_deterministic_with_seeded_rng():
    h1, m1, o1 = deal_hands(3, random.Random(99))
    h2, m2, o2 = deal_hands(3, random.Random(99))
    assert o1.code == o2.code
    assert [[c.code for c in h] for h in h1] == [[c.code for c in h] for h in h2]
    assert [[c.code for c in x] for x in m1] == [[c.code for c in x] for x in m2]


def test_deal_hands_rejects_bad_player_count():
    with pytest.raises(ValueError):
        deal_hands(1, random.Random())
    with pytest.raises(ValueError):
        deal_hands(6, random.Random())


def test_initial_trump_never_spades_over_many_draws():
    rng = random.Random(7)
    for _ in range(200):
        assert choose_initial_trump(rng) in INITIAL_TRUMP_CANDIDATES
        assert choose_initial_trump(rng) != "S"


def test_weighted_trump_returns_suit_present_in_pile():
    pile = [Card.from_str(c) for c in ["7H", "9H", "6D"]]
    rng = random.Random(1)
    for _ in range(50):
        trump = choose_weighted_trump(pile, rng)
        assert trump in ("H", "D")


def test_weighted_trump_weighted_by_count():
    # 10 hearts, 1 diamond -> H should dominate.
    pile = [Card.from_str("7H")] * 10 + [Card.from_str("6D")]
    rng = random.Random(0)
    draws = [choose_weighted_trump(pile, rng) for _ in range(400)]
    hearts = draws.count("H")
    assert hearts > 350  # ~97.5% expected


def test_weighted_trump_empty_pile_falls_back():
    trump = choose_weighted_trump([], random.Random(0))
    assert trump in INITIAL_TRUMP_CANDIDATES
