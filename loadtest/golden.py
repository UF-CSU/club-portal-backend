"""
Compare API responses between two servers running on the same database.

Use it to prove a performance change didn't change any output: run the old code on one port
and the new code on another, then:

    python3 golden.py http://localhost:9201 http://localhost:9202 tokens.json [poll_id]
"""

import json
import sys
import urllib.error
import urllib.request

old_base, new_base, tokens_path = sys.argv[1:4]
poll_id = sys.argv[4] if len(sys.argv) > 4 else None
tokens = json.load(open(tokens_path))

# A spread of users: first ones are club admins in the seed, the rest regular members
users = tokens[:3] + tokens[100:103] + tokens[-3:]

paths = [
    ("/api/v1/club/club-previews/?is_csu_partner=true", False),
    ("/api/v1/event/event-previews/?start_date=2026-01-01&end_date=2026-12-31", False),
    ("/api/v1/event/events/?include_public=true&start_date=2026-01-01&end_date=2026-12-31", True),
    ("/api/v1/user/me/", True),
    ("/api/v1/club/club-memberships/", True),
]
if poll_id:
    paths += [(f"/api/v1/poll/poll-previews/{poll_id}/", False)]


def fetch(base, path, token):
    headers = {"Authorization": f"Token {token}"} if token else {}
    req = urllib.request.Request(base + path, headers=headers)
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:200]


def diff(a, b, at=""):
    """Yield the paths where two JSON values differ."""
    if type(a) is not type(b):
        yield f"{at}: {type(a).__name__} != {type(b).__name__}"
    elif isinstance(a, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a or k not in b:
                yield f"{at}.{k}: missing on {'old' if k not in a else 'new'}"
            else:
                yield from diff(a[k], b[k], f"{at}.{k}")
    elif isinstance(a, list):
        if len(a) != len(b):
            yield f"{at}: length {len(a)} != {len(b)}"
        for i, (x, y) in enumerate(zip(a, b)):
            yield from diff(x, y, f"{at}[{i}]")
    elif a != b:
        yield f"{at}: {str(a)[:60]!r} != {str(b)[:60]!r}"


failures = 0
checks = 0
for path, auth in paths:
    for user in users if auth else [None]:
        token = user["token"] if user else None
        old, new = fetch(old_base, path, token), fetch(new_base, path, token)
        checks += 1
        problems = [f"status {old[0]} != {new[0]}"] if old[0] != new[0] else list(diff(old[1], new[1]))
        if problems:
            failures += 1
            who = f" as user {user['user_id']}" if user else ""
            print(f"DIFF {path}{who}")
            for p in problems[:5]:
                print(f"     {p}")

print(f"{checks - failures}/{checks} responses identical")
sys.exit(1 if failures else 0)
