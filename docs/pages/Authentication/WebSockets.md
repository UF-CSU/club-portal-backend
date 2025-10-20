# WebSocket Authentication

In order to make requests to private WebSocket routes, you will need to get and supply a "ticket" in the subprotocol.

## Getting a ticket

For an authenticated user (see [User Authentication](./UserAuth.md)), a ticket can be received by making a request to
the `GET /api/v1/user/ticket/` route: <http://localhost:8000/api/v1/docs/#/user/user_ticket_retrieve>.

> Note: This ticket is one-time use and expires after 10 minutes.

## Supplying the ticket

When making the connection, you must specify two subprotocols (`Sec-WebSocket-Protocol`). The first subprotocol must be `Authorization`, and the second subprotocol must be your ticket received from the server.


```js
const ws = new WebSocket(WSS_URL, ["Authorization", <ticket>]);
```