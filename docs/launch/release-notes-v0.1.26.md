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
See [Troubleshooting](../troubleshooting.md#the-run-ends-at-once-with-a-tool-call-as-the-agents-last-message).

## Fixed: a benchmark run that fails keeps its usage

A `certo bench` run that ends with an error, for example when the model
server goes away, now records the tokens, cost and condensations it
used up to the error, instead of zeros, whatever the arm's strategy;
an escalation counts every model it tried. Thanks to @bfs2021 (#30,
#36, #37, #38).

