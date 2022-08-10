const PULSE3D_URL = new URLSearchParams(location.search).get("pulse3d_url");
const USERS_URL = new URLSearchParams(location.search).get("users_url");

let accountType = null;
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

const setAccountType = (type) => {
  accountType = type;
};

const clearAccountType = () => {
  accountType = null;
};


const getUrl = (pathname) => {
  const user_urls = ["/login", "/logout", "/refresh", "/register"];
  let url = user_urls.includes(pathname) ? USERS_URL : PULSE3D_URL;
  return new URL(`${url}${pathname}`);
};

const isLoginRequest = (url) => {
  return url.pathname === "/login";
};

const createRequest = (req, url) => {
  // setup new headers
  const headers = new Headers({
    ...req.headers,
    "Content-Type": "application/json",
  });
  if (!isLoginRequest(url)) {
    headers.append("Authorization", `Bearer ${tokens.access}`);
  }

  // apply new headers
  const modifiedReq = new Request(getUrl(url), {
    headers,
    body: req.method === "POST" ? JSON.stringify(await req.json()) : null,
    method: req.method,
  });

  return modifiedReq;
}

const handleRefreshRequest = async () => {
  console.log("[SW] Requesting new tokens in handleRefreshRequest");

  let res = null;
  try {
    res = await fetch(getUrl("/refresh"), {
      method: "POST",
      body: JSON.stringify({}),
      headers: { Authorization: `Bearer ${tokens.refresh}` },
    });
  } catch (e) {
    console.log("ERROR IN REFRESH REQ: ", e.message);
    return { error: JSON.stringify(e.message) };
  }

  // set new tokens if refresh was successful, or clear if refresh failed
  if (res.status === 201) {
    const newTokens = await res.json();
    setTokens(newTokens);
  } else {
    clearTokens();
  }

  return res.status;
};

const requestWithRefresh = async (req, url) => {
  const safeRequest = async () => {
    try {
      const modifiedReq = createRequest(req, url);
      return await fetch(modifiedReq);
    } catch (e) {
      return JSON.stringify(e.message);
    }
  };

  let response = await safeRequest();

  if (response.status === 401) {
    // attempt to get new tokens
    const refreshResponseStatus = await handleRefreshRequest();
    if (refreshResponseStatus !== 201) {
      // if the refresh failed, no need to try request again, just return original failed response
      return response;
    }
    // try again with new tokens
    response = await safeRequest();
  }

  return response;
};

const interceptResponse = async (req, url) => {
  if (isLoginRequest(url)) {
    const modifiedReq = createRequest(req, url);
    const response = await fetch(modifiedReq);
    if (response.status === 200) {
      // set tokens if login was successful
      const data = await response.json();
      setTokens(data);
    }
    // send the response without the tokens so they are always contained within this service worker
    return new Response(JSON.stringify({}), {
      headers: response.headers,
      status: response.status,
      statusText: response.statusText,
    });
  } else {
    const response = await requestWithRefresh(req, url);
    // clear tokens if user purposefully logs out or any other response returns an unauthorized response
    if (url.pathname.includes("logout") || response.status === 401) {
      clearTokens();
    }
    return response;
  }
};

/* Event Listeners */

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
    console.log("[SW] Clearing tokens and account type in ServiceWorker");
    clearTokens();
    clearAccountType();
  } else if (data === "authCheck") {
    console.log("[SW] Returning authentication check ");
    source.postMessage({ authCheck: tokens.access !== null, accountType });
    //auth check
  } else if (data.accountType) {
    console.log("[SW] Setting account type");
    setAccountType(data.accountType);
  }
};