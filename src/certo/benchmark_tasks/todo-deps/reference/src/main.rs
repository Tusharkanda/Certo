//! `todo`: a to-do list where a task can wait for other tasks.

mod board;
mod store;

use std::env;
use std::path::PathBuf;
use std::process;

use board::Board;

const USAGE: &str = "usage: todo add TITLE... [--after ID]... | done ID | block ID --after OTHER \
                     | remove ID [--force] | list | next";

enum Failure {
    /// Exit 2: the command line itself is wrong.
    Usage,
    /// Exit 1: a rule refused the command.
    Error(String),
}

fn id(text: Option<&String>) -> Result<u32, Failure> {
    match text.and_then(|t| t.parse::<u32>().ok()) {
        Some(id) if id > 0 => Ok(id),
        _ => Err(Failure::Usage),
    }
}

fn run(args: &[String], board: &mut Board) -> Result<(Vec<String>, bool), Failure> {
    let rule = Failure::Error;
    let (command, rest) = args.split_first().ok_or(Failure::Usage)?;
    match command.as_str() {
        "add" => {
            let mut words = Vec::new();
            let mut after = Vec::new();
            let mut i = 0;
            while i < rest.len() {
                if rest[i] == "--after" {
                    after.push(id(rest.get(i + 1))?);
                    i += 2;
                } else if rest[i].starts_with("--") {
                    return Err(Failure::Usage);
                } else {
                    words.push(rest[i].as_str());
                    i += 1;
                }
            }
            let title = words.join(" ");
            if title.trim().is_empty() {
                return Err(Failure::Usage);
            }
            let new = board.add(&title, &after).map_err(rule)?;
            Ok((vec![format!("added {}", new)], true))
        }
        "done" if rest.len() == 1 => {
            let task = id(rest.get(0))?;
            board.done(task).map_err(rule)?;
            Ok((vec![format!("done {}", task)], true))
        }
        "block" if rest.len() == 3 && rest[1] == "--after" => {
            let (task, other) = (id(rest.get(0))?, id(rest.get(2))?);
            board.block(task, other).map_err(rule)?;
            Ok((vec![format!("{} waits for {}", task, other)], true))
        }
        "remove" if rest.len() == 1 || (rest.len() == 2 && rest[1] == "--force") => {
            let task = id(rest.get(0))?;
            board.remove(task, rest.len() == 2).map_err(rule)?;
            Ok((vec![format!("removed {}", task)], true))
        }
        "list" if rest.is_empty() => {
            Ok((board.tasks.keys().map(|&task| board.line(task)).collect(), false))
        }
        "next" if rest.is_empty() => {
            let line = board.next().map_or("nothing to do".to_string(), |task| board.line(task));
            Ok((vec![line], false))
        }
        _ => Err(Failure::Usage),
    }
}

fn main() {
    let args: Vec<String> = env::args().skip(1).collect();
    let path = env::var_os("TODO_FILE").map_or_else(|| PathBuf::from("todo.txt"), PathBuf::from);
    let result = store::load(&path).map_err(Failure::Error).and_then(|mut board| {
        let (lines, changed) = run(&args, &mut board)?;
        if changed {
            store::save(&path, &board).map_err(Failure::Error)?;
        }
        Ok(lines)
    });
    match result {
        Ok(lines) => {
            for line in lines {
                println!("{}", line);
            }
        }
        Err(Failure::Usage) => {
            eprintln!("{}", USAGE);
            process::exit(2);
        }
        Err(Failure::Error(message)) => {
            eprintln!("error: {}", message);
            process::exit(1);
        }
    }
}
