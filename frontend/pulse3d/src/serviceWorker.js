// Tanner (8/17/22): moved this file out of public/ since it is now processed by webpack
// which will place the compiled output file into public/ instead. This uncompiled file does not
// need to be included in any build steps, just the compiled webpack output

import jwtDecode from "jwt-decode";

import { Mutex } from "async-mutex";

const refreshMutex = new Mutex();

const PULSE3D_URL = new URLSearchParams(location.search).get("pulse3d_url");
const USERS_URL = new URLSearchParams(location.search).get("users_url");

/* Global state of SW */

let accountType = null;

const setAccountType = (type) => {
  accountType = type;
};

const clearAccountType = () => {
  accountType = null;
};

const tokens = {
  access: null,
  refresh: null,
};
let logoutTimer = null;

const setTokens = ({ access, refresh }) => {
  tokens.access = access.token;
  tokens.refresh = refresh.token;

  // set up logout timer
  const expTime = new Date(jwtDecode(tokens.refresh).exp * 1000);
  const currentTime = new Date().getTime();
  const millisBeforeLogOut = expTime - currentTime;
  logoutTimer = setTimeout(sendLogoutMsg, millisBeforeLogOut);
};

const clearTokens = () => {
  tokens.access = null;
  tokens.refresh = null;

  clearTimeout(logoutTimer);
};

let ClientSource = null;

const sendLogoutMsg = () => {
  ClientSource.postMessage({ logout: true });
  console.log("[SW] logout ping sent");
};

/* Request intercept functions */

const getUrl = ({ pathname, search }) => {
  const userUrls = ["/login", "/logout", "/refresh", "/register"];
  let url = userUrls.includes(pathname) ? USERS_URL : PULSE3D_URL;
  return new URL(`${url}${pathname}${search}`);
};

const isLoginRequest = (url) => {
  return url.pathname === "/login";
};

const modifyRequest = async (req, url) => {
  // setup new headers
  const headers = new Headers({
    ...req.headers,
    "Content-Type": "application/json",
  });

  if (!isLoginRequest(url) && tokens.access) {
    // login request does not require the Authorization header,
    // and if there are no tokens that should mean that no account is logged in
    // and the request should fail with 403
    headers.append("Authorization", `Bearer ${tokens.access}`);
  }

  // apply new headers. Make sure to clone the original request obj if consuming the body by calling json()
  // since it typically can only be consumed once
  const modifiedReq = new Request(getUrl(url), {
    headers,
    body:
      req.method === "POST" ? JSON.stringify(await req.clone().json()) : null,
    method: req.method,
  });

  return modifiedReq;
};

const handleRefreshRequest = async () => {
  console.log("[SW] Requesting new tokens in handleRefreshRequest");

  let res = null;
  try {
    res = await fetch(getUrl({ pathname: "/refresh", search: "" }), {
      method: "POST",
      body: JSON.stringify({}),
      headers: { Authorization: `Bearer ${tokens.refresh}` },
    });
  } catch (e) {
    console.log("[SW] ERROR in refresh req:", e.message);
    return { error: JSON.stringify(e.message) };
  }

  // set new tokens if refresh was successful
  // tokens should get cleared later if refresh failed
  if (res.status === 201) {
    const newTokens = await res.json();
    setTokens(newTokens);
  }

  return res.status;
};

const requestWithRefresh = async (req, url) => {
  const safeRequest = async () => {
    try {
      const modifiedReq = await modifyRequest(req, url);
      return await fetch(modifiedReq);
    } catch (e) {
      return JSON.stringify(e.message);
    }
  };

  let response = await safeRequest();

  if (response.status === 401) {
    // guard with mutex so multiple requests do not try to refresh simultaneously
    const retryRequest = await refreshMutex.runExclusive(async () => {
      // check remaining lifetime of access token
      const nowNoMillis = Math.floor(Date.now() / 1000);
      const accessTokenExp = jwtDecode(tokens.access).exp;
      if (accessTokenExp - nowNoMillis < 10) {
        // refresh tokens since the access token less than 10 seconds away from expiring
        const refreshResponseStatus = await handleRefreshRequest();
        // only retry the original request if the refresh succeeds
        return refreshResponseStatus === 201;
      }
      // since access token is not close to expiring, assume refresh was just triggered by a
      // different request and try this request again
      return true;
    });
    if (retryRequest) {
      response = await safeRequest();
    }
  }

  return response;
};

const interceptResponse = async (req, url) => {
  if (isLoginRequest(url)) {
    const modifiedReq = await modifyRequest(req, url);
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
    if (url.pathname.includes("logout")) {
      // just clear tokens if user purposefully logs out
      clearTokens();
    } else if (response.status === 401) {
      // clear tokens and send logout ping if any other request receives an unauthorized response
      clearTokens();
      sendLogoutMsg();
    }
    return response;
  }
};

/* Event listeners of SW */

self.addEventListener("install", (event) => {
  event.waitUntil(self.skipWaiting());
  console.log("[SW] Service worker installed!");
});

self.addEventListener("activate", (event) => {
  event.waitUntil(self.clients.claim());
  console.log("[SW] Service worker ready!");
});

// Intercept all fetch requests
self.addEventListener("fetch", async (e) => {
  let destURL = new URL(e.request.url);
  // only intercept routes to pulse and user apis

  if (destURL.hostname === "curibio.com") {
    e.respondWith(interceptResponse(e.request, destURL));
  } else e.respondWith(fetch(e.request));
});

// Clear token on postMessage
self.onmessage = ({ data, source }) => {
  ClientSource = source;
  if (data.msgType === "clear") {
    // TODO Tanner (8/24/22): might want to only clear if not already cleared
    console.log("[SW] Clearing tokens and account type in ServiceWorker");
    clearTokens();
    clearAccountType();
  } else if (data.msgType === "authCheck") {
    console.log("[SW] Returning authentication check ");
    source.postMessage({
      authCheck: tokens.access !== null,
      accountType,
      routerPathname: data.routerPathname,
    });
  } else if (data.msgType == "setAccountType") {
    console.log("[SW] Setting account type:", data.accountType);
    setAccountType(data.accountType);
  }
};

export const accessToInternalsForTesting = {
  tokens,
  logoutTimer,
  ClientSource,
  accountType,
};
