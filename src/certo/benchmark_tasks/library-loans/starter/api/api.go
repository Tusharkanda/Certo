// Package api is the library's HTTP API.
package api

import (
	"net/http"
	"time"
)

// NewHandler returns the API, with every date read from clock.
func NewHandler(clock func() time.Time) http.Handler {
	_ = clock
	return http.NotFoundHandler()
}
