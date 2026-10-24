# Certo v0.1.24

Not released yet.

## Changed: Certo doesn't start while OpenHands plugins would load

OpenHands, the agent toolkit under Certo, loads plugins into every run on
its own: from your user folders (`~/.agents/plugins/`,
`~/.openhands/plugins/`) and, for a project Certo generates, from a git
repository around it. A plugin can add skills, tools and hooks that
Certo hasn't checked. Now Certo looks before a run, and before
`certo bench`, and doesn't start when it finds one, naming each plugin
and its folder. A project's own plugins, and a repository's plugins when
you run Certo on an existing folder, are still fine. See
[OpenHands plugins](../guides/manage-skills.md#openhands-plugins).
