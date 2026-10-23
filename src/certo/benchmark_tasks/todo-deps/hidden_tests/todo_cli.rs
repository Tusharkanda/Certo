// Hidden tests: they run the built `todo` binary only, each with its own
// TODO_FILE, so they don't depend on how the code is organised.

use std::fs;
use std::path::PathBuf;
use std::process::Command;
use std::sync::atomic::{AtomicUsize, Ordering};

static NEXT: AtomicUsize = AtomicUsize::new(0);

struct List {
    file: PathBuf,
    dir: PathBuf,
}

struct Out {
    code: i32,
    stdout: String,
    stderr: String,
}

impl List {
    fn new() -> List {
        let n = NEXT.fetch_add(1, Ordering::SeqCst);
        let dir = std::env::temp_dir().join(format!("certo-todo-{}-{}", std::process::id(), n));
        let _ = fs::remove_dir_all(&dir);
        fs::create_dir_all(&dir).unwrap();
        List { file: dir.join("list.txt"), dir }
    }

    fn run(&self, args: &[&str]) -> Out {
        let out = Command::new(env!("CARGO_BIN_EXE_todo"))
            .args(args)
            .env("TODO_FILE", &self.file)
            .current_dir(&self.dir)
            .output()
            .unwrap();
        Out {
            code: out.status.code().unwrap_or(-1),
            stdout: String::from_utf8_lossy(&out.stdout).to_string(),
            stderr: String::from_utf8_lossy(&out.stderr).to_string(),
        }
    }

    /// Runs a command that must succeed and returns its standard output.
    fn ok(&self, args: &[&str]) -> String {
        let out = self.run(args);
        assert_eq!(out.code, 0, "todo {:?} failed: {}", args, out.stderr);
        out.stdout
    }

    fn contents(&self) -> Option<Vec<u8>> {
        fs::read(&self.file).ok()
    }

    /// A command that must fail with `code` and leave the file unchanged.
    fn fails(&self, args: &[&str], code: i32) -> String {
        let before = self.contents();
        let out = self.run(args);
        assert_eq!(out.code, code, "todo {:?}: stdout {:?} stderr {:?}", args, out.stdout, out.stderr);
        assert_eq!(out.stdout, "", "todo {:?} printed to stdout", args);
        assert_eq!(self.contents(), before, "todo {:?} changed the file", args);
        out.stderr
    }

    fn error(&self, args: &[&str]) -> String {
        let stderr = self.fails(args, 1);
        let lines: Vec<&str> = stderr.lines().collect();
        assert_eq!(lines.len(), 1, "todo {:?}: {:?}", args, stderr);
        lines[0].to_string()
    }

    fn usage(&self, args: &[&str]) {
        let stderr = self.fails(args, 2);
        assert!(
            stderr.lines().any(|l| l.starts_with("usage:")),
            "todo {:?}: no usage line in {:?}",
            args,
            stderr
        );
    }
}

impl Drop for List {
    fn drop(&mut self) {
        let _ = fs::remove_dir_all(&self.dir);
    }
}

#[test]
fn hidden_add_list_and_ids() {
    let l = List::new();
    assert_eq!(l.ok(&["list"]), "");
    assert_eq!(l.ok(&["add", "Buy", "food"]), "added 1\n");
    assert_eq!(l.ok(&["add", "Cook dinner"]), "added 2\n");
    assert_eq!(l.ok(&["list"]), "[ ] 1 Buy food\n[ ] 2 Cook dinner\n");
}

#[test]
fn hidden_ids_are_never_reused() {
    let l = List::new();
    l.ok(&["add", "a"]);
    l.ok(&["add", "b"]);
    assert_eq!(l.ok(&["remove", "2"]), "removed 2\n");
    assert_eq!(l.ok(&["add", "c"]), "added 3\n");
    l.ok(&["remove", "3"]);
    l.ok(&["remove", "1"]);
    assert_eq!(l.ok(&["add", "d"]), "added 4\n");
    assert_eq!(l.ok(&["list"]), "[ ] 4 d\n");
}

#[test]
fn hidden_after_anywhere_and_waits_shown_ascending() {
    let l = List::new();
    l.ok(&["add", "a"]);
    l.ok(&["add", "b"]);
    assert_eq!(l.ok(&["add", "--after", "2", "Cook", "--after", "1", "dinner"]), "added 3\n");
    assert_eq!(l.ok(&["list"]), "[ ] 1 a\n[ ] 2 b\n[ ] 3 Cook dinner (after 1, 2)\n");
    assert_eq!(l.ok(&["done", "1"]), "done 1\n");
    assert_eq!(l.ok(&["list"]), "[x] 1 a\n[ ] 2 b\n[ ] 3 Cook dinner (after 2)\n");
    l.ok(&["done", "2"]);
    assert_eq!(l.ok(&["list"]), "[x] 1 a\n[x] 2 b\n[ ] 3 Cook dinner\n");
}

