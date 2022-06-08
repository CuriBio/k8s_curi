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

    postMessage(parsed_res); // errors if response isn't parsed first
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
  try {
    return await axios[method](url, body, { headers: { Authorization: `Bearer ${accessToken}` } });
  } catch (e) {
    console.log("!!!", e);
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
  // axios.interceptors.request.use(
  //   function (config) {
  //     // Do something before request is sent
  //     console.log("@@@", config);
  //     for (var pair of config.data.entries()) {
  //       console.log("@@@", pair[0] + ", " + pair[1]);
  //     }
  //     return config;
  //   },
  //   function (error) {
  //     // Do something with request error
  //     return Promise.reject(error);
  //   },
  // );

  let fileReader = new FileReader();

  fileReader.onload = async function (e) {
    let hash = null;

    if (file.size != e.target.result.byteLength) {
      console.log("ERROR:</strong> Browser reported success but could not read the file until the end.");
      return;
    } else {
      console.log("Finished loading!");
      hash = SparkMD5.ArrayBuffer.hash(e.target.result);
      console.log(file.name);
      console.log("Computed hash: " + hexToBase64(hash));
    }

    const uploadDetails = (
      await handleGenericRequest({
        method: "post",
        url: getUrl("uploads"),
        body: {
          filename: file.name,
          md5s: hexToBase64(hash),
        },
      })
    ).data.params;
    console.log("uploadDetails:", uploadDetails);

    const formData = new FormData();
    Object.entries(uploadDetails.fields).forEach(([k, v]) => {
      formData.append(k, v);
    });
    console.log("file inside handlePresignedRequest:", file);
    formData.append("file", file);
    try {
      // return await axios.post(uploadDetails.url, formData, { headers: { "Content-Type": undefined } } /**/);
      return await fetch(uploadDetails.url, {
        method: "POST",
        body: formData,
      });
    } catch (e) {
      return { error: e.response };
    }
  };

  fileReader.onerror = function () {
    running = false;
    console.log(
      "ERROR: FileReader onerror was triggered, maybe the browser aborted due to high memory usage.",
    );
  };

  fileReader.readAsArrayBuffer(file);
};

function hexToBase64(hexstring) {
  return btoa(
    hexstring
      .match(/\w{2}/g)
      .map(function (a) {
        return String.fromCharCode(parseInt(a, 16));
      })
      .join(""),
  );
}
