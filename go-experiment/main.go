// Experiment: serve the two hottest club portal endpoints from Go, proxy everything else to Django.
//
//	GET  /api/v1/user/me/                      (fetched on every logged-in page load)
//	POST /api/v1/poll/polls/{id}/submissions/  (the form check-in burst)
//
// Responses are meant to be byte-identical to Django's. Anything outside the common path
// (anonymous users, private or closed polls, validation errors, upload questions...) is
// forwarded to Django untouched, so Django stays the source of truth for edge cases.
package main

import (
	"bytes"
	"context"
	"io"
	"log"
	"net/http"
	"net/http/httputil"
	"net/url"
	"os"
	"strings"
	"time"
	_ "time/tzdata"

	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/redis/go-redis/v9"
)

type server struct {
	db     *pgxpool.Pool
	redis  *redis.Client
	django *httputil.ReverseProxy
}

func main() {
	ctx := context.Background()

	db, err := pgxpool.New(ctx, mustEnv("DATABASE_URL"))
	if err != nil {
		log.Fatal(err)
	}
	djangoURL, err := url.Parse(mustEnv("DJANGO_URL"))
	if err != nil {
		log.Fatal(err)
	}

	s := &server{
		db:     db,
		redis:  redis.NewClient(&redis.Options{Addr: mustEnv("REDIS_ADDR")}),
		django: httputil.NewSingleHostReverseProxy(djangoURL),
	}

	mux := http.NewServeMux()
	mux.HandleFunc("GET /api/v1/user/me/", s.handleMe)
	mux.HandleFunc("POST /api/v1/poll/polls/{id}/submissions/", s.handleSubmit)
	mux.Handle("/", s.django)

	addr := ":" + envOr("PORT", "9300")
	log.Printf("listening on %s, proxying to %s", addr, djangoURL)
	srv := &http.Server{Addr: addr, Handler: mux, ReadHeaderTimeout: 10 * time.Second}
	log.Fatal(srv.ListenAndServe())
}

// proxy forwards a request to Django, replaying a body that was already read.
func (s *server) proxy(w http.ResponseWriter, r *http.Request, body []byte) {
	if body != nil {
		r.Body = io.NopCloser(bytes.NewReader(body))
		r.ContentLength = int64(len(body))
	}
	s.django.ServeHTTP(w, r)
}

// authUser resolves a DRF "Authorization: Token <key>" header. ok is false when the request
// should be left to Django (no token, bad token, inactive user).
func (s *server) authUser(ctx context.Context, r *http.Request) (userID int64, ok bool) {
	keyword, key, found := strings.Cut(r.Header.Get("Authorization"), " ")
	if !found || !strings.EqualFold(keyword, "token") || key == "" || strings.Contains(key, " ") {
		return 0, false
	}

	var active bool
	err := s.db.QueryRow(ctx,
		`SELECT u.id, u.is_active FROM authtoken_token t JOIN users_user u ON u.id = t.user_id WHERE t.key = $1`,
		key,
	).Scan(&userID, &active)
	if err != nil || !active {
		return 0, false
	}
	return userID, true
}

// requestLocation mirrors core.middleware.TimezoneMiddleware.
func requestLocation(r *http.Request) *time.Location {
	name := r.Header.Get("X-Timezone")
	if name == "" {
		if c, err := r.Cookie("user_timezone"); err == nil {
			name = c.Value
		}
	}
	if name == "" {
		return time.UTC
	}
	loc, err := time.LoadLocation(name)
	if err != nil {
		return time.UTC
	}
	return loc
}

func mustEnv(key string) string {
	v := os.Getenv(key)
	if v == "" {
		log.Fatalf("%s is required", key)
	}
	return v
}

func envOr(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}
