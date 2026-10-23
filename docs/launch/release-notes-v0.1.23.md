# Certo v0.1.23

Not released yet.

## Removed: the old skill folders and `certo-admin skills`

As announced in 0.1.22, Certo no longer reads `./skills`
(`CERTO_SKILLS_DIR`) or `./third_party_skills/`
(`CERTO_THIRD_PARTY_SKILLS_DIR` and `CERTO_THIRD_PARTY_SKILLS_LOCK`),
and `certo-admin skills` is gone. Skills live in
`~/.config/certo/skills/` and `<project>/.certo/skills/`, managed with
`certo skills`.

If you still have skills in the old folders, add each one again with
`certo skills add PATH --global` (or `--project NAME`); see
[Moving from the old folders](../guides/manage-skills.md#moving-from-the-old-folders).
While one of the three settings is still set, Certo prints a warning
naming it.
