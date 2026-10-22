# Add custom tools

A custom tool gives the agent a new action, written in Python. For new
instructions rather than new actions, use a skill: see
[Manage skills](manage-skills.md).

## Write a tool

Certo's own `run_tests` tool is one. Adding a tool means changing
Certo's source, so work from a checkout of the repository (see
[CONTRIBUTING.md](../../CONTRIBUTING.md)).

Each tool follows the OpenHands SDK pattern of an *Action* (the input), an
*Observation* (the result) and an *Executor* (the code that does the work).
Start from the template, `src/certo/custom_tools/example_tool.py`:

1. Create `src/certo/custom_tools/<name>_tool.py` with an `Action`, an
   `Observation`, a `ToolExecutor`, and a `ToolDefinition` subclass with a
   `create(cls, conv_state, **params)` method. Call
   `register_tool(YourTool.name, YourTool)` at the top level of the module,
   so importing the module registers the tool.
2. Add the tool in `build_tools()` in `src/certo/tools.py`, so the agent
   gets it in local runs.
3. Import the module in `src/certo/custom_tools/__init__.py`, so it is also
   registered in Docker runs. Then rebuild the Docker image.
4. Add `tests/custom_tools/test_<name>_tool.py`: build an `Action`, call the
   executor directly, and check the `Observation`. No model, no network.

Why step 3: in Docker mode the agent runs in a separate process inside the
container. That process only knows the tools it imports when it starts,
and the image starts it with `--import-modules certo.custom_tools`. A tool
that works locally but not in Docker is almost always missing from
`__init__.py`, or the image wasn't rebuilt.

The SDK's own guide: [Custom tools](https://docs.openhands.dev/sdk/guides/custom-tools).

## Related

- [Manage skills](manage-skills.md)
- [Work on an existing project](work-on-an-existing-project.md)
