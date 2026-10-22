# Run in Docker

This guide shows how to run the agent inside a Docker container instead of
directly on your machine. The agent's terminal commands then run in the
container, while the project files stay in a normal folder on your disk.

> **Experimental.** Docker execution works and is tested, but isn't yet proven in real use, and may change between minor versions. See [Experimental features](../README.md#experimental-features).

## What you need

- Docker, installed and running (`docker ps` works).
- The `sandbox` extra:

  ```bash
  uv tool install "certo[sandbox]"      # or: pip install "certo[sandbox]"
  ```

- The Certo agent image, `certo/agent-server:local`. See the next section.

## Build the image (once)

The image adds Certo's own tools to the published OpenHands agent-server
image. Certo builds it the first time you use Docker mode, but it needs the
Dockerfile and source from a checkout of the repository. **From a
`pip install`, the automatic build fails**, so build it once from a
checkout:

```bash
git clone https://github.com/alessioricco/certo.git
cd certo
docker build -f docker/agent-server.Dockerfile -t certo/agent-server:local .
```

Once the image exists, Certo uses it and doesn't rebuild it. To use an
image with another name, set `CERTO_DOCKER_IMAGE`.

**After upgrading Certo, rebuild the image.** It holds a copy of Certo's
tool code, and an old image keeps the old code. Remove it
(`docker rmi certo/agent-server:local`) and build again.

## Run a task

```bash
certo "Add a /version endpoint" --project my-api --execution docker
```

Or set `CERTO_EXECUTION=docker` to make it the default.

- The task's folder is mounted in the container at `/workspace`. Files the
  agent writes appear in the same folder on your disk as with local runs.
- Certo's checks run inside the container too, with the same tools and the
  same Python environment (`/workspace/.venv`) as the agent.
- The container is removed when the run ends, whether it succeeded or not.

## Things to know

- **Toolchains.** Only what the image contains is available. The agent can
  install packages inside the container during a run. Java builds can't be
  verified with the standard image: it has no Maven or Gradle.
- **Python environments don't move between the container and your
  machine.** A `.venv` created in the container doesn't work on macOS or
  Windows, and the other way round. When you later run the same project
  locally, Certo rebuilds a `.venv` it created itself.
- **Platform.** Certo picks `linux/arm64` on Apple Silicon and ARM
  machines, `linux/amd64` otherwise. Set `CERTO_DOCKER_PLATFORM` only if
  you must; the wrong platform runs under emulation, which is slow or
  fails.
- **Automatic model selection** makes its first choice, but can't switch to
  the next model in the middle of a Docker run.

## If it doesn't work

| Symptom | Fix |
|---|---|
| `CERTO_EXECUTION=docker requires the 'sandbox' extra` | Install `certo[sandbox]`. |
| The image build fails right away | You installed from pip. Build the image from a checkout, as above. |
| Hangs, or never becomes healthy | Check that Docker is running (`docker ps`) and that `CERTO_DOCKER_PLATFORM` is empty or matches your machine. |
| A custom tool works locally but not in Docker | See [Add custom tools](add-custom-tools.md#write-a-tool). |

## Related

- [Safety](../concepts/safety.md)
- [Configuration](../reference/configuration.md)
