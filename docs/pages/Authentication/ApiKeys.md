# Client Access with API Keys

Unlike a user Token, an API Key is not attached to a single user (per-say), but instead is meant to authorize an application access to private resources without requiring a user to log in.

An example is this:

> CSU wants to display club information on their public site, but this information should not be publicly available via the REST API; an implementation of this could be a "members" page listing club members, for instance. CSU can achieve this by creating an API Key and giving it permissions to view their club info, and passing the key's secret in requests to the server.

Let's dive into that a bit more...

## Getting an API Key

A club admin can obtain an api key by making a `POST` request to `/api/v1/club/clubs/{club_id}/apikeys/`, like the following:

**Request**

```json
{
  "name": "Public Site Key",
  "description": "API Key to use for the CSU public website.",
  "permissions": [
    "clubs.view_club",
    "clubs.view_clubmembership",
    "clubs.view_event"
  ]
}
```

**Response**

```json
{
  "id": 0,
  "club_id": 0,
  "name": "Public Site Key",
  "description": "API Key to use for the CSU public website.",
  "permissions": [
    "clubs.view_club",
    "clubs.view_clubmembership",
    "clubs.view_event"
  ],
  "secret": "abc123def456"
}
```

In the example discussed earlier, this would allow CSU's public website to view information about their club, memberships, and events only. All other clubs and objects would be forbidden.

The key's secret is only returned in the response from the `POST` request, and cannot be retrieved afterwards. So it is important to save this information immediately. If the key's secret is lost or forgotten, a new key must be created. A club can have unlimited api keys (as of right now).

## Using an API Key

To continue the previous example, say we got a secret returned from our api key with the value `abc123def456`. How does the frontend use this?

A frontend client would simply inject this secret into the `Authorization` header like they would a normal [user token](./UserAuth.md):

```properties
Authorization: Token abc123def456
```

Everything else should work exactly the same as user tokens.
