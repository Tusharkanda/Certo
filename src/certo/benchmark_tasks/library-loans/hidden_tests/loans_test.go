// Hidden tests: only the HTTP API that api.NewHandler returns.
package hidden

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"reflect"
	"strings"
	"sync"
	"testing"
	"time"

	"example.com/library/api"
)

const (
	isbnA = "9780306406157" // valid
	isbnB = "9781861972712" // valid
	isbnC = "9780131103627" // valid
	isbnD = "9780262033848" // valid
)

type lib struct {
	t   *testing.T
	h   http.Handler
	now time.Time
	mu  sync.Mutex
}

func newLib(t *testing.T) *lib {
	l := &lib{t: t, now: time.Date(2025, 11, 3, 9, 30, 0, 0, time.UTC)}
	l.h = api.NewHandler(func() time.Time {
		l.mu.Lock()
		defer l.mu.Unlock()
		return l.now
	})
	return l
}

func (l *lib) days(n int) {
	l.mu.Lock()
	l.now = l.now.AddDate(0, 0, n)
	l.mu.Unlock()
}

// call returns the status and the decoded JSON body, after checking the
// Content-Type and, for an error, the {"error": "..."} shape.
func (l *lib) call(method, path, body string) (int, any) {
	l.t.Helper()
	rec := httptest.NewRecorder()
	l.h.ServeHTTP(rec, httptest.NewRequest(method, path, strings.NewReader(body)))
	if ct := rec.Header().Get("Content-Type"); !strings.HasPrefix(ct, "application/json") {
		l.t.Fatalf("%s %s: Content-Type %q, body %q", method, path, ct, rec.Body.String())
	}
	var out any
	if err := json.Unmarshal(rec.Body.Bytes(), &out); err != nil {
		l.t.Fatalf("%s %s: body isn't JSON: %q", method, path, rec.Body.String())
	}
	if rec.Code >= 400 {
		obj, ok := out.(map[string]any)
		msg, isText := obj["error"].(string)
		if !ok || len(obj) != 1 || !isText || msg == "" {
			l.t.Fatalf("%s %s: error body %q isn't {\"error\": \"...\"}", method, path, rec.Body.String())
		}
	}
	return rec.Code, out
}

func (l *lib) want(status int, method, path, body string) any {
	l.t.Helper()
	got, out := l.call(method, path, body)
	if got != status {
		l.t.Fatalf("%s %s %s: status %d, want %d (%v)", method, path, body, got, status, out)
	}
	return out
}

func (l *lib) setup() {
	l.t.Helper()
	l.want(201, "POST", "/books", `{"isbn": "`+isbnA+`", "title": "A"}`)
	l.want(201, "POST", "/books", `{"isbn": "`+isbnB+`", "title": "B"}`)
	l.want(201, "POST", "/books", `{"isbn": "`+isbnC+`", "title": "C"}`)
	l.want(201, "POST", "/books", `{"isbn": "`+isbnD+`", "title": "D"}`)
	l.want(201, "POST", "/members", `{"name": "Ada"}`)
	l.want(201, "POST", "/members", `{"name": "Bob"}`)
}

func lend(isbn string, member string) string {
	return `{"isbn": "` + isbn + `", "member_id": ` + member + `}`
}

func eq(t *testing.T, got, want any) {
	t.Helper()
	g, _ := json.Marshal(got)
	var norm any
	_ = json.Unmarshal(g, &norm)
	w, _ := json.Marshal(want)
	var wantNorm any
	_ = json.Unmarshal(w, &wantNorm)
	if !reflect.DeepEqual(norm, wantNorm) {
		t.Fatalf("got %s, want %s", g, w)
	}
}

func TestHiddenBooksAndISBNs(t *testing.T) {
	l := newLib(t)
	eq(t, l.want(201, "POST", "/books", `{"isbn": "978-0-306-40615-7", "title": "Measure"}`),
		map[string]any{"isbn": isbnA, "title": "Measure", "available": true})
	l.want(409, "POST", "/books", `{"isbn": "`+isbnA+`", "title": "Again"}`)
	for _, bad := range []string{"9780306406158", "978030640615", "97803064061577", "978030640615X", "0306406152"} {
		l.want(422, "POST", "/books", `{"isbn": "`+bad+`", "title": "x"}`)
	}
	l.want(422, "POST", "/books", `{"isbn": "`+isbnB+`", "title": ""}`)
	eq(t, l.want(200, "GET", "/books/978-0306406157", ""),
		map[string]any{"isbn": isbnA, "title": "Measure", "available": true})
	l.want(404, "GET", "/books/"+isbnB, "")
}

