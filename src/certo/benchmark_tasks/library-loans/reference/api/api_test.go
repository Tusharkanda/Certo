package api

import (
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"
)

func do(h http.Handler, method, path, body string) *httptest.ResponseRecorder {
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, httptest.NewRequest(method, path, strings.NewReader(body)))
	return rec
}

func TestISBN(t *testing.T) {
	for text, want := range map[string]bool{
		"978-0-306-40615-7": true,
		"9780306406158":     false,
		"978030640615":      false,
		"97803064061a7":     false,
	} {
		if _, ok := normalizeISBN(text); ok != want {
			t.Errorf("normalizeISBN(%q) = %v, want %v", text, ok, want)
		}
	}
}

func TestLendAndReturnLate(t *testing.T) {
	now := time.Date(2025, 11, 3, 10, 0, 0, 0, time.UTC)
	h := NewHandler(func() time.Time { return now })
	do(h, "POST", "/books", `{"isbn": "9780306406157", "title": "T"}`)
	do(h, "POST", "/members", `{"name": "Ada"}`)
	if rec := do(h, "POST", "/loans", `{"isbn": "9780306406157", "member_id": 1}`); rec.Code != 201 {
		t.Fatalf("lend: %d %s", rec.Code, rec.Body)
	}
	now = now.AddDate(0, 0, 16)
	rec := do(h, "POST", "/loans/1/return", "")
	if rec.Code != 200 || !strings.Contains(rec.Body.String(), `"fine_cents":50`) {
		t.Fatalf("return: %d %s", rec.Code, rec.Body)
	}
}
