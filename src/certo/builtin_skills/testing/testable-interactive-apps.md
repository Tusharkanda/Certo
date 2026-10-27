---
name: testable-interactive-apps
triggers:
  - interactive
  - game
  - menu
  - terminal
  - stdin
  - standard input
description: Keep a game's or menu's logic apart from its input and output, and test both. Triggered when a task describes an interactive or terminal program.
---

When the program is one people use interactively (a game, a menu, a
loop that reads commands), make it testable and test it, even when the
task doesn't ask for tests:

- Put the rules in functions that take values and return values (the
  new state, the text to show), with no input or printing inside. The
  loop around them only reads a line, calls them and prints the result.
- Make randomness controllable: an option or a parameter (a seed, a
  fixed word or board) lets a test know the outcome.
- Add tests with the project's test runner, where its test command finds
  them: the rules functions (win, lose, invalid input, repeated input),
  and the whole program run as a subprocess with its standard input
  given (in Python, `subprocess.run([...], input="a\nb\n",
  capture_output=True, text=True, timeout=10)`), checking the exact
  output lines and the exit code. Include input that ends early: the
  program must exit cleanly, without hanging or a traceback.
- Never start the program in the terminal without input: it waits
  forever. Pipe the input in (`printf 'a\nb\n' | <run command>`) or use a
  timeout.
- Run the project's test command before finishing.
