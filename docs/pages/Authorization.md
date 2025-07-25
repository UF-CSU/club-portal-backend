# Authorization and Access Control

When making a request to a protected resource, this is what could happen:

1. 401 If user is not authenticated
2. 404 If user does not have access to the resource
3. 403 If user has access, but cannot perform specific action
4. 200 If user has access, and can perform action

> Reference: <https://medium.com/@joabi/access-control-its-not-just-about-unauthorized-and-forbidden-responses-2d45d5a514aa>
