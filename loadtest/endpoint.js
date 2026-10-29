/**
 * Saturate a single endpoint to measure its throughput and CPU cost per request.
 *
 *   k6 run -e BASE_URL=http://host:9000 -e ENDPOINT=me -e VUS=32 -e DURATION=30s endpoint.js
 *   k6 run -e BASE_URL=http://host:9000 -e ENDPOINT=submit -e POLL_ID=123 endpoint.js
 *
 * ENDPOINT: me | submit. Submit uses a different user per request, starting at TOKEN_OFFSET.
 */
import http from 'k6/http';
import { check } from 'k6';
import { SharedArray } from 'k6/data';
import exec from 'k6/execution';

const BASE = (__ENV.BASE_URL || 'http://127.0.0.1:9000') + '/api/v1';
const ENDPOINT = __ENV.ENDPOINT || 'me';
const POLL_ID = __ENV.POLL_ID;
const OFFSET = Number(__ENV.TOKEN_OFFSET || 0);
const tokens = new SharedArray('tokens', () => JSON.parse(open(__ENV.TOKENS || './tokens.json')));

const CHOICES = (__ENV.CHOICES || '').split(';').filter(Boolean).map((c) => {
  const [question, values] = c.split('=');
  return { question: Number(question), values: values.split('|') };
});

export const options = {
  scenarios: {
    load: { executor: 'constant-vus', vus: Number(__ENV.VUS || 32), duration: __ENV.DURATION || '30s' },
  },
  summaryTrendStats: ['avg', 'med', 'p(95)', 'p(99)', 'max'],
};

export default function () {
  if (ENDPOINT === 'me') {
    const user = tokens[Math.floor(Math.random() * tokens.length)];
    const r = http.get(`${BASE}/user/me/`, { headers: { Authorization: `Token ${user.token}` } });
    check(r, { 'me 200': (x) => x.status === 200 });
    return;
  }

  const user = tokens[(OFFSET + exec.scenario.iterationInTest) % tokens.length];
  const answers = [
    { question: Number(__ENV.EMAIL_Q), text_value: user.email },
    { question: Number(__ENV.NAME_Q), text_value: `Student ${user.user_id}` },
    ...CHOICES.map((c) => ({ question: c.question, options_value: [c.values[Math.floor(Math.random() * c.values.length)]] })),
  ];
  const r = http.post(`${BASE}/poll/polls/${POLL_ID}/submissions/`, JSON.stringify({ answers }), {
    headers: { Authorization: `Token ${user.token}`, 'Content-Type': 'application/json' },
  });
  check(r, { 'submit 201': (x) => x.status === 201 });
}
