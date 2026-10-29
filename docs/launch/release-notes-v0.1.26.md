# Certo v0.1.26

Not released yet.

## New: a tool call written as text no longer ends the run

Some local models sometimes answer with a tool call written as text,
such as `{"command": "view", "path": "..."}`, instead of making the
call. The agent framework took that as the agent's final answer, so the
run ended there, often on its first step, with `inconclusive` or
`unchanged`. In Certo's saved benchmark runs, `qwen3.8:27b` did this in
22 of 151 runs and in 4 of 8 runs of the 60-minute budget benchmark;
no cloud model did it in 178 runs.

Certo now sees it, tells the agent to make the call, and lets it go on:

```
Certo: the agent wrote a tool call as text instead of making it, so nothing ran. Asking it to make the call (1 of 3).
```

`CERTO_TOOL_CALL_REMINDERS` sets how many times per run (default 3, counted per model on an
escalation ladder;
`0` turns it off), and a benchmark arm can set `tool_call_reminders` to
compare. A model that makes real tool calls is never sent a reminder.
Measured in [a benchmark](../benchmark/reminders-0.1.26.md): `claude-haiku-5-5`
got none and passed 13 of 13; `qwen3.8` made one real call after most
reminders, then went back to text, so the reminder didn't save its runs.
See [Troubleshooting](../troubleshooting.md#the-run-ends-at-once-with-a-tool-call-as-the-agents-last-message).

## Benchmark: the Ollama model's build is recorded

For each Ollama model, `meta.json` and the top of `results.md` now
record the digest of the model's build, next to the Ollama version and
the context window, so two benchmarks of the same model name can be told
apart when it was pulled again in between.

## New skill: testable interactive programs

When a task describes a game, a menu or another terminal program,
Certo's new `testable-interactive-apps` skill tells the agent to keep
the rules apart from input and output, to make randomness controllable,
and to test the rules and the whole program with its input piped in.
Without tests, Certo can't say such a program works: `qwen3.8` wrote a
working Hangman game in 3 of 3 runs, and none was `verified`, because it
wrote no tests. With the skill it wrote tests in 3 of 3 runs, and all 3
were `verified`, though one of them was wrong: its tests missed a rule.
Runs took about three times longer. `claude-haiku-5-5` already wrote
tests, so the skill changed little there. Measured in
[a benchmark](../benchmark/interactive-0.1.26.md). See
[Manage skills](../guides/manage-skills.md).

## Benchmark: arms without some of Certo's skills

A benchmark arm can list `skills_off`, Certo's own skills its runs
don't get, to measure what a skill changes next to an arm that has it.
See [the benchmark file reference](../reference/bench-yaml.md).

## Changed: old sections in `models_list.yaml` are no longer read

Since 0.1.20, task profiles and escalation ladders have their own files,
`task_profiles.yaml` and `escalation.yaml`. A `task_profiles:` or
`escalation:` section still in `models_list.yaml` was read with a
warning; now Certo stops and says where to move it. Nothing inside the
section changes. See
[Moving from one file](../reference/models-yaml.md#moving-from-one-file-0119-and-earlier).

## Fixed: a benchmark run that fails keeps its usage

A `certo bench` run that ends with an error, for example when the model
server goes away, now records the tokens, cost and condensations it
used up to the error, instead of zeros, whatever the arm's strategy;
an escalation counts every model it tried. Thanks to @bfs2021 (#30,
#36, #37, #38).

