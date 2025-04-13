# User Authentication

In order to make requests to private api routes, you will need to supply a "token" in the Authorization header of the request. The token must be preceded by the word `Token`. In Postman it would look like this for a token value `somelongtoken123`:

_Headers_

| Key           | Value                  |
| ------------- | ---------------------- |
| Authorization | Token somelongtoken123 |

The following sections will describe different ways of obtaining and using this token.

## Getting a token via password authentication

The easiest way to get a token for testing is to use the api docs and submit login information for the `POST /api/v1/user/token/` route: <http://localhost:8000/api/v1/docs/#/user/user_token_create>. You can use the same credentials you use for the admin dashboard; by default they are:

- Username: <admin@example.com>
- Password: changeme

## Getting a token using OAuth

### Setting up OAuth for dev

#### Google

You will need to setup an OAuth consent screen in Google Cloud. Use these docs to learn more:

- <https://developers.google.com/workspace/guides/configure-oauth-consent>
- <https://dev.to/odhiambo/integrate-google-oauth2-social-authentication-into-your-django-web-app-1bk5>

Once you have the consent screen setup, set these environment variables:

```properties
GOOGLE_CLIENT_ID=""
GOOGLE_CLIENT_SECRET=""
```

#### GitHub

Steps to create a GitHub application

1. Create a new application at <https://github.com/settings/applications/new>.
2. Specify callback URL as <http://localhost:8000/oauth/github/login/callback/>.
3. Don't select Enable Device Flow.

Once you have the GitHub app setup, get the client id and secret and add them to your .env file:

```properties
GITHUB_CLIENT_ID=""
GITHUB_CLIENT_SECRET=""
```

### Testing OAuth

You can test out all of the 3rd party apps available by going to this page: <http://localhost:8000/oauth/3rdparty/>. Clicking on each link will allow you to connect an external account with that service.

### OAuth Api Flow

#### From a user's perspective

1. Starting on club portal, user clicks button to login and/or sign up with service
2. User is redirected to service's consent page
3. User accepts consent page
4. User is redirected back to club portal and is authenticated

#### From a developer's perspective

The terms **CLIENT** represent the front end application, **SERVER** represents the backend application, and **PROVIDER** represents the OAuth provider (like Google, GitHub, etc).

1. **CLIENT**: User clicks oauth button
2. **CLIENT**: Create temporary form element using JS, and add fields as text/hidden inputs: provider, callback_url, process. Here is an example:

   ```json
   {
     "provider": "google",
     "callback_url": "https://ufclubs.org/oauth-return/",
     "process": "login"
   }
   ```

3. **CLIENT**: Submit form to `/api/oauth/browser/v1/auth/provider/redirect`
4. **SERVER**: Server responds with a redirect to the oauth service's consent screen, client follows redirect due to form submission
5. **PROVIDER**: Redirect lands on consent screen, user accepts consent
6. **PROVIDER**: User is redirected back to server with state identifiers
7. **SERVER**: Server uses state identifiers to see what user has returned, creates auth session
8. **SERVER**: User is redirected back to original url specified in `callback_url` field from client with cookie storing session id
9. **CLIENT**: User returns to frontend, client uses the session cookie to request an API token from the server
10. **SERVER**: Using session cookie as authentication, creates an API token for the user, gives to client in response
11. **CLIENT**: Stores the token for all future API requests
12. **CLIENT**: Redirect user to final location (home page, etc)

## Using the token in development

### Using the token with Swagger

To use the token with the api docs created by swagger (at `/api/docs/`), scroll to the top of the page and click on the "Authorize" button. Under `tokenAuth`, write "Token somelongtoken123", replace "somelongtoken123" with the token value. Then click "Authorize".

The problem with this method is the token will disappear when the page refreshes. To fix this, you can instead use a browser extension to automatically insert the `Authorization` header on each request made by Swagger.

#### Header injections and Swagger

Header injection browser extensions:

- [ModHeader](https://chromewebstore.google.com/detail/modheader-modify-http-hea/idgpnmonknjnojddfkpgkljpfnnfcklj?hl=en&pli=1): Chrome
- [Requestly](https://requestly.com/blog/modify-headers-in-https-requests-and-responses-in-chrome-firefox-safari/): Chrome, Safari
- [Modify Header Value](https://addons.mozilla.org/en-US/firefox/addon/modify-header-value/): Firefox
- [simple-modify-headers](https://addons.mozilla.org/en-US/firefox/addon/simple-modify-header/): Firefox

Once you have the preferred extension installed, add the `Authorization` header, and make sure to use the same syntax for the token value as before.

Make sure to filter which requests use the new `Authorization` header, otherwise some websites may not work as expected. In ModHeader you can filter by request origins (localhost:8000), and/or for certain tabs. The same is probably try for the other extensions.

### Using the token with Postman

If you are testing the apis in postman, you can optionally get the token through postman as well using the same api route as described in [Getting the token](#getting-a-token-via-password-authentication).

Once you have the token, under the url input bar, go to Headers and add the following:

- Key: `Authorization`
- Value: `Token somelongtoken123`

And replace _somelongtoken123_ with the value of the token.
