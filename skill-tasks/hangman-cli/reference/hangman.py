"""Hangman in the terminal: the rules in HangmanGame, the input and
output in main()."""

import argparse
import random
import sys

WORDS = [
    "python",
    "garden",
    "rocket",
    "silver",
    "planet",
    "window",
    "orange",
    "bridge",
    "castle",
    "puzzle",
]
MAX_MISSES = 6


class HangmanGame:
    def __init__(self, word: str, max_misses: int = MAX_MISSES) -> None:
        self.word = word.lower()
        self.max_misses = max_misses
        self.guessed: set[str] = set()
        self.misses = 0

    def masked(self) -> str:
        return " ".join(c if c in self.guessed else "_" for c in self.word)

    @property
    def misses_left(self) -> int:
        return self.max_misses - self.misses

    def guess(self, text: str) -> str:
        """'invalid', 'repeat', 'hit' or 'miss'."""
        letter = text.strip().lower()
        if len(letter) != 1 or not ("a" <= letter <= "z"):
            return "invalid"
        if letter in self.guessed:
            return "repeat"
        self.guessed.add(letter)
        if letter in self.word:
            return "hit"
        self.misses += 1
        return "miss"

    @property
    def won(self) -> bool:
        return all(c in self.guessed for c in self.word)

    @property
    def lost(self) -> bool:
        return self.misses >= self.max_misses


def valid_word(word: str) -> bool:
    return bool(word) and all("a" <= c <= "z" for c in word.lower())


def main(argv=None, stdin=sys.stdin, out=sys.stdout) -> int:
    parser = argparse.ArgumentParser(description="Hangman in the terminal.")
    parser.add_argument("--word", help="the secret word")
    args = parser.parse_args(argv)
    if args.word is not None and not valid_word(args.word):
        print(f"error: --word must be letters a to z only, got {args.word!r}", file=sys.stderr)
        return 2
    game = HangmanGame(args.word or random.choice(WORDS))
    while True:
        print(f"Word: {game.masked()}", file=out)
        print(f"Misses left: {game.misses_left}", file=out)
        line = stdin.readline()
        if not line:
            print("Bye.", file=out)
            return 0
        result = game.guess(line)
        if result == "invalid":
            print("Please type one letter, a to z.", file=out)
        elif result == "repeat":
            print("You already guessed that letter.", file=out)
        if game.won:
            print(f"You win! The word was {game.word}.", file=out)
            return 0
        if game.lost:
            print(f"You lose! The word was {game.word}.", file=out)
            return 0


if __name__ == "__main__":
    sys.exit(main())