func TestHiddenMembers(t *testing.T) {
	l := newLib(t)
	eq(t, l.want(201, "POST", "/members", `{"name": "Ada"}`), map[string]any{"id": 1, "name": "Ada"})
	eq(t, l.want(201, "POST", "/members", `{"name": "Bob"}`), map[string]any{"id": 2, "name": "Bob"})
	l.want(422, "POST", "/members", `{"name": ""}`)
	eq(t, l.want(201, "POST", "/members", `{"name": "Cy"}`), map[string]any{"id": 3, "name": "Cy"})
}

func TestHiddenALoanAndItsDates(t *testing.T) {
	l := newLib(t)
	l.setup()
	eq(t, l.want(201, "POST", "/loans", lend("978-1-86197-271-2", "2")), map[string]any{
		"id": 1, "isbn": isbnB, "member_id": 2, "borrowed": "2025-11-03", "due": "2025-11-17",
	})
	eq(t, l.want(200, "GET", "/books/"+isbnB, ""), map[string]any{"isbn": isbnB, "title": "B", "available": false})
	l.want(409, "POST", "/loans", lend(isbnB, "1"))
	l.want(404, "POST", "/loans", lend(isbnB, "9"))
	l.want(404, "POST", "/loans", lend("9780470059029", "1"))
}

func TestHiddenTheDateIsReadInUTC(t *testing.T) {
	l := newLib(t)
	l.setup()
	tokyo := time.FixedZone("JST", 9*3600)
	l.mu.Lock()
	l.now = time.Date(2025, 11, 4, 1, 0, 0, 0, tokyo) // 2025-11-03 16:00 UTC
	l.mu.Unlock()
	eq(t, l.want(201, "POST", "/loans", lend(isbnA, "1")), map[string]any{
		"id": 1, "isbn": isbnA, "member_id": 1, "borrowed": "2025-11-03", "due": "2025-11-17",
	})
}

func TestHiddenFines(t *testing.T) {
	cases := []struct {
		after int
		fine  int
	}{{14, 0}, {3, 0}, {15, 25}, {18, 100}, {54, 1000}, {80, 1000}}
	for _, c := range cases {
		l := newLib(t)
		l.setup()
		l.want(201, "POST", "/loans", lend(isbnA, "1"))
		l.days(c.after)
		got := l.want(200, "POST", "/loans/1/return", "").(map[string]any)
		if got["fine_cents"] != float64(c.fine) {
			t.Errorf("returned after %d days: fine %v, want %d", c.after, got["fine_cents"], c.fine)
		}
		want := l.now.Format("2006-01-02")
		if got["returned"] != want || got["due"] != "2025-11-17" || got["id"] != float64(1) {
			t.Errorf("returned after %d days: %v", c.after, got)
		}
		l.want(409, "POST", "/loans/1/return", "")
		eq(t, l.want(200, "GET", "/books/"+isbnA, "").(map[string]any)["available"], true)
	}
}

func TestHiddenThreeOpenLoansAtMost(t *testing.T) {
	l := newLib(t)
	l.setup()
	l.want(201, "POST", "/loans", lend(isbnA, "1"))
	l.want(201, "POST", "/loans", lend(isbnB, "1"))
	l.want(201, "POST", "/loans", lend(isbnC, "1"))
	l.want(409, "POST", "/loans", lend(isbnD, "1")) // a fourth open loan
	l.want(200, "POST", "/loans/2/return", "")
	l.want(201, "POST", "/loans", lend(isbnD, "1")) // three again
	l.want(409, "POST", "/loans", lend(isbnB, "1"))
}

func TestHiddenNoNewLoanWhileOneIsOverdue(t *testing.T) {
	l := newLib(t)
	l.setup()
	l.want(201, "POST", "/loans", lend(isbnA, "1"))
	l.days(14)
	l.want(201, "POST", "/loans", lend(isbnB, "1")) // due today: not overdue yet
	l.days(1)
	l.want(409, "POST", "/loans", lend(isbnC, "1"))
	l.want(201, "POST", "/loans", lend(isbnC, "2"))
	l.want(200, "POST", "/loans/1/return", "")
	l.want(201, "POST", "/loans", lend(isbnD, "1"))
}

