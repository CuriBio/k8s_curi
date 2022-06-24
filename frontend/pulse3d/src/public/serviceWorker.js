// TODO add .env for prod v. test url
const domain = "curibio-test"; // MODIFY URL until decided how it's handled

const getUrl = (endpoint) => {
  let subdomain = endpoint.includes("users") ? "apiv2" : "pulse3d";
  return new URL(`https://${subdomain}.${domain}.com${endpoint}`);
};

const tokens = {
  access: null,
  refresh: null,
};

const setTokens = ({ access, refresh }) => {
  tokens.access = access.token;
  tokens.refresh = refresh.token;
};

const clearTokens = () => {
  tokens.access = null;
  tokens.refresh = null;
};

const isAuthRequest = (url) => {
  const tokenUrl = "/users/login";
  return tokenUrl.includes(url.pathname);
};

self.addEventListener("install", (event) => {
  event.waitUntil(self.skipWaiting());
  console.log("[SW] Service worker installed!");
});

self.addEventListener("activate", (event) => {
  event.waitUntil(self.clients.claim());
  console.log("[SW] Service worker ready!");
});

// Clear token on postMessage
self.onmessage = ({ data, source }) => {
  if (data === "clear") {
    console.log("[SW] Clearing tokens in ServiceWorker");
    clearTokens();
  } else if (data === "authCheck") {
    console.log("[SW] Returning authentication check");
    source.postMessage(tokens.access !== null);
  }
};
// Intercept all fetch requests
self.addEventListener("fetch", async (e) => {
  destURL = new URL(e.request.url);
  // only intercept routes to pulse and user apis
  if (destURL.host === "localhost") {
    e.respondWith(interceptResponse(e.request, destURL));
  }
});

const interceptResponse = async (req, url) => {
  // setup new headers
  const headers = new Headers({
    ...req.headers,
    "Content-Type": "application/json",
  });
  if (tokens.access && !isAuthRequest(url)) {
    headers.append("Authorization", `Bearer ${tokens.access}`);
  }
  // apply new headers
  const newReq = new Request(getUrl(url.pathname), {
    headers,
    body: req.method === "POST" ? JSON.stringify(await req.json()) : null,
    method: req.method,
  });

  if (!isAuthRequest(url)) {
    const requestFn = async () => await fetch(newReq);
    return await requestWithRefresh(requestFn, url);
  } else {
    const response = await fetch(newReq);

    // catch response and set token
    if (response.status === 200) {
      const data = await response.json();
      setTokens(data);
    }
    // send the response without it
    return new Response(JSON.stringify({}), {
      headers: response.headers,
      status: response.status,
      statusText: response.statusText,
    });
  }
};

const requestWithRefresh = async (requestFn, url) => {
  const safeRequest = async () => {
    try {
      return await requestFn();
    } catch (e) {
      return JSON.stringify(e.message);
    }
  };

  let response = await safeRequest();
  if (response.status === 401) {
    // attempt to get new tokens
    const refreshResponse = await handleRefreshRequest();
    if (refreshResponse.status !== 200) {
      // if the refresh failed, no need to try request again, just return original failed response
      clearTokens();
      return response;
    }
    //
    // try again with new tokens
    response = await safeRequest();
  }

  // clear tokens if user purposefully logs out or any other response returns an unauthorized response
  if (
    url.pathname.includes("logout") ||
    response.status === 401 ||
    response.status === 403
  )
    clearTokens();

  return response;
};

const handleRefreshRequest = async () => {
  console.log("[SW] Requesting new tokens in handleRefreshRequest");

  let res = null;
  try {
    res = await axios.post(
      getUrl("/users/refresh"),
      // TODO look into ways to not pass an empty body
      {},
      { headers: { Authorization: `Bearer ${tokens.refresh}` } }
    );
  } catch (e) {
    return { error: JSON.stringify(e.message) };
  }
  //set new tokens
  setTokens(await res.json());

  // remove tokens from response
  return new Response(JSON.stringify({}), {
    headers: res.headers,
    status: res.status,
    statusText: res.statusText,
  });
};
