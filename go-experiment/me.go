package main

import (
	"context"
	"net/http"
	"strings"
	"time"

	"github.com/jackc/pgx/v5"
)

// clubAdminPerms is clubs.defaults.CLUB_ADMIN_ROLE_PERMISSIONS. A membership is an admin when
// it is the owner, the user is a superuser, or its roles grant all of these.
var clubAdminPerms = strings.Split("analytics.add_link,analytics.add_qrcode,analytics.change_link,analytics.change_qrcode,analytics.delete_link,analytics.delete_qrcode,analytics.view_link,analytics.view_qrcode,clubs.add_clubapikey,clubs.add_clubfile,clubs.add_clubmembership,clubs.add_clubrole,clubs.add_team,clubs.add_teammembership,clubs.add_teamrole,clubs.change_club,clubs.change_clubapikey,clubs.change_clubfile,clubs.change_clubmembership,clubs.change_clubrole,clubs.change_team,clubs.change_teammembership,clubs.change_teamrole,clubs.delete_clubapikey,clubs.delete_clubfile,clubs.delete_clubmembership,clubs.delete_clubrole,clubs.delete_team,clubs.delete_teammembership,clubs.delete_teamrole,clubs.view_club,clubs.view_club_details,clubs.view_clubapikey,clubs.view_clubfile,clubs.view_clubmembership,clubs.view_clubphoto,clubs.view_clubrole,clubs.view_clubtag,clubs.view_team,clubs.view_teammembership,clubs.view_teamrole,events.add_event,events.add_recurringevent,events.change_event,events.change_recurringevent,events.delete_event,events.delete_recurringevent,events.view_event,events.view_event_analytics,events.view_event_details,events.view_private_event,events.view_recurringevent,polls.add_choiceinputoption,polls.add_poll,polls.add_pollfield,polls.change_choiceinputoption,polls.change_poll,polls.change_pollfield,polls.delete_choiceinputoption,polls.delete_poll,polls.delete_pollfield,polls.view_choiceinputoption,polls.view_poll_analytics,polls.view_pollfield,polls.view_pollsubmission,polls.view_private_poll", ",")

type profileJSON struct {
	IsSchoolEmailVerified bool    `json:"is_school_email_verified"`
	Image                 *string `json:"image"`
	Phone                 *string `json:"phone"`
	Name                  *string `json:"name"`
	Bio                   *string `json:"bio"`
	City                  *string `json:"city"`
	State                 *string `json:"state"`
	Country               *string `json:"country"`
	Birthday              *string `json:"birthday"`
	SchoolEmail           *string `json:"school_email"`
	Major                 *string `json:"major"`
	Minor                 *string `json:"minor"`
	College               *string `json:"college"`
	GraduationDate        *string `json:"graduation_date"`
}

type clubJSON struct {
	ID   int64  `json:"id"`
	Name string `json:"name"`
}

type socialJSON struct {
	ID         int64   `json:"id"`
	SocialType string  `json:"social_type"`
	URL        *string `json:"url"`
	Username   *string `json:"username"`
	Order      int     `json:"order"`
}

type meJSON struct {
	ID              int64        `json:"id"`
	CreatedAt       string       `json:"created_at"`
	UpdatedAt       string       `json:"updated_at"`
	Username        string       `json:"username"`
	Email           *string      `json:"email"`
	Clubs           []clubJSON   `json:"clubs"`
	Profile         *profileJSON `json:"profile"`
	Socials         []socialJSON `json:"socials"`
	IsOnboarded     bool         `json:"is_onboarded"`
	IsEmailVerified bool         `json:"is_email_verified"`
	CanAuthenticate bool         `json:"can_authenticate"`
	IsClubAdmin     *bool        `json:"is_club_admin"` // true or null, like User.is_club_admin
}

const profileColumns = `p.user_id IS NOT NULL, p.image, p.phone, p.name, p.bio, p.city, p.state, p.country,
	to_char(p.birthday, 'YYYY-MM-DD'), p.school_email, p.major, p.minor, p.college, p.graduation_date`

func scanProfile(hasProfile *bool, p *profileJSON, image **string) []any {
	return []any{hasProfile, image, &p.Phone, &p.Name, &p.Bio, &p.City, &p.State, &p.Country,
		&p.Birthday, &p.SchoolEmail, &p.Major, &p.Minor, &p.College, &p.GraduationDate}
}

func (s *server) handleMe(w http.ResponseWriter, r *http.Request) {
	ctx := r.Context()
	userID, ok := s.authUser(ctx, r)
	if !ok {
		s.proxy(w, r, nil)
		return
	}

	me, hasProfile, err := s.loadMe(ctx, r, userID)
	if err != nil {
		serverError(w, err)
		return
	}
	if !hasProfile {
		s.proxy(w, r, nil) // Django's behavior for users without a profile, whatever it is
		return
	}
	writeJSON(w, http.StatusOK, me)
}

