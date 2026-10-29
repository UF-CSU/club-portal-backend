package main

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"strconv"
	"strings"
	"time"

	"github.com/jackc/pgx/v5"
)

// answerInput is one answer in the request body. Pointer fields distinguish "absent" from null,
// because Django's update_or_create only updates the keys that were sent.
type answerInput struct {
	Question         *int64           `json:"question"`
	TextValue        *json.RawMessage `json:"text_value"`
	NumberValue      *json.RawMessage `json:"number_value"`
	BooleanValue     *json.RawMessage `json:"boolean_value"`
	OtherOptionValue *json.RawMessage `json:"other_option_value"`
	OptionsValue     *[]string        `json:"options_value"`
	FileValue        *json.RawMessage `json:"file_value"`
}

type answerJSON struct {
	ID               int64    `json:"id"`
	OptionsValue     []string `json:"options_value"`
	IsValid          bool     `json:"is_valid"`
	CreatedAt        string   `json:"created_at"`
	UpdatedAt        string   `json:"updated_at"`
	TextValue        *string  `json:"text_value"`
	NumberValue      *int64   `json:"number_value"`
	BooleanValue     *bool    `json:"boolean_value"`
	OtherOptionValue *string  `json:"other_option_value"`
	Error            *string  `json:"error"`
	Question         int64    `json:"question"`
	FileValue        *int64   `json:"file_value"`
}

type submissionUserJSON struct {
	ID      int64        `json:"id"`
	Email   *string      `json:"email"`
	Profile *profileJSON `json:"profile"`
}

type submissionJSON struct {
	ID        int64              `json:"id"`
	Poll      int64              `json:"poll"`
	IsValid   bool               `json:"is_valid"`
	User      submissionUserJSON `json:"user"`
	Answers   []answerJSON       `json:"answers"`
	CreatedAt string             `json:"created_at"`
	UpdatedAt string             `json:"updated_at"`
}

// Profile fields a question can be linked to. Others (e.g. graduation_date) go to Django.
var linkedProfileColumns = map[string]string{
	"name": "name", "phone": "phone", "major": "major", "minor": "minor", "college": "college",
}

// errDeferToDjango means the request is valid input for Django but outside what Go handles.
var errDeferToDjango = errors.New("defer to django")

type question struct {
	inputType string
	linkField *string
	options   map[string]int64 // value -> option id
}

func (s *server) handleSubmit(w http.ResponseWriter, r *http.Request) {
	ctx := r.Context()
	body, err := io.ReadAll(io.LimitReader(r.Body, 1<<20))
	if err != nil {
		serverError(w, err)
		return
	}

	pollID, err := strconv.ParseInt(r.PathValue("id"), 10, 64)
	userID, ok := s.authUser(ctx, r)
	if err != nil || !ok {
		s.proxy(w, r, body)
		return
	}

	var payload struct {
		Answers *[]answerInput `json:"answers"`
	}
	if err := json.Unmarshal(body, &payload); err != nil || payload.Answers == nil {
		s.proxy(w, r, body)
		return
	}

	submissionID, err := s.submit(ctx, pollID, userID, *payload.Answers)
	if errors.Is(err, errDeferToDjango) {
		s.proxy(w, r, body)
		return
	}
	if err != nil {
		serverError(w, err)
		return
	}

	// Mirrors the post_save signal on new submissions: notify live result viewers
	s.notifyListeners(ctx, pollID)

	resp, err := s.loadSubmission(ctx, r, submissionID)
	if err != nil {
		serverError(w, err)
		return
	}
	writeJSON(w, http.StatusCreated, resp)
}

