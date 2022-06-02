import axios from "axios";

// const sample = (function () {
//   let _privateVariable = 'This is private';

//   return {
//     setPrivateVariable: (value) => {
//       _privateVariable = value;
//     },
//     getPrivateVariable: () => {
//       return _privateVariable;
//     },
//   };
// })();

// TODO add .env for prod v. test url
const domain = "curibio-test"; // MODIFY URL until decided how it's handled

const getUrl = (subdomain) => {
  return `http://${subdomain}.${domain}.com/`;
};
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
onmessage = async ({ data }) => {
  console.log(authToken, data);
  if (data.method) {
    const res = dispatchRequest(data);
    // add request type back for caller to differentiate request type
    const parsed_res = JSON.parse(JSON.stringify(res));
    parsed_res.type = data.type;

    postMessage(parsed_res); // errors if response isn't parsed first
  }
};

const dispatchRequest = async (data) => {
  switch (data.type) {
    case "login":
      return await handleAuthRequest(data);
    case "presignedUrl":
      return await handlePresignedRequest(data);
    default:
      return await handleGenericRequest(data);
  }
};

const handleGenericRequest = async ({ method, subdomain, endpoint, body, type }) => {
  const url = `${getUrl(subdomain)}${endpoint}`;
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
  const url = `${getUrl("apiv2")}${endpoint}`;

  let res = null;
  try {
    res = await axios.post(url, body);
  } catch (e) {
    return { error: e.response };
  }

  authToken = res.data.access.token;
  // Capture the auth token here
  // await sample.setPrivateVariable(res.data.access.token);
  // return 200 status code
  return { status: 200 };
};

const handlePresignedRequest = async ({ presignedUrl }) => {
  const reqInstance = axios.create({
    data: body,
  });

  try {
    return await reqInstance[method](presignedUrl);
  } catch (e) {
    return { error: e.response };
  }
};
