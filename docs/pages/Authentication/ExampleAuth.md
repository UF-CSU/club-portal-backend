# Example Client Auth Code

The following code was adapted (simplified) from: <https://github.com/ufosc/Jukebox-Frontend/blob/main/src/network/NetworkBase.ts>.

It shows utility functions that could be used to interact with the api, user authentication, and demonstrates how the frontend might implement OAuth. This code is just for demonstration purposes and would need a few changes to work in a smooth development/production environment.

```ts
// src/AuthProvider.ts
import axios from 'axios'

const CURRENT_URL = `${window.location.protocol}//${window.location.host}`

/**
 * Handle Authentication Logic
 */
class AuthProvider {
  /**
   * Initiate standard auth flow.
   *
   * Sends a request to the server which returns a user
   * token. This token will be sent with each api request.
   */
  public async loginWithUsername(usernameOrEmail: string, password: string) {
    const url = 'http://localhost:8000/api/v1/user/token/'

    const res = await axios.post(url, {
      method: 'POST',
      data: { username: usernameOrEmail, password },
      headers: { 'Content-Type': 'application/json' }
    })

    if (!res.success) {
      console.error('There was an issue getting the auth token:', res)
      return
    }
    localStorage.setItem('clubportal-token', res.data.token)

    return
  }

  /**
   * Initiate the oauth flow.
   *
   * Creates a new dynamic form, creates hidden fields for each of the
   * required fields to submit to the server, and submits the form to
   * the server. This allows the post request to redirect the user
   * to the server, which will redirect to the consent screen.
   */
  public async loginWithOauth(returnPath?: string) {
    const form = document.createElement('form')
    form.method = 'POST'
    form.action =
      'http://localhost:8000/api/oauth/browser/v1/auth/provider/redirect'

    const data = {
      provider: 'google',
      callback_url: CURRENT_URL + (returnPath ?? '/'),
      process: 'login'
    }

    for (const [key, value] of Object.entries(data)) {
      const input = document.createElement('input')
      input.type = 'hidden'
      input.name = key
      input.value = value
      form.appendChild(input)
    }
    document.body.appendChild(form)

    form.submit()
  }

  /**
   * Handle return request from oauth.
   *
   * The server returns with a new session id stored as a cookie.
   * This session id allows us to authenticate with the server
   * and obtain a user token to use with the REST API.
   */
  public async handleOauthReturn() {
    const url = 'http://localhost:8000/api/v1/user/token/'

    const res = await axios.get(url, {
      withCredentials: true, // Allows session cookie to be sent with request
      headers: { 'Content-Type': 'application/json' }
    })

    if (!res.success) {
      console.error('There was an issue getting the auth token:', res)
      return
    }

    localStorage.setItem('clubportal-token', res.data.token)
  }

  /**
   * Example API Request
   *
   * Demonstrates how to send an API request using the token
   * obtained from authentication.
   */
  public async getResources() {
    const url = 'http://localhost:8000/api/v1/resource/resources/'
    const token = localStorage.getItem('clubportal-token')

    const res = await axios.get(url, {
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Token ${token}`
      }
    })

    if (!res.success) {
      console.error('There was an error getting resource:', res)
      return
    }

    return res.data
  }
}
```
