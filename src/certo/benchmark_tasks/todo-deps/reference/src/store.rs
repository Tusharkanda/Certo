//! The list file: a `next N` line, then one task per line as
//! `id<TAB>done<TAB>waits<TAB>title`. The title comes last, so it may hold
//! tabs; it can't hold a line break, which the task rules out.

use std::collections::BTreeSet;
use std::fs;
use std::io::ErrorKind;
use std::path::Path;

use crate::board::{Board, Task};

pub fn load(path: &Path) -> Result<Board, String> {
    let text = match fs::read_to_string(path) {
        Ok(text) => text,
        Err(err) if err.kind() == ErrorKind::NotFound => return Ok(Board::new()),
        Err(err) => return Err(format!("can't read {}: {}", path.display(), err)),
    };
    let bad = |n: usize| format!("{} line {} is damaged", path.display(), n + 1);
    let mut lines = text.lines().enumerate();
    let mut board = Board::new();
    match lines.next() {
        None => return Ok(board),
        Some((n, first)) => {
            board.next_id = first
                .strip_prefix("next ")
                .and_then(|v| v.parse().ok())
                .ok_or_else(|| bad(n))?;
        }
    }
    for (n, line) in lines {
        let parts: Vec<&str> = line.splitn(4, '\t').collect();
        if parts.len() != 4 {
            return Err(bad(n));
        }
        let id: u32 = parts[0].parse().map_err(|_| bad(n))?;
        let done = match parts[1] {
            "0" => false,
            "1" => true,
            _ => return Err(bad(n)),
        };
        let mut after = BTreeSet::new();
        for wait in parts[2].split(',').filter(|w| !w.is_empty()) {
            after.insert(wait.parse().map_err(|_| bad(n))?);
        }
        board.tasks.insert(id, Task { title: parts[3].to_string(), done, after });
    }
    Ok(board)
}

pub fn save(path: &Path, board: &Board) -> Result<(), String> {
    let mut text = format!("next {}\n", board.next_id);
    for (id, task) in &board.tasks {
        let waits: Vec<String> = task.after.iter().map(|w| w.to_string()).collect();
        let done = if task.done { "1" } else { "0" };
        text.push_str(&format!("{}\t{}\t{}\t{}\n", id, done, waits.join(","), task.title));
    }
    // Through a temporary file, so a crash never leaves half a list.
    let tmp = path.with_extension("tmp");
    fs::write(&tmp, text).map_err(|err| format!("can't write {}: {}", tmp.display(), err))?;
    fs::rename(&tmp, path).map_err(|err| format!("can't write {}: {}", path.display(), err))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn a_title_with_tabs_survives() {
        let path = std::env::temp_dir().join(format!("todo-store-{}.txt", std::process::id()));
        let mut board = Board::new();
        board.add("a\tb | # \"c\" é", &[]).unwrap();
        board.add("d", &[1]).unwrap();
        save(&path, &board).unwrap();
        assert_eq!(load(&path).unwrap(), board);
        fs::remove_file(&path).unwrap();
    }
}