func TestHiddenAMembersLoans(t *testing.T) {
	l := newLib(t)
	l.setup()
	eq(t, l.want(200, "GET", "/members/1/loans", ""), []any{})
	l.want(201, "POST", "/loans", lend(isbnA, "1")) // loan 1, due 11-17
	l.days(2)
	l.want(201, "POST", "/loans", lend(isbnB, "1")) // loan 2, due 11-19
	l.days(-2)
	l.want(201, "POST", "/loans", lend(isbnC, "1")) // loan 3, due 11-17
	l.want(201, "POST", "/loans", lend(isbnD, "2"))
	l.days(15) // 2025-11-18
	eq(t, l.want(200, "GET", "/members/1/loans", ""), []any{
		map[string]any{"id": 1, "isbn": isbnA, "member_id": 1, "borrowed": "2025-11-03", "due": "2025-11-17", "overdue": true},
		map[string]any{"id": 3, "isbn": isbnC, "member_id": 1, "borrowed": "2025-11-03", "due": "2025-11-17", "overdue": true},
		map[string]any{"id": 2, "isbn": isbnB, "member_id": 1, "borrowed": "2025-11-05", "due": "2025-11-19", "overdue": false},
	})
	l.want(200, "POST", "/loans/3/return", "")
	got := l.want(200, "GET", "/members/1/loans", "").([]any)
	if len(got) != 2 {
		t.Fatalf("a returned loan is still listed: %v", got)
	}
	l.want(404, "GET", "/members/7/loans", "")
}

func TestHiddenBadRequests(t *testing.T) {
	l := newLib(t)
	l.setup()
	for _, body := range []string{
		``, `not json`, `[]`, `"isbn"`, `null`,
		`{"isbn": "` + isbnA + `"}`,
		`{"isbn": "` + isbnA + `", "title": "x", "year": 1990}`,
		`{"isbn": 9780306406157, "title": "x"}`,
	} {
		l.want(400, "POST", "/books", body)
	}
	l.want(400, "POST", "/members", `{}`)
	l.want(400, "POST", "/members", `{"name": "x", "id": 3}`)
	l.want(400, "POST", "/loans", `{"isbn": "`+isbnA+`", "member_id": "1"}`)
	l.want(400, "POST", "/loans", `{"isbn": "`+isbnA+`"}`)
	for _, id := range []string{"abc", "0", "-1", "1.5"} {
		l.want(400, "POST", "/loans/"+id+"/return", "")
		l.want(400, "GET", "/members/"+id+"/loans", "")
	}
	l.want(404, "POST", "/loans/5/return", "")
}

func TestHiddenMethodsAndPaths(t *testing.T) {
	l := newLib(t)
	l.setup()
	l.want(405, "GET", "/books", "")
	l.want(405, "DELETE", "/books/"+isbnA, "")
	l.want(405, "GET", "/loans", "")
	l.want(405, "POST", "/members/1/loans", "")
	l.want(404, "GET", "/nothing", "")
	l.want(404, "GET", "/", "")
}

func TestHiddenConcurrentLoansOfOneBook(t *testing.T) {
	// Many rounds, every request released at once: without a lock, one
	// book gets lent twice or the maps break.
	const members = 16
	for round := 0; round < 200; round++ {
		l := newLib(t)
		l.want(201, "POST", "/books", `{"isbn": "`+isbnA+`", "title": "A"}`)
		for i := 0; i < members; i++ {
			l.want(201, "POST", "/members", `{"name": "m"}`)
		}
		start := make(chan struct{})
		codes := make(chan int, members)
		var wg sync.WaitGroup
		for i := 1; i <= members; i++ {
			wg.Add(1)
			go func(member int) {
				defer wg.Done()
				req := httptest.NewRequest("POST", "/loans",
					strings.NewReader(`{"isbn": "`+isbnA+`", "member_id": `+itoa(member)+`}`))
				rec := httptest.NewRecorder()
				<-start
				l.h.ServeHTTP(rec, req)
				codes <- rec.Code
			}(i)
		}
		close(start)
		wg.Wait()
		close(codes)
		created := 0
		for code := range codes {
			if code == 201 {
				created++
			} else if code != 409 {
				t.Fatalf("round %d: unexpected status %d", round, code)
			}
		}
		if created != 1 {
			t.Fatalf("round %d: one book was lent %d times", round, created)
		}
	}
}

func itoa(n int) string {
	b, _ := json.Marshal(n)
	return string(b)
}
