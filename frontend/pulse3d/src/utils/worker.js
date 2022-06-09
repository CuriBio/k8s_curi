import axios from "axios";
import SparkMD5 from "spark-md5";

// TODO add .env for prod v. test url
const domain = "curibio-test"; // MODIFY URL until decided how it's handled

const getUrl = (endpoint) => {
  let subdomain = endpoint.includes("users") ? "apiv2" : "pulse3d";

  return `https://${subdomain}.${domain}.com/${endpoint}`;
};

let accessToken = null;
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
  console.log("WW onmessage:", accessToken, data);
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

const handleGenericRequest = async ({ url, method, body }) => {
  console.log("handleGenericRequest", url, method, body, accessToken);

  const headers = { Authorization: `Bearer ${accessToken}` };

  try {
    if (method === "get") {
      return await axios.get(url, { headers, params: body });
    } else {
      return await axios.post(url, body, { headers });
    }
  } catch (e) {
    return { error: e.response };
  }
};

const handleAuthRequest = async ({ url, body }) => {
  let res = null;
  try {
    res = await axios.post(url, body);
  } catch (e) {
    return { error: e.response };
  }

  accessToken = res.data.access.token;
  // return 200 status code
  return { status: 200 };
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
