# Hangman in the terminal

Build a Hangman game for the terminal in Python, using only the standard
library. People play it with `python hangman.py`.

## How it plays

- The secret word is the one given with `--word WORD`, in lower case.
  Without `--word`, the game picks one at random from a list of at least
  ten English words inside the program. A `--word` that isn't only
  letters `a` to `z` (any case) is refused: print an error to standard
  error and exit with code 2, before the game starts.
- The player may make 6 wrong guesses.
- At the start and after every guess, print two lines, each a whole
  line of its own with nothing before it (no prompt such as `Guess: `
  on the same line):
  - `Word: ` and the word with each letter not yet guessed shown as `_`,
    the letters separated by single spaces, such as `Word: _ a _ _ m a _`;
  - `Misses left: ` and the number of wrong guesses the player has left.
- Then read one line from standard input:
  - one letter is a guess, in any case. A letter already guessed is
    pointed out and costs nothing;
  - anything else (an empty line, several characters, a digit) is
    refused with a short message and costs nothing.
- When every letter is guessed, print `You win! The word was WORD.` with
  the word in lower case, and exit with code 0. After the sixth wrong
  guess, print `You lose! The word was WORD.` and exit with code 0.
- When the input ends before the game is over (Ctrl-D, or input piped
  from a file), print `Bye.` and exit with code 0, without a traceback.
