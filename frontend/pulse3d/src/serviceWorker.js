// Tanner (8/17/22): moved this file out of public/ since it is now processed by webpack
// which will place the compiled output file into public/ instead. This uncompiled file does not
// need to be included in any build steps, just the compiled webpack output

import jwtDecode from "jwt-decode";
import { Mutex } from "async-mutex";

const refreshMutex = new Mutex();

const USERS_URL = new URLSearchParams(location.search).get("users_url");
const PULSE3D_URL = new URLSearchParams(location.search).get("pulse3d_url");

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
  clearAccountInfo();
  ClientSource.postMessage({ logout: true });
  console.log("[SW] logout ping sent");
};

const clearAccountInfo = () => {
  clearTokens();
  clearAccountType();
  // TODO change all console.log to console.debug and figure out how to enable debug logging
  console.log("[SW] account info cleared");
};

/* Request intercept functions */

const isLoginRequest = (url) => {
  return url.pathname.includes("/login");
};

const isVerifyRequest = (url) => {
  return url.pathname.includes("/verify");
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
  const modifiedReq = new Request(url, {
    headers,
    body: !["GET", "DELETE"].includes(req.method) ? JSON.stringify(await req.clone().json()) : null,
    method: req.method,
  });

  return modifiedReq;
};

const handleRefreshRequest = async () => {
  console.log("[SW] Requesting new tokens in handleRefreshRequest");

  let res = null;
  try {
    res = await fetch(`${USERS_URL}/refresh`, {
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
      let accountType = jwtDecode(tokens.access).account_type; // either token will work here

      if (accountType === "customer") {
        // token types are 'user' and 'customer', but FE uses 'user' and 'admin'
        accountType = "admin";
      }
      console.log("[SW] Setting account type:", accountType);
      setAccountType(accountType);
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
      // just clear account info if user purposefully logs out
      clearAccountInfo();
    } else if (response.status === 401 || response.status === 403) {
      // if any other request receives an unauthorized or forbidden error code, send logout ping (this fn will also clear account info)
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
  // only intercept requests to pulse3d and user APIs
  if (
    (e.request.url.includes(USERS_URL) || e.request.url.includes(PULSE3D_URL)) &&
    !isVerifyRequest(destURL)
  ) {
    e.respondWith(interceptResponse(e.request, destURL));
  } else {
    console.log(e.request);
    e.respondWith(fetch(e.request));
  }
});

self.onmessage = ({ data, source }) => {
  ClientSource = source;
  if (data.msgType === "authCheck") {
    console.log("[SW] Returning authentication check");
    source.postMessage({
      isLoggedIn: tokens.access !== null,
      accountType,
      routerPathname: data.routerPathname,
    });
  } else if (data.msgType === "stayAlive") {
    // TODO should have this do something else so that there isn't a log msg produced every 20 seconds
    console.log("[SW] Staying alive");
  }
};

export const accessToInternalsForTesting = {
  tokens,
  logoutTimer,
  ClientSource,
  accountType,
};
