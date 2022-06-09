import axios from "axios";
import SparkMD5 from "spark-md5";

const tokens = {
  access: null,
  refresh: null,
};

const setTokens = (responseData) => {
  tokens.access = responseData.access.token;
  tokens.refresh = responseData.refresh.token;
};
// TODO add .env for prod v. test url
const domain = "curibio-test"; // MODIFY URL until decided how it's handled

const getUrl = (endpoint) => {
  let subdomain = endpoint.includes("users") ? "apiv2" : "pulse3d";

  return `https://${subdomain}.${domain}.com/${endpoint}`;
};

const getAccessHeader = () => {
  console.log("getAccessHeader:", tokens);
  return { Authorization: `Bearer ${tokens.access}` };
};

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
  console.log("WW onmessage:", tokens, data);
  if (data.method || data.file) {
    const res = await dispatchRequest(data);
    console.log("res:", res);
    const parsed_res = JSON.parse(JSON.stringify(res));

    if (parsed_res.error) {
      parsed_res.error.type = data.type;
    } else {
      parsed_res.type = data.type;
    }

    postMessage(parsed_res); // errors if response isn't parsed firstå
  }
};

const dispatchRequest = async (data) => {
  if (data.file) {
    return await handleFileUpload(data);
  }
  data.url = getUrl(data.endpoint);
  if (data.url.includes("users/log")) {
    return await handleAuthRequest(data);
  } else {
    return await handleGenericRequest(data);
  }
};

const handleAuthRequest = async ({ url, body }) => {
  let res = null;
  try {
    res = await axios.post(url, body);
  } catch (e) {
    return { error: e.response };
  }

  setTokens(res.data);

  // return 200 status code
  return { status: 200 };
};

const requestWithRefresh = async (requestFn) => {
  const safeRequest = async () => {
    console.log("safeRequest", tokens);
    try {
      return await requestFn();
    } catch (e) {
      return e.response;
    }
  };

  let response = await safeRequest();

  if (response.status === 401) {
    // attempt to get new tokens
    const refreshResponse = await handleRefreshRequest();
    if (refreshResponse.error) {
      // if the refresh failed, no need to try request again, just return original failed response
      return { error: response };
    }
    // try again with new tokens
    response = await safeRequest();
  }

  return response;
};

const handleRefreshRequest = async () => {
  let res = null;
  try {
    res = await axios.post(
      getUrl("users/refresh"),
      // TODO look into ways to not pass an empty body
      {},
      { headers: { Authorization: `Bearer ${tokens.refresh}` } },
    );
  } catch (e) {
    return { error: e.response };
  }

  console.log("old tokens:", tokens);
  setTokens(res.data);
  console.log("new tokens:", tokens);

  return res;
};

const handleGenericRequest = async ({ url, method, body }) => {
  let requestFn = null;
  if (method === "get") {
    requestFn = async () => await axios.get(url, { headers: { ...getAccessHeader() }, params: body });
  } else {
    requestFn = async () => await axios.post(url, body, { headers: { ...getAccessHeader() } });
  }

  return await requestWithRefresh(requestFn);
};

const handleFileUpload = async ({ file }) => {
  let uploadPromise = new Promise((resolve, reject) => {
    let fileReader = new FileReader();

    fileReader.onload = async function (e) {
      if (file.size != e.target.result.byteLength) {
        reject("ERROR:</strong> Browser reported success but could not read the file until the end.");
      }

      let hash = SparkMD5.ArrayBuffer.hash(e.target.result);

      const uploadsResponse = await handleGenericRequest({
        method: "post",
        url: getUrl("uploads"),
        body: {
          filename: file.name,
          md5s: hexToBase64(hash),
        },
      });

      if (uploadsResponse.error) {
        reject(uploadsResponse.error);
      }

      const uploadDetails = uploadsResponse.data.params;
      const uploadId = uploadsResponse.data.id;

      const formData = new FormData();
      Object.entries(uploadDetails.fields).forEach(([k, v]) => {
        formData.append(k, v);
      });
      formData.append("file", file);

      try {
        await fetch(uploadDetails.url, {
          method: "POST",
          body: formData,
        });
        resolve({ uploadId });
      } catch (e) {
        reject({ error: e.response });
      }
    };

    fileReader.onerror = function () {
      reject("ERROR: FileReader onerror was triggered, maybe the browser aborted due to high memory usage.");
    };

    fileReader.readAsArrayBuffer(file);
  });

  const response = {};

  try {
    response = await uploadPromise;
  } catch (e) {
    if (typeof e === "string") {
      response = { error: { message: e } };
    } else {
      response = e;
    }
  }

  return response;
};

// TODO move to another file
function hexToBase64(hexstring) {
  return btoa(
    // TODO remove deprecated method btoa
    hexstring
      .match(/\w{2}/g)
      .map(function (a) {
        return String.fromCharCode(parseInt(a, 16));
      })
      .join(""),
  );
}
