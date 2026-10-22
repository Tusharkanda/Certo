# Certo v0.1.22

Not released yet.

## Changed: a run that ends after its time budget is still checked

Certo checks the time budget (`CERTO_MAX_TASK_SECONDS`, 30 minutes by
default) only between the agent's runs, so a slow model's last run can end
after it. Until now Certo then reported `budget_exhausted` without looking
at the work. In the 0.1.15 local benchmark, three runs ended that way
although their work passed the hidden tests.

Now the project's checks run once, with no fix attempt, because they need
no model. Work that passes is `verified`, with a note that the budget ran
out. Work that fails stays `budget_exhausted`, and the check results are
shown. A run that ended in an error, or with checks turned off, is
reported as before.
