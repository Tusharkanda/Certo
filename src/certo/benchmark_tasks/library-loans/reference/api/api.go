// Package api is the library's HTTP API: books, members and loans, kept in
// memory, with every date read from the clock it is given.
package api

import (
	"bytes"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"sort"
	"strconv"
	"strings"
	"sync"
	"time"
)

const (
	loanDays     = 14
	finePerDay   = 25
	maxFine      = 1000
	maxOpenLoans = 3
	dateLayout   = "2006-01-02"
)

type book struct {
	ISBN      string `json:"isbn"`
	Title     string `json:"title"`
	Available bool   `json:"available"`
}

type member struct {
	ID   int    `json:"id"`
	Name string `json:"name"`
}

type loan struct {
	ID       int
	ISBN     string
	MemberID int
	Borrowed time.Time
	Due      time.Time
	Returned *time.Time
	Fine     int
}

type server struct {
	clock   func() time.Time
	mu      sync.Mutex
	books   map[string]*book
	members map[int]*member
	loans   map[int]*loan
	nextID  struct{ member, loan int }
}

// apiError is an answer with a status code and a message.
type apiError struct {
	status  int
	message string
}

func (e *apiError) Error() string { return e.message }

func fail(status int, format string, args ...any) *apiError {
	return &apiError{status, fmt.Sprintf(format, args...)}
}

// NewHandler returns the API, with every date read from clock.
func NewHandler(clock func() time.Time) http.Handler {
	s := &server{
		clock:   clock,
		books:   map[string]*book{},
		members: map[int]*member{},
		loans:   map[int]*loan{},
	}
	routes := []struct {
		method, pattern string
		handle          func(*http.Request) (int, any, error)
	}{
		{"POST", "/books", s.addBook},
		{"GET", "/books/{isbn}", s.getBook},
		{"POST", "/members", s.addMember},
		{"GET", "/members/{id}/loans", s.memberLoans},
		{"POST", "/loans", s.lend},
		{"POST", "/loans/{id}/return", s.giveBack},
	}
	mux := http.NewServeMux()
	for _, route := range routes {
		route := route
		mux.HandleFunc(route.pattern, func(w http.ResponseWriter, r *http.Request) {
			if r.Method != route.method {
				write(w, http.StatusMethodNotAllowed, map[string]string{"error": "method not allowed"})
				return
			}
			s.mu.Lock()
			status, body, err := route.handle(r)
			s.mu.Unlock()
			var answer *apiError
			if errors.As(err, &answer) {
				write(w, answer.status, map[string]string{"error": answer.message})
				return
			}
			write(w, status, body)
		})
	}
	mux.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		write(w, http.StatusNotFound, map[string]string{"error": "not found"})
	})
	return mux
}

func write(w http.ResponseWriter, status int, body any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(body)
}

// decode reads a JSON object with exactly the fields of target.
func decode(r *http.Request, target any) error {
	data, err := io.ReadAll(r.Body)
	if err != nil {
		return fail(400, "can't read the body")
	}
	var fields map[string]json.RawMessage
	if err := json.Unmarshal(data, &fields); err != nil || fields == nil {
		return fail(400, "the body must be a JSON object")
	}
	dec := json.NewDecoder(bytes.NewReader(data))
	dec.DisallowUnknownFields()
	if err := dec.Decode(target); err != nil {
		return fail(400, "bad body: %v", err)
	}
	want, _ := json.Marshal(target)
	var expected map[string]json.RawMessage
	_ = json.Unmarshal(want, &expected)
	for name := range expected {
		if _, ok := fields[name]; !ok {
			return fail(400, "missing field %q", name)
		}
	}
	return nil
}

func pathID(r *http.Request) (int, error) {
	id, err := strconv.Atoi(r.PathValue("id"))
	if err != nil || id <= 0 || strings.HasPrefix(r.PathValue("id"), "+") {
		return 0, fail(400, "the id must be a positive whole number")
	}
	return id, nil
}

// normalizeISBN removes hyphens; ok is false for anything but a valid
// ISBN-13.
func normalizeISBN(text string) (string, bool) {
	isbn := strings.ReplaceAll(text, "-", "")
	if len(isbn) != 13 {
		return isbn, false
	}
	sum := 0
	for i, c := range isbn {
		if c < '0' || c > '9' {
			return isbn, false
		}
		weight := 1
		if i%2 == 1 {
			weight = 3
		}
		if i < 12 {
			sum += int(c-'0') * weight
		}
	}
	return isbn, (10-sum%10)%10 == int(isbn[12]-'0')
}

func (s *server) today() time.Time {
	now := s.clock().UTC()
	return time.Date(now.Year(), now.Month(), now.Day(), 0, 0, 0, 0, time.UTC)
}