// submit validates the answers, then writes the submission, answers, linked profile fields and
// event attendance in one transaction.
func (s *server) submit(ctx context.Context, pollID, userID int64, answers []answerInput) (int64, error) {
	var status string
	var private bool
	var eventID *int64
	err := s.db.QueryRow(ctx,
		`SELECT p.status, b.is_private, p.event_id FROM polls_poll p JOIN polls_pollbase b ON b.id = p.id WHERE p.id = $1`,
		pollID,
	).Scan(&status, &private, &eventID)
	if err != nil || status != "open" || private {
		return 0, errDeferToDjango // not found, closed and private polls keep Django's handling
	}

	questions, err := s.loadQuestions(ctx, answers)
	if err != nil {
		return 0, err
	}
	optionIDs, err := validateAnswers(answers, questions)
	if err != nil {
		return 0, err
	}

	var hasProfile bool
	if err := s.db.QueryRow(ctx, `SELECT EXISTS (SELECT 1 FROM users_profile WHERE user_id = $1)`, userID).Scan(&hasProfile); err != nil {
		return 0, err
	}
	if !hasProfile {
		return 0, errDeferToDjango
	}

	tx, err := s.db.Begin(ctx)
	if err != nil {
		return 0, err
	}
	defer tx.Rollback(ctx)

	// PollSubmission.objects.get_or_create(user=user, poll=poll)
	var submissionID int64
	err = tx.QueryRow(ctx,
		`SELECT id FROM polls_pollsubmission WHERE poll_id = $1 AND user_id = $2 ORDER BY id LIMIT 1`,
		pollID, userID,
	).Scan(&submissionID)
	if errors.Is(err, pgx.ErrNoRows) {
		err = tx.QueryRow(ctx,
			`INSERT INTO polls_pollsubmission (created_at, updated_at, poll_id, user_id, is_complete)
			 VALUES (now(), now(), $1, $2, true) RETURNING id`,
			pollID, userID,
		).Scan(&submissionID)
	}
	if err != nil {
		return 0, err
	}

	for i, a := range answers {
		if err := upsertAnswer(ctx, tx, submissionID, a, optionIDs[i]); err != nil {
			return 0, err
		}
	}

	if err := updateLinkedProfile(ctx, tx, submissionID, userID); err != nil {
		return 0, err
	}

	if eventID != nil {
		_, err = tx.Exec(ctx,
			`INSERT INTO events_eventattendance (created_at, updated_at, event_id, user_id)
			 VALUES (now(), now(), $1, $2) ON CONFLICT (event_id, user_id) DO NOTHING`,
			*eventID, userID,
		)
		if err != nil {
			return 0, err
		}
	}

	return submissionID, tx.Commit(ctx)
}

func (s *server) loadQuestions(ctx context.Context, answers []answerInput) (map[int64]*question, error) {
	var ids []int64
	for _, a := range answers {
		if a.Question == nil {
			return nil, errDeferToDjango
		}
		ids = append(ids, *a.Question)
	}

	questions := map[int64]*question{}
	batch := &pgx.Batch{}
	batch.Queue(`SELECT id, input_type, link_user_field FROM polls_pollquestion WHERE id = ANY($1)`, ids)
	batch.Queue(`SELECT ci.question_id, o.value, o.id FROM polls_choiceinputoption o
		JOIN polls_choiceinput ci ON ci.id = o.input_id WHERE ci.question_id = ANY($1)`, ids)
	results := s.db.SendBatch(ctx, batch)
	defer results.Close()

	var id int64
	var q question
	rows, _ := results.Query()
	if _, err := pgx.ForEachRow(rows, []any{&id, &q.inputType, &q.linkField}, func() error {
		copied := q
		copied.options = map[string]int64{}
		questions[id] = &copied
		return nil
	}); err != nil {
		return nil, err
	}

	var value string
	var optionID int64
	rows, _ = results.Query()
	if _, err := pgx.ForEachRow(rows, []any{&id, &value, &optionID}, func() error {
		if _, dup := questions[id].options[value]; dup {
			questions[id].options[value] = -1 // ambiguous value: Django raises, so defer to it
		} else {
			questions[id].options[value] = optionID
		}
		return nil
	}); err != nil {
		return nil, err
	}
	return questions, nil
}

// validateAnswers accepts only input Django would accept on the happy path, and returns the
// option ids for each answer. Anything else is deferred so Django produces its exact errors.
func validateAnswers(answers []answerInput, questions map[int64]*question) ([][]int64, error) {
	optionIDs := make([][]int64, len(answers))
	for i, a := range answers {
		q, found := questions[*a.Question]
		if !found || q.inputType == "upload" || a.FileValue != nil {
			return nil, errDeferToDjango
		}
		if q.linkField != nil {
			if _, supported := linkedProfileColumns[*q.linkField]; !supported {
				return nil, errDeferToDjango
			}
		}
		if !isNullOr[string](a.TextValue) || !isNullOr[int64](a.NumberValue) ||
			!isNullOr[bool](a.BooleanValue) || !isNullOr[string](a.OtherOptionValue) {
			return nil, errDeferToDjango
		}
		if !isNull(a.TextValue) && !isNull(a.NumberValue) {
			return nil, errDeferToDjango // violates pollanswer_text_or_number_or_option_set
		}
		if a.OptionsValue != nil {
			for _, v := range *a.OptionsValue {
				id, ok := q.options[v]
				if !ok || id < 0 {
					return nil, errDeferToDjango
				}
				optionIDs[i] = append(optionIDs[i], id)
			}
		}
	}
	return optionIDs, nil
}

