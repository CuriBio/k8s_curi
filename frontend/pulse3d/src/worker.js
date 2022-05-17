let authToken = null;
const baseUrl = 'https://apiv2.curibio-test.com'; // TODO set .env for prod v. dev envs

/*
Expected message format:
{
    method: "POST"/"GET", 
    endpoint: "/users/login",
    body: {}
}
*/

// message handler
self.onmessage = async ({ data }) => {
  if (data.method) {
    const res = await handleRequest(data);
    postMessage(res);
  }
  return;
};

const handleRequest = async ({ method, endpoint, body }) => {
  const url = new URL(endpoint, baseUrl);
  //   const isSameOrigin = self.location.origin === url.origin;
  //   const isProtectedUrl = isSameOrigin && protectedUrls.includes(url.pathname);
  //   const isAuthUrl = isSameOrigin && authUrls.includes(url.pathname);
  const request = new Request(url, {
    method: method,
    cache: 'default',
    body: body,
  });

  // Attach auth token to header only if required
  if (authToken) {
    // add token to request headers
    const headers = new Headers();
    headers.append('Authorization', `Bearer ${authToken}`);
    request.headers = headers;

    return fetch(request);
  } else {
    const res = await fetch(request);

    if (!res.ok) {
      const message = `An error has occured: ${response.status}`;
      return new Error(message);
    }

    const data = await res.json();

    // Capture the auth token here
    authToken = data.token;

    const newBody = JSON.stringify({
      success: data.success,
      message: data.message,
    });

    // Make a new reponse because clones are readonly
    return new Response(newBody, {
      status: response.status,
      statusText: response.statusText,
      headers: new Headers(Array.from(response.headers.entries())),
    });
  }
};
