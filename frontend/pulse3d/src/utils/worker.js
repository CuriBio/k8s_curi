import axios from 'axios';

const baseUrl = 'http://localhost:8000'; // TODO add .env for prod v. test url
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
    const res = authToken
      ? await handleGenericRequest(data)
      : await handleAuthRequest(data);

    postMessage(res);
  }
};

const handleGenericRequest = async ({ method, endpoint, body }) => {
  const url = `${baseUrl}${endpoint}`;

  // add token to request headers
  const headers = new Headers();
  headers.append('Authorization', `Bearer ${authToken}`);
  request.headers = headers;

  try {
    return await axios(method, url, headers, body);
  } catch (e) {
    return { error: e.response.status };
  }
};

const handleAuthRequest = async ({ endpoint, body }) => {
  let res = null;
  const url = `${baseUrl}${endpoint}`;

  try {
    res = await axios.post(url, body);
  } catch (e) {
    return { error: e.response.status };
  }

  // Capture the auth token here
  const { token, success, message } = await res.json();
  authToken = token;

  const newBody = JSON.stringify({
    success,
    message,
  });

  // Make a new reponse because clones are readonly
  return new Response(newBody, {
    status: res.status,
    statusText: res.statusText,
    headers: new Headers(Array.from(res.headers.entries())),
  });
};