// isNullOr reports whether a raw JSON value is absent, null, or decodes as T.
func isNullOr[T any](raw *json.RawMessage) bool {
	if isNull(raw) {
		return true
	}
	var v T
	return json.Unmarshal(*raw, &v) == nil
}

func isNull(raw *json.RawMessage) bool {
	return raw == nil || string(*raw) == "null"
}

func rawValue(raw *json.RawMessage) any {
	if isNull(raw) {
		return nil
	}
	var v any
	json.Unmarshal(*raw, &v)
	if f, ok := v.(float64); ok {
		return int64(f)
	}
	return v
}

// upsertAnswer mirrors PollQuestionAnswer.objects.update_or_create(submission, question, defaults=...).
func upsertAnswer(ctx context.Context, tx pgx.Tx, submissionID int64, a answerInput, optionIDs []int64) error {
	columns := []string{}
	values := []any{}
	for _, f := range []struct {
		column string
		raw    *json.RawMessage
	}{
		{"text_value", a.TextValue}, {"number_value", a.NumberValue},
		{"boolean_value", a.BooleanValue}, {"other_option_value", a.OtherOptionValue},
	} {
		if f.raw != nil {
			columns = append(columns, f.column)
			values = append(values, rawValue(f.raw))
		}
	}

	var answerID int64
	err := tx.QueryRow(ctx,
		`SELECT id FROM polls_pollquestionanswer WHERE submission_id = $1 AND question_id = $2 FOR UPDATE`,
		submissionID, *a.Question,
	).Scan(&answerID)

	switch {
	case errors.Is(err, pgx.ErrNoRows):
		cols := append([]string{"created_at", "updated_at", "submission_id", "question_id"}, columns...)
		args := append([]any{submissionID, *a.Question}, values...)
		placeholders := []string{"now()", "now()"}
		for i := range args {
			placeholders = append(placeholders, fmt.Sprintf("$%d", i+1))
		}
		err = tx.QueryRow(ctx, fmt.Sprintf(`INSERT INTO polls_pollquestionanswer (%s) VALUES (%s) RETURNING id`,
			strings.Join(cols, ", "), strings.Join(placeholders, ", ")), args...).Scan(&answerID)
	case err == nil:
		sets := []string{"updated_at = now()"}
		for i, c := range columns {
			sets = append(sets, fmt.Sprintf("%s = $%d", c, i+2))
		}
		_, err = tx.Exec(ctx, fmt.Sprintf(`UPDATE polls_pollquestionanswer SET %s WHERE id = $1`,
			strings.Join(sets, ", ")), append([]any{answerID}, values...)...)
	}
	if err != nil {
		return err
	}

	// answer.options_value.set(options), only when options were sent and non-empty
	if len(optionIDs) == 0 {
		return nil
	}
	if _, err := tx.Exec(ctx,
		`DELETE FROM polls_pollquestionanswer_options_value WHERE pollquestionanswer_id = $1 AND NOT (choiceinputoption_id = ANY($2))`,
		answerID, optionIDs,
	); err != nil {
		return err
	}
	_, err = tx.Exec(ctx,
		`INSERT INTO polls_pollquestionanswer_options_value (pollquestionanswer_id, choiceinputoption_id)
		 SELECT $1, o FROM unnest($2::bigint[]) AS o
		 WHERE NOT EXISTS (SELECT 1 FROM polls_pollquestionanswer_options_value
		                   WHERE pollquestionanswer_id = $1 AND choiceinputoption_id = o)`,
		answerID, optionIDs,
	)
	return err
}

