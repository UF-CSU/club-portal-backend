# Club Portal Authentication

- [Auth Flow](#auth-flow)
- [Auth for Local Dev Testing](#auth-for-local-dev-testing)
  - [Getting the token](#getting-the-token)
  - [Using the token with Swagger](#using-the-token-with-swagger)
    - [Header injections and Swagger](#header-injections-and-swagger)
  - [Using the token with Postman](#using-the-token-with-postman)
- [OAuth](#oauth)
  - [Setting up OAuth for dev](#setting-up-oauth-for-dev)
    - [Google](#google)
    - [GitHub](#github)

## Auth Flow

In order to make requests to private api routes, you will need to supply a "token" in the Authorization header of the request. The token must be preceded by the word `Token`. In Postman it would look like this for a token value `somelongtoken123`:

_Headers_

| Key           | Value                  |
| ------------- | ---------------------- |
| Authorization | Token somelongtoken123 |

## Auth for Local Dev Testing

### Getting the token

The easiest way to get a token for testing is to use the api docs and submit login information for the `POST /api/v1/user/token/` route: <http://localhost:8000/api/v1/docs/#/user/user_token_create>. You can use the same credentials you use for the admin dashboard; by default they are:

- Username: <admin@example.com>
- Password: changeme

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

If you are testing the apis in postman, you can optionally get the token through postman as well using the same api route as described in [Getting the token](#getting-the-token).

Once you have the token, under the url input bar, go to Headers and add the following:

- Key: `Authorization`
- Value: `Token somelongtoken123`

And replace _somelongtoken123_ with the value of the token.

## OAuth

### Setting up OAuth for dev

#### Google

You will need to setup an OAuth consent screen in Google Cloud. Use these docs to learn more:

- <https://developers.google.com/workspace/guides/configure-oauth-consent>
- <https://dev.to/odhiambo/integrate-google-oauth2-social-authentication-into-your-django-web-app-1bk5>

#### GitHub

Steps to create a GitHub application

1. Create a new application at <https://github.com/settings/applications/new>.
2. Specify callback URL as <http://localhost:8000/oauth/github/login/callback/>.
3. Copy Client ID into GITHUB_CLIENT_ID and Secret into GITHUB_CLIENT_SECRET in .env.
4. Don't select Enable Device Flow.
