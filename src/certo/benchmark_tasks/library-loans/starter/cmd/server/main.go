// Command server serves the library API on :8080.
package main

import (
	"log"
	"net/http"
	"time"

	"example.com/library/api"
)

func main() {
	log.Fatal(http.ListenAndServe(":8080", api.NewHandler(time.Now)))
}
