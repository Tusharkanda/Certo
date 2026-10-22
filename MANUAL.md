# The manual has moved

Certo's documentation now lives in [`docs/`](docs/README.md), as short
pages organised by what you want to do. Start at the
[documentation home](docs/README.md), or at
[Getting started](docs/getting-started.md) if you are new.

This table maps each section of the old manual to its new page.

| Old section | New page |
|---|---|
| Setup: From PyPI | [Getting started](docs/getting-started.md) |
| Setup: From a checkout (development) | [CONTRIBUTING.md](CONTRIBUTING.md) |
| Configuration reference | [Configuration](docs/reference/configuration.md) |
| Where settings come from | [Configuration: Where Certo looks](docs/reference/configuration.md#where-certo-looks) |
| CLI reference | [Commands](docs/reference/commands.md) |
| `certo verify [PATH]` | [Commands: certo verify](docs/reference/commands.md#certo-verify), [Verify in CI](docs/guides/verify-in-ci.md) |
| `certo init [FOLDER]` | [Commands: certo init](docs/reference/commands.md#certo-init), [Getting started](docs/getting-started.md) |
| `certo check` | [Commands: certo check](docs/reference/commands.md#certo-check), [Troubleshooting](docs/troubleshooting.md) |
| Before the agent edits an existing folder | [Work on an existing project](docs/guides/work-on-an-existing-project.md) |
| Task source resolution | [Commands: certo](docs/reference/commands.md#certo) |
| Interactive mode | [Interactive and confirm mode](docs/guides/interactive-mode.md) |
| Automatic model selection | [Pick models automatically](docs/guides/pick-models-automatically.md), [models.yaml and models_list.yaml](docs/reference/models-yaml.md) |
| Run artifacts | [Run records and costs](docs/guides/run-records-and-costs.md) |
| Server mode (HTTP/WebSocket) | [Run as a server](docs/guides/run-as-a-server.md), [Server API](docs/reference/server-api.md) |
| Task registry persistence, `certo-admin` | [Run as a server](docs/guides/run-as-a-server.md#keep-task-records), [Commands: certo-admin](docs/reference/commands.md#certo-admin) |
| Projects: one subfolder per generated project | [Commands: certo](docs/reference/commands.md#certo), [Safety](docs/concepts/safety.md#where-the-agent-may-work) |
| Project environments (Python) | [Work on an existing project](docs/guides/work-on-an-existing-project.md#python-projects-get-their-own-environment) |
| Skills, Third-party skills, Lifecycle skills, Per-project context | [Manage skills](docs/guides/manage-skills.md) |
| Execution modes | [Run in Docker](docs/guides/run-in-docker.md) |
| Switching LLM provider / model | [OpenAI, Claude and Gemini](docs/guides/openai-claude-gemini.md), [Ollama and local models](docs/guides/ollama-and-local-models.md) |
| Custom tools | [Add custom tools](docs/guides/add-custom-tools.md), [Verification by language](docs/reference/verification-by-language.md) |
| Test verification | [How verification works](docs/concepts/how-verification-works.md), [Verdicts](docs/reference/verdicts.md) |
| Confirmation mode | [Interactive and confirm mode](docs/guides/interactive-mode.md#confirm-mode-approve-every-action) |
| Task budget | [Safety: Budgets](docs/concepts/safety.md#budgets) |
| Acceptance checks | [Acceptance checks](docs/guides/acceptance-checks.md) |
| Testing, Release check | [CONTRIBUTING.md](CONTRIBUTING.md) |
| Known limitations | [Documentation home: Known limitations](docs/README.md#known-limitations) |
| Troubleshooting | [Troubleshooting](docs/troubleshooting.md) |

The stories behind the design, from the old "Test verification" section,
are in [Why agents lie](docs/concepts/why-agents-lie.md).
