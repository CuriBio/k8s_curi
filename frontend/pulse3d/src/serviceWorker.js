// Tanner (8/17/22): moved this file out of public/ since it is now processed by webpack
// which will place the compiled output file into public/ instead. This uncompiled file does not
// need to be included in any build steps, just the compiled webpack output

import jwtDecode from "jwt-decode";
import { Mutex } from "async-mutex";

/* Global state of SW */
const refreshMutex = new Mutex();

let accountType = null;
let usageQuota = null; // TODO Tanner (7/6/23): doesn't seem like this is being used for anything other than the authcheck, but the value is ignored when that message is received. Can probably remove this
let accountId = null;
let ClientSource = null;

let reloadNeeded = false;

const cacheName = "preloadedWellData";

const USERS_URL = new URLSearchParams(location.search).get("users_url");
const PULSE3D_URL = new URLSearchParams(location.search).get("pulse3d_url");
const USAGE_URLS = ["/login", "/uploads", "/jobs"];

// add timestamps to logging
const originalLog = console.log;

console.log = function () {
  const time = new Date().toLocaleTimeString("en-US", {
    hour12: false,
    hour: "numeric",
    minute: "numeric",
    second: "numeric",
  });
  originalLog(...[`[SW @ ${time}]`, ...arguments]);
};

const setAccountType = (type) => {
  accountType = type;
};

const clearAccountType = () => {
  accountType = null;
};

const setAccountId = (id) => {
  accountType = type;
};

const clearAccountId = () => {
  accountId = null;
};

const setUsageQuota = (usage) => {
  usageQuota = usage;
};

const clearUsageQuota = () => {
  usageQuota = null;
};
const tokens = {
  access: null,
  refresh: null,
};

let logoutTimer = null;

const setTokens = ({ access, refresh }) => {
  tokens.access = access.token;
  tokens.refresh = refresh.token;

  // clear old logout timer if one already exists
  if (logoutTimer) {
    clearTimeout(logoutTimer);
  }
  // set up new logout timer
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

const sendLogoutMsg = () => {
  clearAccountInfo();
  ClientSource.postMessage({ msgType: "logout" });
  console.log("logout ping sent");
};

const clearAccountInfo = () => {
  // TODO should combine all this data into one object so different functions aren't needed for each
  clearTokens();
  clearAccountType();
  clearAccountId();
  clearUsageQuota();
  // TODO change all console.log to console.debug and figure out how to enable debug logging
  console.log("account info cleared");
};

/* Request intercept functions */

const isLoginRequest = (url) => {
  return url.pathname.includes("/login");
};

const isUpdateRequest = (url) => {
  return url.pathname.includes("/account");
};

const isEmailRequest = (url) => {
  return url.pathname.includes("/email");
};

const isWaveformDataRequest = (url) => {
  return url.pathname.includes("/waveform-data");
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
  console.log("Requesting new tokens in handleRefreshRequest");

  let res = null;
  try {
    res = await fetch(`${USERS_URL}/refresh`, {
      method: "POST",
      body: JSON.stringify({}),
      headers: { Authorization: `Bearer ${tokens.refresh}` },
    });
  } catch (e) {
    console.log("ERROR in refresh req:", e.message);
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
      setTokens(data.tokens);
      const decodedAccessToken = jwtDecode(tokens.access);
      let { account_type: accountType, userid: id } = decodedAccessToken; // either token will work here

      if (accountType === "customer") {
        // token types are 'user' and 'customer', but FE uses 'user' and 'admin'
        accountType = "admin";
      }

      console.log("Setting account type:", accountType);
      setAccountType(accountType);
      setAccountId(id);
      // sending usage at login, is separate from auth check request because it's not needed as often
      setUsageQuota(data.usage_quota);
    }

    // send the response without the tokens so they are always contained within this service worker
    return new Response(JSON.stringify({}), {
      headers: response.headers,
      status: response.status,
      statusText: response.statusText,
    });
  } else {
    const response = await requestWithRefresh(req, url);

    // these URLs will return usage_error in the body with a 200 response
    if (USAGE_URLS.includes(url.pathname) && req.method === "POST" && response.status == 200) {
      const resBodyToCheck = await response.json();

      // set the usage error to SW state to send in auth check, will return a 200 status
      if (resBodyToCheck.error && resBodyToCheck.error === "UsageError") {
        setUsageQuota(resBodyToCheck.message);
      } else {
        setUsageQuota(resBodyToCheck.usage_quota);
      }
      // make sure to send the rest of the body for the uploads-form to handle response itself
      return new Response(JSON.stringify(resBodyToCheck));
    } else if (url.pathname.includes("logout")) {
      // just clear account info if user purposefully logs out
      clearAccountInfo();
    } else if (response.status === 401 || response.status === 403) {
      // if any other request receives an unauthorized or forbidden error code, send logout ping (this fn will also clear account info)
      sendLogoutMsg();
    }
    return response.clone();
  }
};

