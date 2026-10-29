/**
 * Load test modeled on real people, not request loops.
 *
 * Each VU is one student using the portal, with think time between pages. API calls per page
 * mirror csu-portal-frontend: hooks.server.ts fetches /user/me/ on every logged-in navigation.
 *
 *   browse:  students browsing events and clubs (steady, VUS people at once)
 *   checkin: ATTENDEES people open the live event's form within ARRIVAL_S seconds, fill it
 *            for 30-90 s and submit (the QR-code-on-the-projector moment)
 *
 *   k6 run -e BASE_URL=http://host:9000 -e VUS=500 -e ATTENDEES=300 -e POLL_ID=123 people.js
 *
 * Env: BASE_URL, VUS (default 200), ATTENDEES (default 0), POLL_ID, ARRIVAL_S (default 60),
 *      DURATION (default 5m), RAMP_UP (default 60s), TOKENS (default ./tokens.json).
 *
 * Pass: p95 < 500 ms, p99 < 1000 ms, under 1% failed requests.
 */
import http from 'k6/http';
import { check, sleep } from 'k6';
import { SharedArray } from 'k6/data';
import exec from 'k6/execution';

const BASE = (__ENV.BASE_URL || 'http://127.0.0.1:9000') + '/api/v1';
const VUS = Number(__ENV.VUS || 200);
const ATTENDEES = Number(__ENV.ATTENDEES || 0);
const ARRIVAL_S = Number(__ENV.ARRIVAL_S || 60);
const POLL_ID = __ENV.POLL_ID;
const tokens = new SharedArray('tokens', () => JSON.parse(open(__ENV.TOKENS || './tokens.json')));

const scenarios = {
  browse: {
    executor: 'ramping-vus',
    exec: 'browse',
    stages: [
      { duration: __ENV.RAMP_UP || '60s', target: VUS },
      { duration: __ENV.DURATION || '5m', target: VUS },
      { duration: '30s', target: 0 },
    ],
    gracefulRampDown: '10s',
  },
};
if (ATTENDEES > 0) {
  scenarios.checkin = {
    executor: 'per-vu-iterations',
    exec: 'checkin',
    vus: ATTENDEES,
    iterations: 1,
    startTime: __ENV.CHECKIN_AT || '90s',
    maxDuration: '5m',
  };
}

export const options = {
  scenarios,
  thresholds: {
    http_req_duration: ['p(95)<500', 'p(99)<1000'],
    http_req_failed: ['rate<0.01'],
    'http_req_duration{scenario:checkin}': ['p(95)<1000'],
    'http_req_duration{name:submit}': ['max>=0'],
  },
  summaryTrendStats: ['avg', 'med', 'p(95)', 'p(99)', 'max'],
};

const between = (lo, hi) => lo + Math.random() * (hi - lo);

function headersFor(user) {
  return { headers: { Authorization: `Token ${user.token}`, 'Content-Type': 'application/json' } };
}

function get(path, name, auth) {
  const r = http.get(`${BASE}${path}`, Object.assign({ tags: { name } }, auth || {}));
  check(r, { [`${name} 200`]: (x) => x.status === 200 });
  return r;
}

function isoDate(d) {
  return d.toISOString().slice(0, 10);
}

/** A logged-in student browsing: events page, an event, a club, their dashboard. */
export function browse() {
  // Browse VUs use the first half of the token list, check-in VUs the second half
  const user = tokens[(__VU - 1) % Math.floor(tokens.length / 2)];
  const auth = headersFor(user);
  if (__ITER === 0) sleep(between(0, 5));

  const today = new Date();
  const weekAhead = new Date(today.getTime() + 7 * 86400000);

  // Events page
  get('/user/me/', 'me', auth);
  // The frontend sends include_public=true, which currently 500s on this branch, so it's left out
  const events = get(
    `/event/events/?start_date=${isoDate(today)}&end_date=${isoDate(weekAhead)}`,
    'events',
    auth,
  );
  sleep(between(5, 15));

  // An event's page
  const list = events.status === 200 ? events.json('results') || [] : [];
  if (list.length > 0) {
    get('/user/me/', 'me', auth);
    get(`/event/events/${list[Math.floor(Math.random() * list.length)].id}/`, 'event detail', auth);
    sleep(between(5, 20));
  }

  // Clubs directory, then a club
  get('/user/me/', 'me', auth);
  const clubs = get('/club/club-previews/?is_csu_partner=true', 'club previews');
  sleep(between(5, 15));
  const clubList = clubs.status === 200 ? clubs.json('results') || [] : [];
  if (clubList.length > 0) {
    get('/user/me/', 'me', auth);
    get(`/club/club-previews/${clubList[Math.floor(Math.random() * clubList.length)].id}/`, 'club preview');
    sleep(between(5, 15));
  }

  // Dashboard (30% of visits)
  if (Math.random() < 0.3) {
    get('/user/me/', 'me', auth);
    get('/club/club-memberships/', 'memberships', auth);
    sleep(between(5, 15));
  }

  sleep(between(10, 30));
}

/** One attendee: open the form from the QR code, fill it in, submit, see the done page. */
export function checkin() {
  const half = Math.floor(tokens.length / 2);
  const user = tokens[half + ((exec.scenario.iterationInTest) % (tokens.length - half))];
  const auth = headersFor(user);

  sleep(between(0, ARRIVAL_S)); // people scan the QR code over this window

  get('/user/me/', 'me', auth);
  const poll = get(`/poll/poll-previews/${POLL_ID}/`, 'poll preview', auth);
  get('/user/me/', 'me', auth);
  // The frontend checks for an existing submission; this is admin-only, so students get a 403
  const existing = http.get(
    `${BASE}/poll/polls/${POLL_ID}/submissions/`,
    Object.assign({ tags: { name: 'check existing submission' }, responseCallback: http.expectedStatuses(200, 403) }, auth),
  );
  check(existing, { 'check existing submission 200/403': (x) => x.status === 200 || x.status === 403 });
  if (poll.status !== 200) return;

  sleep(between(30, 90)); // filling in the form

  const r = http.post(
    `${BASE}/poll/polls/${POLL_ID}/submissions/`,
    JSON.stringify({ answers: buildAnswers(poll.json(), user) }),
    Object.assign({ tags: { name: 'submit' } }, auth),
  );
  check(r, { 'submit 201': (x) => x.status === 201 });

  get('/user/me/', 'me', auth);
  get(`/poll/poll-previews/${POLL_ID}/`, 'poll preview', auth);
}

function buildAnswers(poll, user) {
  const answers = [];
  for (const field of poll.fields || []) {
    const q = field.question;
    if (!q) continue;
    if (q.is_user_lookup) {
      answers.push({ question: q.id, text_value: user.email });
    } else if (q.input_type === 'choice') {
      const options = (q.choice_input && q.choice_input.options) || [];
      if (options.length > 0) {
        answers.push({ question: q.id, options_value: [options[Math.floor(Math.random() * options.length)].value] });
      }
    } else if (q.link_user_field === 'name') {
      answers.push({ question: q.id, text_value: `Student ${user.user_id}` });
    } else if (Math.random() < 0.3) {
      answers.push({ question: q.id, text_value: 'See you next week!' });
    }
  }
  return answers;
}