func (s *server) addBook(r *http.Request) (int, any, error) {
	var in struct {
		ISBN  string `json:"isbn"`
		Title string `json:"title"`
	}
	if err := decode(r, &in); err != nil {
		return 0, nil, err
	}
	isbn, ok := normalizeISBN(in.ISBN)
	if !ok {
		return 0, nil, fail(422, "not a valid ISBN-13: %q", in.ISBN)
	}
	if in.Title == "" {
		return 0, nil, fail(422, "the title must not be empty")
	}
	if _, exists := s.books[isbn]; exists {
		return 0, nil, fail(409, "book %s already exists", isbn)
	}
	b := &book{ISBN: isbn, Title: in.Title, Available: true}
	s.books[isbn] = b
	return 201, b, nil
}

func (s *server) getBook(r *http.Request) (int, any, error) {
	isbn := strings.ReplaceAll(r.PathValue("isbn"), "-", "")
	b, ok := s.books[isbn]
	if !ok {
		return 0, nil, fail(404, "no book %s", isbn)
	}
	return 200, b, nil
}

func (s *server) addMember(r *http.Request) (int, any, error) {
	var in struct {
		Name string `json:"name"`
	}
	if err := decode(r, &in); err != nil {
		return 0, nil, err
	}
	if in.Name == "" {
		return 0, nil, fail(422, "the name must not be empty")
	}
	s.nextID.member++
	m := &member{ID: s.nextID.member, Name: in.Name}
	s.members[m.ID] = m
	return 201, m, nil
}

func (s *server) view(l *loan, overdue bool) map[string]any {
	out := map[string]any{
		"id":        l.ID,
		"isbn":      l.ISBN,
		"member_id": l.MemberID,
		"borrowed":  l.Borrowed.Format(dateLayout),
		"due":       l.Due.Format(dateLayout),
	}
	if l.Returned != nil {
		out["returned"] = l.Returned.Format(dateLayout)
		out["fine_cents"] = l.Fine
	}
	if overdue {
		out["overdue"] = s.today().After(l.Due)
	}
	return out
}

func (s *server) openLoans(memberID int) []*loan {
	var open []*loan
	for _, l := range s.loans {
		if l.MemberID == memberID && l.Returned == nil {
			open = append(open, l)
		}
	}
	sort.Slice(open, func(i, j int) bool {
		if !open[i].Due.Equal(open[j].Due) {
			return open[i].Due.Before(open[j].Due)
		}
		return open[i].ID < open[j].ID
	})
	return open
}

func (s *server) lend(r *http.Request) (int, any, error) {
	var in struct {
		ISBN     string `json:"isbn"`
		MemberID int    `json:"member_id"`
	}
	if err := decode(r, &in); err != nil {
		return 0, nil, err
	}
	isbn := strings.ReplaceAll(in.ISBN, "-", "")
	b, ok := s.books[isbn]
	if !ok {
		return 0, nil, fail(404, "no book %s", isbn)
	}
	if _, ok := s.members[in.MemberID]; !ok {
		return 0, nil, fail(404, "no member %d", in.MemberID)
	}
	if !b.Available {
		return 0, nil, fail(409, "book %s is on loan", isbn)
	}
	open := s.openLoans(in.MemberID)
	if len(open) >= maxOpenLoans {
		return 0, nil, fail(409, "member %d already has %d loans", in.MemberID, maxOpenLoans)
	}
	today := s.today()
	for _, l := range open {
		if today.After(l.Due) {
			return 0, nil, fail(409, "member %d has an overdue loan", in.MemberID)
		}
	}
	s.nextID.loan++
	l := &loan{
		ID:       s.nextID.loan,
		ISBN:     isbn,
		MemberID: in.MemberID,
		Borrowed: today,
		Due:      today.AddDate(0, 0, loanDays),
	}
	s.loans[l.ID] = l
	b.Available = false
	return 201, s.view(l, false), nil
}

func (s *server) giveBack(r *http.Request) (int, any, error) {
	id, err := pathID(r)
	if err != nil {
		return 0, nil, err
	}
	l, ok := s.loans[id]
	if !ok {
		return 0, nil, fail(404, "no loan %d", id)
	}
	if l.Returned != nil {
		return 0, nil, fail(409, "loan %d was already returned", id)
	}
	today := s.today()
	l.Returned = &today
	if days := int(today.Sub(l.Due).Hours() / 24); days > 0 {
		l.Fine = days * finePerDay
		if l.Fine > maxFine {
			l.Fine = maxFine
		}
	}
	s.books[l.ISBN].Available = true
	return 200, s.view(l, false), nil
}

func (s *server) memberLoans(r *http.Request) (int, any, error) {
	id, err := pathID(r)
	if err != nil {
		return 0, nil, err
	}
	if _, ok := s.members[id]; !ok {
		return 0, nil, fail(404, "no member %d", id)
	}
	out := []map[string]any{}
	for _, l := range s.openLoans(id) {
		out = append(out, s.view(l, true))
	}
	return 200, out, nil
}