const convertLargeArrToJson = (arr) => {
  return "[" + arr.map((el) => JSON.stringify(el)).join(",") + "]";
};

const getWaveformDataFromS3 = async (res) => {
  try {
    const response = await res.json();

    const timeForceRes = await fetch(response.time_force_url);
    const peaksValleysRes = await fetch(response.peaks_valleys_url);

    return {
      normalizeYAxis: response.normalize_y_axis,
      peaksValleysData: convertLargeArrToJson(new Uint8Array(await peaksValleysRes.arrayBuffer())),
      timeForceData: convertLargeArrToJson(new Uint8Array(await timeForceRes.arrayBuffer())),
    };
  } catch (e) {
    console.log("Error grabbing waveform data: " + e);
  }
};

/* Event listeners of SW */

self.addEventListener("install", (event) => {
  event.waitUntil(self.skipWaiting());
  console.log("Service worker installed!");
  reloadNeeded = true;
});

self.addEventListener("activate", (event) => {
  // delete any previous cache from previous sessions
  event.waitUntil(
    caches.keys().then(function (cacheNames) {
      return Promise.all(
        cacheNames.map(function (cacheName) {
          console.log("Deleting cache for: ", cacheName);
          return caches.delete(cacheName);
        })
      );
    })
  );
  console.log("Service worker ready!");
});
// Intercept all fetch requests
self.addEventListener("fetch", async (e) => {
  let destURL = new URL(e.request.url);

  if (
    (e.request.url.includes(USERS_URL) || e.request.url.includes(PULSE3D_URL)) &&
    !isEmailRequest(destURL) && // this request doesn't depend on a token
    !isUpdateRequest(destURL) // we don't need to intercept verify request because it's handling own token
  ) {
    // only intercept requests to pulse3d and user APIs
    e.respondWith(
      caches.open(cacheName).then(async (cache) => {
        // Go to the cache first
        const cachedResponse = await cache.match(e.request.url);
        //  For now, only return cached responses for waveform data requests
        if (cachedResponse && isWaveformDataRequest(destURL)) {
          console.log(`Returning cached response for ${destURL}`);
          return cachedResponse;
        }
        // Otherwise, hit the network
        let response = await interceptResponse(e.request, destURL);
        // before returning response, check if you need to preload other wells
        // this needs to go after interceptResponse so that the initial A1 data gets returned first and not blocked by other requests
        if (isWaveformDataRequest(destURL)) {
          const fetchedData = await getWaveformDataFromS3(response);
          response = new Response(JSON.stringify(fetchedData), {
            status: response.status,
            statusText: response.statusText,
          });
          // only store if successful request
          if (response && response.status === 200) cache.put(e.request, response.clone());
        }

        return response;
      })
    );
  } else {
    e.respondWith(fetch(e.request));
  }
});

self.onmessage = ({ data, source }) => {
  ClientSource = source;

  const { msgType, routerPathname } = data;
  const baseMsg = { msgType, routerPathname };
  let msgInfo = {};

  if (msgType === "checkReloadNeeded") {
    msgInfo = { reloadNeeded };
    reloadNeeded = false;
  } else if (msgType === "authCheck") {
    console.log("Returning authentication check");
    msgInfo = {
      isLoggedIn: tokens.access !== null,
      accountType,
      accountId,
      usageQuota,
    };
  } else if (msgType === "stayAlive") {
    // TODO should have this do something else so that there isn't a log msg produced every 20 seconds
    console.log("Staying alive");
  } else if (msgType === "clearData") {
    // a way for the FE components to force clear all stored data in the service worker
    console.log("Recieved clear message type to clear account info");
    clearAccountInfo();
  }

  if (Object.keys(msgInfo).length > 0) {
    source.postMessage({
      ...baseMsg,
      ...msgInfo,
    });
  }
};

export const accessToInternalsForTesting = {
  tokens,
  logoutTimer,
  ClientSource,
  accountType,
};
