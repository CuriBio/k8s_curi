// Tanner (8/17/22): moved this file out of public/ since it is now processed by webpack
// which will place the compiled output file into public/ instead. This uncompiled file does not
// need to be included in any build steps, just the compiled webpack output

import jwtDecode from "jwt-decode";
import { Mutex } from "async-mutex";
import { WellTitle as LabwareDefinition } from "./utils/labwareCalculations";

/* Global state of SW */
const refreshMutex = new Mutex();

let accountType = null;
let usageQuota = null;
let ClientSource = null;

const cacheName = "preloadedWellData";
const twentyFourPlateDefinition = new LabwareDefinition(4, 6);
const wellNames = Array(24)
  .fill()
  .map((_, idx) => twentyFourPlateDefinition.getWellNameFromIndex(idx));

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
  ClientSource.postMessage({ logout: true });
  console.log("logout ping sent");
};

const clearAccountInfo = () => {
  clearTokens();
  clearAccountType();
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
  // if it's a string, just check that it's  a waveform data request
  // else check if it's the initial request and will be passed url params instead
  return url instanceof URL
    ? url.pathname.includes("/waveform-data")
    : url.get("well_name") == "A1" && url.get("peaks_valleys");
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
      let accountType = jwtDecode(tokens.access).account_type; // either token will work here

      if (accountType === "customer") {
        // token types are 'user' and 'customer', but FE uses 'user' and 'admin'
        accountType = "admin";
      }

      console.log("Setting account type:", accountType);
      setAccountType(accountType);
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
    } else if (isWaveformDataRequest(url)) {
      caches.open(cacheName).then(async (cache) => {
        if (response) cache.put(req, response.clone());
      });
    }

    return response.clone();
  }
};

const startPreloadingWellData = (uploadId, jobId) => {
  try {
    // remove A1 as that's loaded first separately
    const [, ...remainingWells] = wellNames;

    for (const well of remainingWells) {
      const destURL = new URL(
        `${PULSE3D_URL}/jobs/waveform-data?upload_id=${uploadId}&job_id=${jobId}&peaks_valleys=false&well_name=${well}`
      );

      const newReq = new Request(destURL);
      caches.open(cacheName).then(async (cache) => {
        // Go to the cache first
        return cache.match(newReq.url).then(async (cachedResponse) => {
          // Return a cached response if we have one
          if (!cachedResponse) {
            // Otherwise, hit the network
            interceptResponse(newReq, destURL);
          }
        });
      });
    }
  } catch (e) {
    console.log("Error grabbing preloaded data: " + e);
  }
};

/* Event listeners of SW */

self.addEventListener("install", (event) => {
  event.waitUntil(self.skipWaiting());
  console.log("Service worker installed!");
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
  const urlParams = new URLSearchParams(destURL.search);

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
        if (cachedResponse) {
          return cachedResponse;
        }
        // Otherwise, hit the network
        const response = await interceptResponse(e.request, destURL);
        // before returning response, check if you need to preload other wells
        // this needs to go after interceptResponse so that the initial A1 data gets returned first and not blocked by other requests
        if (isWaveformDataRequest(urlParams)) {
          const jobId = urlParams.get("job_id");
          const uploadId = urlParams.get("upload_id");
          startPreloadingWellData(uploadId, jobId);
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
  if (data.msgType === "authCheck") {
    console.log("Returning authentication check");
    source.postMessage({
      isLoggedIn: tokens.access !== null,
      accountType,
      routerPathname: data.routerPathname,
      usageQuota,
    });
  } else if (data.msgType === "stayAlive") {
    // TODO should have this do something else so that there isn't a log msg produced every 20 seconds
    console.log("Staying alive");
  } else if (data.msgType === "clearData") {
    // a way for the FE components to force clear all stored data in the service worker
    console.log("Recieved clear message type to clear account info");
    clearAccountInfo();
  }
};

export const accessToInternalsForTesting = {
  tokens,
  logoutTimer,
  ClientSource,
  accountType,
};
