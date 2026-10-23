//! The tasks and their waits, with every rule a command checks.

use std::collections::{BTreeMap, BTreeSet};

#[derive(Debug, Clone, PartialEq)]
pub struct Task {
    pub title: String,
    pub done: bool,
    pub after: BTreeSet<u32>,
}

#[derive(Debug, Clone, PartialEq, Default)]
pub struct Board {
    /// The id the next added task gets; ids are never reused.
    pub next_id: u32,
    pub tasks: BTreeMap<u32, Task>,
}

fn ids(list: &[u32]) -> String {
    list.iter().map(|id| id.to_string()).collect::<Vec<_>>().join(", ")
}

impl Board {
    pub fn new() -> Board {
        Board { next_id: 1, tasks: BTreeMap::new() }
    }

    fn get(&self, id: u32) -> Result<&Task, String> {
        self.tasks.get(&id).ok_or_else(|| format!("no task {}", id))
    }

    /// The open tasks `id` still waits for, ascending.
    pub fn open_waits(&self, id: u32) -> Vec<u32> {
        let task = &self.tasks[&id];
        task.after.iter().copied().filter(|w| !self.tasks[w].done).collect()
    }

    pub fn add(&mut self, title: &str, after: &[u32]) -> Result<u32, String> {
        for &other in after {
            self.get(other)?;
        }
        let id = self.next_id;
        self.next_id += 1;
        let after = after.iter().copied().collect();
        self.tasks.insert(id, Task { title: title.to_string(), done: false, after });
        Ok(id)
    }

    pub fn done(&mut self, id: u32) -> Result<(), String> {
        if self.get(id)?.done {
            return Err(format!("task {} is already done", id));
        }
        let open = self.open_waits(id);
        if !open.is_empty() {
            return Err(format!("task {} is blocked by {}", id, ids(&open)));
        }
        self.tasks.get_mut(&id).unwrap().done = true;
        Ok(())
    }

    /// True when `from` already waits for `target`, directly or through
    /// other tasks.
    fn waits_for(&self, from: u32, target: u32) -> bool {
        let mut stack = vec![from];
        let mut seen = BTreeSet::new();
        while let Some(id) = stack.pop() {
            if id == target {
                return true;
            }
            if seen.insert(id) {
                stack.extend(self.tasks[&id].after.iter().copied());
            }
        }
        false
    }

    pub fn block(&mut self, id: u32, other: u32) -> Result<(), String> {
        self.get(id)?;
        self.get(other)?;
        if self.waits_for(other, id) {
            return Err(format!("task {} would wait for itself", id));
        }
        self.tasks.get_mut(&id).unwrap().after.insert(other);
        Ok(())
    }

    pub fn remove(&mut self, id: u32, force: bool) -> Result<(), String> {
        self.get(id)?;
        let needed: Vec<u32> = self
            .tasks
            .iter()
            .filter(|(_, task)| task.after.contains(&id))
            .map(|(&other, _)| other)
            .collect();
        if !needed.is_empty() && !force {
            return Err(format!("task {} is needed by {}", id, ids(&needed)));
        }
        self.tasks.remove(&id);
        for task in self.tasks.values_mut() {
            task.after.remove(&id);
        }
        Ok(())
    }

    /// One line of `todo list`.
    pub fn line(&self, id: u32) -> String {
        let task = &self.tasks[&id];
        let mark = if task.done { "x" } else { " " };
        let mut line = format!("[{}] {} {}", mark, id, task.title);
        if !task.done {
            let open = self.open_waits(id);
            if !open.is_empty() {
                line.push_str(&format!(" (after {})", ids(&open)));
            }
        }
        line
    }

    pub fn next(&self) -> Option<u32> {
        self.tasks
            .iter()
            .find(|(&id, task)| !task.done && self.open_waits(id).is_empty())
            .map(|(&id, _)| id)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn ids_are_never_reused() {
        let mut board = Board::new();
        board.add("a", &[]).unwrap();
        board.remove(1, false).unwrap();
        assert_eq!(board.add("b", &[]), Ok(2));
    }

    #[test]
    fn done_needs_the_waits_done_first() {
        let mut board = Board::new();
        board.add("a", &[]).unwrap();
        board.add("b", &[]).unwrap();
        board.add("c", &[2, 1]).unwrap();
        assert_eq!(board.done(3), Err("task 3 is blocked by 1, 2".to_string()));
        board.done(1).unwrap();
        assert_eq!(board.line(3), "[ ] 3 c (after 2)");
        assert_eq!(board.next(), Some(2));
    }

    #[test]
    fn a_cycle_is_refused() {
        let mut board = Board::new();
        board.add("a", &[]).unwrap();
        board.add("b", &[1]).unwrap();
        assert_eq!(board.block(1, 2), Err("task 1 would wait for itself".to_string()));
        assert_eq!(board.block(1, 1), Err("task 1 would wait for itself".to_string()));
    }

    #[test]
    fn remove_refuses_a_needed_task_unless_forced() {
        let mut board = Board::new();
        board.add("a", &[]).unwrap();
        board.add("b", &[1]).unwrap();
        assert_eq!(board.remove(1, false), Err("task 1 is needed by 2".to_string()));
        board.remove(1, true).unwrap();
        assert!(board.tasks[&2].after.is_empty());
    }
}
