package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"net/http"
	"strings"
	"time"
)

// writeJSON renders compact JSON like DRF's JSONRenderer (no HTML escaping, no trailing newline).
func writeJSON(w http.ResponseWriter, status int, v any) {
	var buf bytes.Buffer
	enc := json.NewEncoder(&buf)
	enc.SetEscapeHTML(false)
	if err := enc.Encode(v); err != nil {
		serverError(w, err)
		return
	}
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	w.Write(bytes.TrimSuffix(buf.Bytes(), []byte("\n")))
}

func serverError(w http.ResponseWriter, err error) {
	fmt.Println("error:", err)
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusInternalServerError)
	w.Write([]byte(`{"type":"server_error","errors":[{"code":"error","detail":"Server Error (500)","attr":null}]}`))
}

// isoTime matches DRF's default DateTimeField output (datetime.isoformat, "Z" for UTC).
func isoTime(t time.Time, loc *time.Location) string {
	t = t.In(loc)
	s := t.Format("2006-01-02T15:04:05")
	if us := t.Nanosecond() / 1000; us != 0 {
		s += fmt.Sprintf(".%06d", us)
	}
	if loc == time.UTC {
		return s + "Z"
	}
	return s + t.Format("-07:00")
}

// simpleTime matches the "%Y-%m-%d %H:%M:%S" format used by ModelSerializer.
func simpleTime(t time.Time, loc *time.Location) string {
	return t.In(loc).Format("2006-01-02 15:04:05")
}

// mediaURL matches DRF's ImageField: request.build_absolute_uri(MEDIA_URL + filepath_to_uri(name)).
func mediaURL(r *http.Request, name *string) *string {
	if name == nil || *name == "" {
		return nil
	}
	u := "http://" + r.Host + "/files/media/public/" + quotePath(*name)
	return &u
}

// quotePath mirrors urllib.parse.quote(path, safe="/~!*()'").
func quotePath(s string) string {
	var b strings.Builder
	for i := 0; i < len(s); i++ {
		c := s[i]
		if c >= 'a' && c <= 'z' || c >= 'A' && c <= 'Z' || c >= '0' && c <= '9' || strings.IndexByte("_.-/~!*()'", c) >= 0 {
			b.WriteByte(c)
		} else {
			fmt.Fprintf(&b, "%%%02X", c)
		}
	}
	return b.String()
}
