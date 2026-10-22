"""What a run prints to the terminal.

The SDK's default console output prints, before the agent's first action,
the whole system prompt (about 500 lines), the whole first message with
the skills Certo adds (about 240 lines more) and its own INFO logs.
Measured on a first Wordle run, 2026-10-20: 2,949 lines in all, with
Certo's own lines lost among them. By default Certo shows one line for
the system prompt and one for the task, and leaves everything else (the
agent's actions, observations and messages, and Certo's follow-up
messages such as failing checks) to the SDK's visualizer, unchanged.
`CERTO_VERBOSE` / `--verbose` brings back the full output.
"""

from __future__ import annotations

import logging
import os

from openhands.sdk.conversation.visualizer import (
    ConversationVisualizerBase,
    DefaultConversationVisualizer,
)
from openhands.sdk.event import Event, MessageEvent, SystemPromptEvent
from openhands.sdk.event.conversation_error import ConversationErrorEvent

from .config import Config
from .escalation import handoff_task
from .model_catalog import task_title


class QuietVisualizer(DefaultConversationVisualizer):
    """The SDK's visualizer, with the system prompt and the first user
    message (the task, with the skills Certo added) shortened to a line
    each. Overrides only `on_event`, the visualizer's public hook."""

    def __init__(self) -> None:
        super().__init__()
        self._task_shown = False

    def on_event(self, event: Event) -> None:
        if isinstance(event, SystemPromptEvent):
            lines = len(event.visualize.plain.splitlines())
            print(f"System prompt: {lines} lines (--verbose shows it)", flush=True)
            return
        if isinstance(event, MessageEvent) and event.source == "user" and not self._task_shown:
            self._task_shown = True
            text = event.visualize.plain
            lines = len(text.splitlines())
            # An escalation rung after the first starts with Certo's note
            # about the previous model: show the task's own title.
            task = handoff_task(text)
            if task is not None:
                print(
                    f"Task: {task_title(task)} (with Certo's note about the previous model, "
                    f"{lines} lines with the skills; --verbose shows them)",
                    flush=True,
                )
                return
            print(
                f"Task: {task_title(text)} ({lines} lines with the skills; --verbose shows them)",
                flush=True,
            )
            return
        if isinstance(event, ConversationErrorEvent):
            # The SDK's visualizer has no block for it and logs a warning
            # instead; Certo prints the error itself (a failed rung's line,
            # or the run's error).
            return
        super().on_event(event)


def visualizer_for(cfg: Config) -> type[ConversationVisualizerBase] | ConversationVisualizerBase:
    """The visualizer to pass to `Conversation`: a fresh one per
    conversation, since it remembers whether the task was shown."""
    return DefaultConversationVisualizer if cfg.verbose else QuietVisualizer()


def quiet_sdk_logs(cfg: Config) -> None:
    """Hide the SDK's INFO logs ("Created new conversation", "Loaded 4
    tools", ...) unless the run is verbose or the user set the SDK's own
    LOG_LEVEL. Warnings and errors still show."""
    if cfg.verbose or os.environ.get("LOG_LEVEL"):
        return
    logging.getLogger("openhands").setLevel(logging.WARNING)
