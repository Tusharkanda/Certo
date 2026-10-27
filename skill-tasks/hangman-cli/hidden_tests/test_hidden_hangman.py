"""Hangman, played as people play it: the program run with input piped in."""

import subprocess
import sys
from pathlib import Path

GAME = Path.cwd() / "hangman.py"


def play(*args, lines=(), timeout=20):
    text = "".join(f"{line}\n" for line in lines)
    return subprocess.run(
        [sys.executable, str(GAME), *args],
        input=text,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def word_lines(out):
    return [line.strip() for line in out.splitlines() if line.strip().startswith("Word:")]


def misses_lines(out):
    return [line.strip() for line in out.splitlines() if line.strip().startswith("Misses left:")]


def test_first_screen_shows_the_hidden_word_and_six_misses():
    result = play("--word", "banana")
    assert word_lines(result.stdout)[0] == "Word: _ _ _ _ _ _"
    assert misses_lines(result.stdout)[0] == "Misses left: 6"


def test_a_right_guess_shows_every_copy_of_the_letter():
    result = play("--word", "banana", lines=["a"])
    assert "Word: _ a _ a _ a" in word_lines(result.stdout)


def test_winning():
    result = play("--word", "banana", lines=["b", "a", "n"])
    assert result.returncode == 0
    assert "You win! The word was banana." in result.stdout


def test_guesses_ignore_case_and_the_word_is_shown_in_lower_case():
    result = play("--word", "BaNaNa", lines=["B", "A", "n"])
    assert "You win! The word was banana." in result.stdout


def test_losing_after_six_wrong_guesses():
    result = play("--word", "banana", lines=["c", "d", "e", "f", "g", "h"])
    assert result.returncode == 0
    assert "You lose! The word was banana." in result.stdout
    assert "Misses left: 1" in misses_lines(result.stdout)


def test_a_wrong_guess_costs_one_miss():
    result = play("--word", "banana", lines=["z"])
    assert misses_lines(result.stdout)[:2] == ["Misses left: 6", "Misses left: 5"]


def test_a_repeated_letter_costs_nothing():
    result = play("--word", "banana", lines=["z"] * 8)
    assert "You lose!" not in result.stdout
    assert misses_lines(result.stdout)[-1] == "Misses left: 5"


def test_invalid_input_costs_nothing():
    result = play("--word", "banana", lines=["", "ab", "7", "?"])
    assert "You lose!" not in result.stdout
    assert set(misses_lines(result.stdout)) == {"Misses left: 6"}


def test_end_of_input_says_bye_without_a_traceback():
    result = play("--word", "banana", lines=["a"])
    assert result.returncode == 0
    assert result.stdout.strip().endswith("Bye.")
    assert "Traceback" not in result.stderr


def test_no_input_at_all_says_bye():
    result = play("--word", "banana")
    assert result.returncode == 0
    assert "Bye." in result.stdout


def test_a_bad_word_is_refused_with_code_2():
    for bad in ("ban4na", "two words", "café"):
        result = play("--word", bad)
        assert result.returncode == 2, bad
        assert result.stderr.strip(), bad
        assert "Word:" not in result.stdout, bad


def test_without_word_a_random_word_is_playable():
    result = play()
    first = word_lines(result.stdout)[0]
    letters = first.removeprefix("Word:").split()
    assert len(letters) >= 1 and set(letters) == {"_"}
    assert "Bye." in result.stdout
