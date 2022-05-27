import axios from 'axios';

// TODO add .env for prod v. test url
const baseUrl = 'http://localhost:8000'; // MODIFY URL until decided how it's handled
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

  const reqInstance = axios.create({
    headers: {
      Authorization: `Bearer ${authToken}`,
    },
  });

  try {
    return await reqInstance[method](url, body);
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
  authToken = await res.data.access.token;

  // return 200 status code
  return { status: res.status };
};
