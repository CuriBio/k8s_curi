import axios from "axios";

// TODO add .env for prod v. test url
const baseUrl = "http://localhost:8000/"; // MODIFY URL until decided how it's handled
let authToken = null;
/*
Expected message format:
{
    method: "post", "get", 
    endpoint: "/users/login",
    body: {}
}
*/
// message handler
// TODO add a timeout to prevent hanging requests
onmessage = async ({ data }) => {
  if (data.method) {
    const res =
      data.type === "login"
        ? await handleAuthRequest(data)
        : await handleGenericRequest(data);

    // add request type back for caller to diffrentiate request type
    const parsed_res = JSON.parse(JSON.stringify(res));
    parsed_res.type = data.type;

    postMessage(parsed_res); // errors if response isn't parsed first
  }
};

const handleGenericRequest = async ({ method, endpoint, body, type }) => {
  const url = `${baseUrl}${endpoint}`;
  const reqInstance = axios.create({
    headers: {
      Authorization: `Bearer ${authToken}`,
    },
    data: body,
  });

  try {
    return await reqInstance[method](url, { params: body });
  } catch (e) {
    return { error: e.response };
  }
};

const handleAuthRequest = async ({ endpoint, body }) => {
  let res = null;
  const url = `http://localhost:8001/${endpoint}`;

  try {
    res = await axios.post(url, body);
  } catch (e) {
    return { error: e.response };
  }

  authToken = res.data.access.token;
  // return 200 status code
  return { status: 200 };
};
