const baseUrl = "https://apiv2.curibio-test.com"; // TODO set .env for prod v. dev envs
let authToken = null;
/*
Expected message format:
{
    method: "POST", "GET", 
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
  let res = null;
  const url = new URL(endpoint, baseUrl);
  const request = new Request(url, {
    method: method,
    body: body,
  });

  // Attach auth token to header only if required
  if (authToken) {
    // add token to request headers
    const headers = new Headers();
    headers.append("Authorization", `Bearer ${authToken}`);
    request.headers = headers;

    try {
      return await fetch(request);
    } catch (e) {
      return { error: e };
    }
  } else {
    try {
      res = await fetch(request);
    } catch (e) {
      return { error: e };
    }

    if (!res.ok) return { error: res.status };

    const data = await res.json();
    // Capture the auth token here
    authToken = data.token;

    const newBody = JSON.stringify({
      success: data.success,
      message: data.message,
    });

    // Make a new reponse because clones are readonly
    return new Response(newBody, {
      status: res.status,
      statusText: res.statusText,
      headers: new Headers(Array.from(res.headers.entries())),
    });
  }
};
