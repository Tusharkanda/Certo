# Server mode has no authentication: let's design it

**Context.** `certo-server` runs tasks for anyone who can reach it, and a task gives the agent a terminal: shell access on the machine, as the user running the server. It listens on `127.0.0.1` by default, and the docs say to keep it there or put it behind your own gateway ([Safety](https://github.com/alessioricco/certo/blob/main/docs/concepts/safety.md#server-mode)). With `--host`, though, every endpoint is open, and a request can also override the model's `api_key` and `base_url`. I'd like to discuss a design here before anyone writes code.

**What done looks like** for this issue: an agreed design written in a comment, which then becomes a smaller implementation issue. Not code yet.

**Questions to answer.**
- **What to protect.** The endpoints in `create_app()` in `src/certo/server.py`: `POST /tasks`, `GET` and `DELETE /tasks/{task_id}`, `DELETE /tasks`, the WebSocket `/tasks/stream`, `GET /v1/models` and `POST /v1/chat/completions`. Should `/health` stay open?
- **How callers prove who they are.** Options I can see: a shared secret in a header (for example a new `CERTO_SERVER_API_KEY` setting), a bearer token that OpenAI-compatible clients already send for `/v1/chat/completions`, or leaving it to a reverse proxy and refusing to start on a non-local `--host` without one. Others are welcome.
- **The per-request `api_key` and `base_url` overrides.** Should an authenticated caller still be able to point the server at any URL?
- **WebSocket.** Browsers can't set custom headers on a WebSocket, so a header-only design may not work there.
- **Defaults.** What happens on `--host 0.0.0.0` with no secret set: a warning, or refusing to start?

**Where to start.**
- `src/certo/server.py`: `create_app()` (the routes), `main()` (the `--host` option).
- [Run as a server](https://github.com/alessioricco/certo/blob/main/docs/guides/run-as-a-server.md) and [Safety](https://github.com/alessioricco/certo/blob/main/docs/concepts/safety.md#server-mode).
- `tests/test_server.py`: how the server is tested with no model.

**How to check it.** For the design: a comment here that answers the questions above. For the later implementation: `uv run pytest -q` with the `server` extra (`uv pip install -e ".[dev,server]"`), no API key needed.

**Labels:** help wanted
