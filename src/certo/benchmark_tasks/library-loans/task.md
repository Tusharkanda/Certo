# A library loans API in Go

Write the HTTP API of a small lending library, in Go, using only the
standard library (no modules from outside it). `go.mod` is here, and
`api/api.go` has the function to fill in:

```go
func NewHandler(clock func() time.Time) http.Handler
```

Every date comes from `clock`, read in UTC, so tests can choose "today".
Keep everything in memory: each call to `NewHandler` starts empty. The
handler must be safe for concurrent requests. `cmd/server/main.go` may
serve it on a port; nothing tests that. Keep `go test ./...` and
`go vet ./...` passing, and add tests of your own.

## Requests and answers

Request and response bodies are JSON (`Content-Type: application/json`
on every response). Dates are strings like `"2025-11-03"`.

- `POST /books` with `{"isbn": "...", "title": "..."}` adds a book:
  `201` and `{"isbn": ..., "title": ..., "available": true}`. The ISBN
  may contain hyphens, which are removed: the stored and returned ISBN is
  13 digits. It must be a valid ISBN-13: 13 digits whose check digit is
  right (weights 1, 3, 1, 3, ... over the first 12 digits; the check
  digit is (10 − sum mod 10) mod 10). The title must not be empty. A
  book with the same ISBN already there is a `409`.
- `POST /members` with `{"name": "..."}` adds a member: `201` and
  `{"id": N, "name": ...}`. Ids are 1, 2, 3, ... in the order members
  are added. The name must not be empty.
- `POST /loans` with `{"isbn": "...", "member_id": N}` lends a book:
  `201` and `{"id": N, "isbn": ..., "member_id": ..., "borrowed":
  "YYYY-MM-DD", "due": "YYYY-MM-DD"}`. Loan ids are 1, 2, 3, ...
  `borrowed` is today; `due` is 14 days later. The ISBN may have hyphens
  here too. Refused with `404` when the book or the member doesn't
  exist, and with `409` when the book is already on loan, when the
  member already has 3 open loans, or when the member has an overdue
  loan.
- `POST /loans/{id}/return` returns a book: `200` and the loan with
  `"returned": "YYYY-MM-DD"` (today) and `"fine_cents": N` added. The
  fine is 25 cents for each day after the due date, at most 1000. A book
  returned on its due date or before pays 0. `404` for a loan that
  doesn't exist, `409` for one already returned.
- `GET /books/{isbn}`: `200` and the book, where `available` is false
  while it is on loan. The ISBN may have hyphens. `404` if it doesn't
  exist.
- `GET /members/{id}/loans`: `200` and a JSON array of the member's open
  loans (not returned), sorted by due date, then by loan id. Each has the
  fields of a new loan plus `"overdue": true|false`; a loan is overdue
  from the day after its due date. An empty array (`[]`) when there are
  none; `404` for a member that doesn't exist.

## Errors

Every error answer is `{"error": "a message"}` with its status code:

- `400` for a body that isn't a JSON object with exactly the fields
  listed, of the right types (a missing field or an unknown field is a
  `400`), and for an id in a path that isn't a positive whole number;
- `422` for a value the rules above refuse: an invalid ISBN, an empty
  title or name;
- `404`, `405` and `409` as above: `405` for a known path with the wrong
  method, `404` for any unknown path.