#[test]
fn hidden_done_rules() {
    let l = List::new();
    l.ok(&["add", "a"]);
    l.ok(&["add", "b"]);
    l.ok(&["add", "c", "--after", "2", "--after", "1"]);
    assert_eq!(l.error(&["done", "3"]), "error: task 3 is blocked by 1, 2");
    l.ok(&["done", "2"]);
    assert_eq!(l.error(&["done", "3"]), "error: task 3 is blocked by 1");
    assert_eq!(l.error(&["done", "2"]), "error: task 2 is already done");
    assert_eq!(l.error(&["done", "9"]), "error: no task 9");
}

#[test]
fn hidden_next() {
    let l = List::new();
    assert_eq!(l.ok(&["next"]), "nothing to do\n");
    l.ok(&["add", "a"]);
    l.ok(&["add", "b"]);
    l.ok(&["block", "1", "--after", "2"]);
    assert_eq!(l.ok(&["next"]), "[ ] 2 b\n");
    l.ok(&["done", "2"]);
    assert_eq!(l.ok(&["next"]), "[ ] 1 a\n");
    l.ok(&["done", "1"]);
    assert_eq!(l.ok(&["next"]), "nothing to do\n");
}

#[test]
fn hidden_block_and_cycles() {
    let l = List::new();
    l.ok(&["add", "a"]);
    l.ok(&["add", "b", "--after", "1"]);
    l.ok(&["add", "c", "--after", "2"]);
    // 3 waits for 2, which waits for 1: only an indirect wait.
    assert_eq!(l.error(&["block", "1", "--after", "3"]), "error: task 1 would wait for itself");
    assert_eq!(l.ok(&["block", "3", "--after", "1"]), "3 waits for 1\n");
    assert_eq!(l.ok(&["block", "3", "--after", "1"]), "3 waits for 1\n");
    assert_eq!(l.ok(&["list"]), "[ ] 1 a\n[ ] 2 b (after 1)\n[ ] 3 c (after 1, 2)\n");
    assert_eq!(l.error(&["block", "1", "--after", "3"]), "error: task 1 would wait for itself");
    assert_eq!(l.error(&["block", "1", "--after", "2"]), "error: task 1 would wait for itself");
    assert_eq!(l.error(&["block", "2", "--after", "2"]), "error: task 2 would wait for itself");
    assert_eq!(l.error(&["block", "2", "--after", "8"]), "error: no task 8");
    assert_eq!(l.error(&["block", "8", "--after", "2"]), "error: no task 8");
}

#[test]
fn hidden_remove_rules() {
    let l = List::new();
    l.ok(&["add", "a"]);
    l.ok(&["add", "b"]);
    l.ok(&["add", "c", "--after", "1"]);
    l.ok(&["add", "d", "--after", "1", "--after", "2"]);
    assert_eq!(l.error(&["remove", "1"]), "error: task 1 is needed by 3, 4");
    assert_eq!(l.ok(&["remove", "1", "--force"]), "removed 1\n");
    assert_eq!(l.ok(&["list"]), "[ ] 2 b\n[ ] 3 c\n[ ] 4 d (after 2)\n");
    assert_eq!(l.ok(&["next"]), "[ ] 2 b\n");
    assert_eq!(l.ok(&["remove", "3"]), "removed 3\n");
    assert_eq!(l.error(&["remove", "3"]), "error: no task 3");
}

#[test]
fn hidden_an_unknown_after_is_an_error() {
    let l = List::new();
    l.ok(&["add", "a"]);
    assert_eq!(l.error(&["add", "b", "--after", "7"]), "error: no task 7");
    assert_eq!(l.ok(&["add", "c"]), "added 2\n");
}

#[test]
fn hidden_titles_survive_the_file() {
    let l = List::new();
    l.ok(&["add", "tab\there | pipe # hash \"quotes\" 'single'"]);
    l.ok(&["add", "Café ☕ naïve", "--after", "1"]);
    assert_eq!(
        l.ok(&["list"]),
        "[ ] 1 tab\there | pipe # hash \"quotes\" 'single'\n\
         [ ] 2 Café ☕ naïve (after 1)\n"
    );
}

#[test]
fn hidden_the_default_file_is_todo_txt_in_the_current_folder() {
    let l = List::new();
    let run = |args: &[&str]| {
        Command::new(env!("CARGO_BIN_EXE_todo"))
            .args(args)
            .env_remove("TODO_FILE")
            .current_dir(&l.dir)
            .output()
            .unwrap()
    };
    assert!(run(&["add", "here"]).status.success());
    assert!(l.dir.join("todo.txt").is_file());
    assert_eq!(String::from_utf8_lossy(&run(&["list"]).stdout), "[ ] 1 here\n");
}

#[test]
fn hidden_usage_errors() {
    let l = List::new();
    l.ok(&["add", "a"]);
    for args in [
        vec![],
        vec!["frobnicate"],
        vec!["add"],
        vec!["add", "--after", "1"],
        vec!["add", "x", "--after"],
        vec!["add", "x", "--after", "one"],
        vec!["add", "x", "--colour", "red"],
        vec!["add", "--colour", "x"],
        vec!["done"],
        vec!["done", "0"],
        vec!["done", "-1"],
        vec!["done", "1.5"],
        vec!["done", "abc"],
        vec!["remove", "1", "--hard"],
        vec!["block", "1"],
        vec!["block", "1", "2"],
    ] {
        l.usage(&args);
    }
}
