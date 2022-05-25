const baseUrl = 'https://apiv2.curibio-test.com'; // TODO set .env for prod v. dev envs
let authToken = null;
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

  const request = new Request(url, {
    method: method,
    cache: 'default',
    headers: {
      //   'Access-Control-Allow-Origin': '*',
      'Content-Type': 'application/json',
    },
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
    console.log('LUCI', res);
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
