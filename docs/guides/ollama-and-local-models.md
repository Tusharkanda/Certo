# Ollama and local models

This guide shows how to run Certo with a model on your own computer, or on
another computer in your network, using [Ollama](https://ollama.com). It
covers choosing a model, memory, the context window, and reaching Ollama on
another machine. A local model costs nothing per run and sends no code to a
cloud provider.

## Choose a model

The agent needs a model that is good at code and supports tool calling.

| Model | Memory needed | Notes |
|---|---|---|
| `qwen3.8:27b` | about 20 GB of GPU or unified memory | The default in `certo init`. Passed 27 of 27 tasks in Certo's [0.1.18 benchmark](../benchmark/baseline-0.1.18-local.md). |
| `qwen2.5-coder:7b` | much less | For smaller machines. Never benchmarked by Certo; expect it to be weaker on multi-step tasks. |

```bash
ollama pull qwen3.8:27b
```

Small local models often struggle with long, multi-step tasks. Expect
weaker results than a large cloud model. Which models did best in Certo's
own benchmark, and how to test one on your setup:
[Choose a local model](choose-a-local-model.md).

## Set up

With `certo init`, choose **Ollama**. It asks for the server address
(default `http://localhost:11434`) and lists the models installed there,
with the recommended model preselected when it is installed. If the server can't be reached, or has no
models yet, it says so and prints the `ollama pull` command to run.

`certo init` also sets `CERTO_LLM_TIMEOUT_SECONDS=1200`, so a slow
answer has 20 minutes instead of the default 5 (see
[Slow answers and the call timeout](#slow-answers-and-the-call-timeout)).

By hand:

```bash
CERTO_LLM_MODEL=ollama/qwen3.8:27b
CERTO_LLM_BASE_URL=http://localhost:11434
CERTO_LLM_TIMEOUT_SECONDS=1200
```

No API key is needed when `CERTO_LLM_BASE_URL` is set. Then run
`certo check`. The first call can take a minute while Ollama loads the
model.

## Give the model a large enough context window

The context window is how much text the model can see at once. An agent
needs a lot: the task, the files it read, and the output of every command.

On a machine with less than 24 GB of GPU memory, Ollama's default context
window is 4096 tokens. That is too short for an agent. The model loses the
start of the task and starts to wander: it repeats steps, forgets what it
was asked, or stops with half the work done.

Start Ollama with a larger window:

```bash
OLLAMA_CONTEXT_LENGTH=32768 ollama serve
```

In the Ollama desktop app, move the context length slider in the settings
instead. `ollama ps` shows the context a loaded model got.

Certo also refuses a model whose context window is under 16,384 tokens, as
reported by LiteLLM, before any request is sent. See
[Troubleshooting](../troubleshooting.md#context-window-below-the-minimum).

## Make sure the model fits in memory

If a model is larger than your GPU or unified memory, Ollama runs part of
it on the CPU. It still works, but each step of the agent can take minutes
instead of seconds, and a task can run out of its time budget (30 minutes
by default).

Check with `ollama ps` while the model is loaded: the `PROCESSOR` column
should say `100% GPU`. If it shows a CPU share, pick a smaller model, or a
smaller quantization of the same model.

### Slow answers and the call timeout

One call to the model may take `CERTO_LLM_TIMEOUT_SECONDS`: 300 seconds
by default, and 1200 in the settings `certo init` writes for Ollama. A
call that takes longer fails and is tried again from the start, up to 5
more times, so a model that needs 400 seconds per answer never gets one
with the default, and spends the whole time budget trying. A model that
thinks at length, such as `qwen3.8:27b`, can need more than 300 seconds
for one answer once the task has grown. If you set Ollama up by hand,
raise the limit:

```bash
CERTO_LLM_TIMEOUT_SECONDS=1200
```

For one model, set `timeout_seconds: 1200` on it in `models_list.yaml`, or
as an override in your `models.yaml`. A longer
call timeout also makes the whole task longer, so you may need to raise
`CERTO_MAX_TASK_SECONDS` too.

## Use Ollama on another machine

Ollama listens only on its own machine by default. On the machine that runs
Ollama, start it so it accepts connections from the network:

```bash
OLLAMA_HOST=0.0.0.0 ollama serve
```

On the machine that runs Certo, point to it:

```bash
CERTO_LLM_MODEL=ollama/qwen3.8:27b
CERTO_LLM_BASE_URL=http://192.168.1.50:11434
```

Use the other machine's real address. If `certo check` says
`Couldn't reach the server`, check the address, that Ollama is running
there, and that no firewall blocks port 11434.

Anyone who can reach that port can use the model. Only do this on a
network you trust.

## Thinking (reasoning) with Ollama

Most Ollama models have no thinking mode, and Ollama rejects a request that
asks for one. So for `ollama/` models, Certo sends no reasoning setting
unless you ask for one. To turn thinking on for a model that has it (for
example `qwen3` or `deepseek-r1`):

```bash
CERTO_LLM_REASONING_EFFORT=high
```

If you set it for a model without a thinking mode, the first call fails
with `does not support thinking`. Clear the setting or set it to `none`.

## Other local servers

Servers such as vLLM or LM Studio work too, as long as LiteLLM supports
them. Set `CERTO_LLM_MODEL` to the LiteLLM id for that server and
`CERTO_LLM_BASE_URL` to its address. See LiteLLM's
[provider list](https://docs.litellm.ai/docs/providers).

## Related

- Every Ollama problem with its fix: [Troubleshooting](../troubleshooting.md)
- Every setting: [Configuration](../reference/configuration.md)
- [Choose a local model](choose-a-local-model.md): benchmark results and how to test a model
