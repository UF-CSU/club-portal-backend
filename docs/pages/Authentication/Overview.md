# Auth Overview

When authenticating with the API, there are two concepts to keep in mind: 1) how does the user authenticate, and 2) how does the frontend application (client) securely communicate with the API on the user's behalf.

In a nutshell, there are two ways a user can log into a system and authenticate with the API:

1. [Password authentication](./UserAuth.md#getting-a-token-via-password-authentication)
2. [OAuth](./UserAuth.md#getting-a-token-using-oauth)

Either of those methods will eventually create a token the client can use to interact with the API on the user's behalf. But what happens if a frontend application wants to display data to an anonymous user, ie the user is not logged in? That introduces the concept of an API Key. In summary, there are 2 ways a client application can securely communicate with a server:

1. [User Tokens](./UserAuth.md)
2. [API Keys](./ApiKeys.md)
