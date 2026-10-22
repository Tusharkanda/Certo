# syntax=docker/dockerfile:1.7
#
# Wraps the published OpenHands agent-server image so our custom tools are
# importable and registered inside the container. register_tool() only
# affects the process that calls it; under CERTO_EXECUTION=docker the agent
# loop runs inside this container's own agent-server process, not the
# harness's local Python process, so the tool source has to ship with the
# image. Build from the repo root (src/certo/workspace.py does this
# automatically on first use):
#
#   docker build -f docker/agent-server.Dockerfile -t certo/agent-server:local .
#
# This same image is meant to generalize beyond local `docker run`: push it to
# a registry (e.g. ECR) and any compute backend that can run a container and
# reach it over HTTP (ECS, EC2, ...) can serve as a CERTO_EXECUTION backend
# later without changing this Dockerfile — only src/certo/workspace.py's
# dispatch needs a new branch.
ARG BASE_IMAGE=ghcr.io/openhands/agent-server:latest-python
FROM ${BASE_IMAGE}

COPY src/certo/__init__.py /certo_src/certo/__init__.py
COPY src/certo/project_env.py /certo_src/certo/project_env.py
COPY src/certo/verification.py /certo_src/certo/verification.py
COPY src/certo/custom_tools/ /certo_src/certo/custom_tools/

# Read by openhands.agent_server.__main__.extend_python_path(). A plain
# PYTHONPATH env var isn't enough — the entrypoint below is a PyInstaller
# binary that doesn't honor it; this is the SDK's documented mechanism for
# exactly that case.
ENV OH_EXTRA_PYTHON_PATH=/certo_src

ENTRYPOINT ["tini", "--", "/usr/local/bin/openhands-agent-server", "--import-modules", "certo.custom_tools"]