func (s *server) loadMe(ctx context.Context, r *http.Request, userID int64) (*meJSON, bool, error) {
	loc := requestLocation(r)
	me := &meJSON{ID: userID, Clubs: []clubJSON{}, Socials: []socialJSON{}, Profile: &profileJSON{}}

	// One round trip for everything /me needs
	batch := &pgx.Batch{}
	batch.Queue(`SELECT u.created_at, u.updated_at, u.username, u.email, u.password, u.is_superuser, `+profileColumns+`
		FROM users_user u LEFT JOIN users_profile p ON p.user_id = u.id WHERE u.id = $1`, userID)
	// Same unordered membership query shape as Django's prefetch, so row order matches
	batch.Queue(`SELECT m.club_id, m.is_owner OR u.is_superuser OR (
			SELECT count(DISTINCT ct.app_label || '.' || p.codename)
			FROM clubs_clubmembership_roles mr
			JOIN clubs_clubrole_permissions rp ON rp.clubrole_id = mr.clubrole_id
			JOIN auth_permission p ON p.id = rp.permission_id
			JOIN django_content_type ct ON ct.id = p.content_type_id
			WHERE mr.clubmembership_id = m.id AND ct.app_label || '.' || p.codename = ANY($2)
		) = cardinality($2)
		FROM clubs_clubmembership m JOIN users_user u ON u.id = m.user_id WHERE m.user_id = $1`, userID, clubAdminPerms)
	batch.Queue(`SELECT c.id, c.name FROM clubs_club c WHERE c.id IN (SELECT club_id FROM clubs_clubmembership WHERE user_id = $1)`, userID)
	batch.Queue(`SELECT email FROM users_verifiedemail WHERE user_id = $1`, userID)
	batch.Queue(`SELECT id, social_type, url, username, "order" FROM users_socialprofile WHERE user_id = $1 ORDER BY "order", id`, userID)
	batch.Queue(`SELECT count(*) FROM socialaccount_socialaccount WHERE user_id = $1`, userID)

	results := s.db.SendBatch(ctx, batch)
	defer results.Close()

	var createdAt, updatedAt time.Time
	var password string
	var superuser, hasProfile bool
	var image *string
	dest := append([]any{&createdAt, &updatedAt, &me.Username, &me.Email, &password, &superuser},
		scanProfile(&hasProfile, me.Profile, &image)...)
	if err := results.QueryRow().Scan(dest...); err != nil {
		return nil, false, err
	}
	me.CreatedAt, me.UpdatedAt = simpleTime(createdAt, loc), simpleTime(updatedAt, loc)
	me.Profile.Image = mediaURL(r, image)

	// Memberships, in Django's order
	var clubOrder []int64
	var clubID int64
	var admin, anyAdmin bool
	rows, _ := results.Query()
	if _, err := pgx.ForEachRow(rows, []any{&clubID, &admin}, func() error {
		clubOrder = append(clubOrder, clubID)
		anyAdmin = anyAdmin || admin
		return nil
	}); err != nil {
		return nil, false, err
	}

	names := map[int64]string{}
	var name string
	rows, _ = results.Query()
	if _, err := pgx.ForEachRow(rows, []any{&clubID, &name}, func() error {
		names[clubID] = name
		return nil
	}); err != nil {
		return nil, false, err
	}
	for _, id := range clubOrder {
		me.Clubs = append(me.Clubs, clubJSON{ID: id, Name: names[id]})
	}

	var verified string
	rows, _ = results.Query()
	if _, err := pgx.ForEachRow(rows, []any{&verified}, func() error {
		if me.Email != nil && verified == *me.Email {
			me.IsEmailVerified = true
		}
		if me.Profile.SchoolEmail != nil && verified == *me.Profile.SchoolEmail {
			me.Profile.IsSchoolEmailVerified = true
		}
		return nil
	}); err != nil {
		return nil, false, err
	}

	var social socialJSON
	rows, _ = results.Query()
	if _, err := pgx.ForEachRow(rows, []any{&social.ID, &social.SocialType, &social.URL, &social.Username, &social.Order}, func() error {
		me.Socials = append(me.Socials, social)
		return nil
	}); err != nil {
		return nil, false, err
	}

	var socialAccounts int
	if err := results.QueryRow().Scan(&socialAccounts); err != nil {
		return nil, false, err
	}

	// Django: has_usable_password() is false for passwords starting with "!"
	me.CanAuthenticate = !strings.HasPrefix(password, "!") || socialAccounts > 0
	me.IsOnboarded = len(clubOrder) > 0 && hasProfile && me.Profile.Name != nil
	if anyAdmin {
		t := true
		me.IsClubAdmin = &t
	}
	return me, hasProfile, nil
}