// updateLinkedProfile mirrors PollService._update_user_fields_from_submission: for every answer
// linked to a profile field, set it to the answer's value (or keep it) and save the profile.
func updateLinkedProfile(ctx context.Context, tx pgx.Tx, submissionID, userID int64) error {
	rows, err := tx.Query(ctx, `
		SELECT q.link_user_field,
		       COALESCE(a.text_value, a.number_value::text,
		                (SELECT string_agg(o.value, ', ' ORDER BY o."order", o.id DESC)
		                 FROM polls_pollquestionanswer_options_value av
		                 JOIN polls_choiceinputoption o ON o.id = av.choiceinputoption_id
		                 WHERE av.pollquestionanswer_id = a.id),
		                CASE WHEN a.boolean_value THEN 'True' WHEN NOT a.boolean_value THEN NULL END)
		FROM polls_pollquestionanswer a JOIN polls_pollquestion q ON q.id = a.question_id
		WHERE a.submission_id = $1 AND q.link_user_field IS NOT NULL`, submissionID)
	if err != nil {
		return err
	}
	type update struct {
		column string
		value  *string
	}
	var updates []update
	var field string
	var value *string
	if _, err := pgx.ForEachRow(rows, []any{&field, &value}, func() error {
		updates = append(updates, update{linkedProfileColumns[field], value})
		return nil
	}); err != nil {
		return err
	}

	for _, u := range updates {
		// "answer.value or profile.<field>": empty values keep the existing one
		_, err := tx.Exec(ctx, fmt.Sprintf(
			`UPDATE users_profile SET %[1]s = COALESCE(NULLIF($2, ''), %[1]s), updated_at = now() WHERE user_id = $1`,
			u.column), userID, u.value)
		if err != nil {
			return err
		}
	}
	return nil
}

// notifyListeners stands in for the post_save signal's Channels broadcast. With no one watching
// the results page the group is empty, which is the load test case; broadcasting to live
// viewers would need the channels_redis message format and isn't implemented here.
func (s *server) notifyListeners(ctx context.Context, pollID int64) {
	ctx, cancel := context.WithTimeout(ctx, time.Second)
	defer cancel()
	key := fmt.Sprintf("asgi:group:poll_%d", pollID)
	if n, err := s.redis.ZCard(ctx, key).Result(); err == nil && n > 0 {
		fmt.Printf("warning: %d live viewers on poll %d were not notified\n", n, pollID)
	}
}

func (s *server) loadSubmission(ctx context.Context, r *http.Request, submissionID int64) (*submissionJSON, error) {
	loc := requestLocation(r)
	sub := &submissionJSON{ID: submissionID, Answers: []answerJSON{}}
	profile := &profileJSON{}
	sub.User.Profile = profile

	batch := &pgx.Batch{}
	batch.Queue(`SELECT s.poll_id, s.error, s.created_at, s.updated_at, u.id, u.email, `+profileColumns+`,
			EXISTS (SELECT 1 FROM users_verifiedemail v WHERE v.user_id = u.id AND v.email = p.school_email)
		FROM polls_pollsubmission s JOIN users_user u ON u.id = s.user_id
		LEFT JOIN users_profile p ON p.user_id = u.id WHERE s.id = $1`, submissionID)
	batch.Queue(`SELECT a.id, a.created_at, a.updated_at, a.text_value, a.number_value, a.boolean_value,
			a.other_option_value, a.error, a.question_id, a.file_value_id,
			COALESCE((SELECT array_agg(o.value ORDER BY o."order", o.id DESC)
			          FROM polls_pollquestionanswer_options_value av
			          JOIN polls_choiceinputoption o ON o.id = av.choiceinputoption_id
			          WHERE av.pollquestionanswer_id = a.id), '{}')
		FROM polls_pollquestionanswer a WHERE a.submission_id = $1 ORDER BY a.id`, submissionID) // Django's order is unspecified here
	results := s.db.SendBatch(ctx, batch)
	defer results.Close()

	var subError *string
	var createdAt, updatedAt time.Time
	var hasProfile bool
	var image *string
	dest := append([]any{&sub.Poll, &subError, &createdAt, &updatedAt, &sub.User.ID, &sub.User.Email},
		scanProfile(&hasProfile, profile, &image)...)
	dest = append(dest, &profile.IsSchoolEmailVerified)
	if err := results.QueryRow().Scan(dest...); err != nil {
		return nil, err
	}
	profile.Image = mediaURL(r, image)
	sub.CreatedAt, sub.UpdatedAt = isoTime(createdAt, loc), isoTime(updatedAt, loc)

	sub.IsValid = subError == nil
	var a answerJSON
	var aCreated, aUpdated time.Time
	rows, _ := results.Query()
	if _, err := pgx.ForEachRow(rows, []any{&a.ID, &aCreated, &aUpdated, &a.TextValue, &a.NumberValue,
		&a.BooleanValue, &a.OtherOptionValue, &a.Error, &a.Question, &a.FileValue, &a.OptionsValue}, func() error {
		a.CreatedAt, a.UpdatedAt = isoTime(aCreated, loc), isoTime(aUpdated, loc)
		a.IsValid = a.Error == nil
		sub.IsValid = sub.IsValid && a.IsValid
		sub.Answers = append(sub.Answers, a)
		return nil
	}); err != nil {
		return nil, err
	}
	return sub, nil
}
