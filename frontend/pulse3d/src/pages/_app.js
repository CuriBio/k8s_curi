import "../styles/globals.css";
import "@fontsource/mulish";
import Layout from "@/components/layouts/Layout";
import { createTheme, ThemeProvider } from "@mui/material/styles";
import { useEffect, createContext, useState } from "react";
import { useRouter } from "next/router";
import ModalWidget from "@/components/basicWidgets/ModalWidget";
import { deepCopy } from "@/utils/generic";
import useEventSource from "@/utils/eventSource";
import { formatJob } from "@/utils/generic";

/*
  This theme is to be used with materialUI components
  More colors can be added if desired.
  Colors need to be lable specific to what material UI expects otherwise it will error in tests
*/
const MUItheme = createTheme({
  palette: {
    primary: {
      // dark blue
      main: "rgb(0, 38, 62)",
    },
    secondary: {
      // teal green
      main: "rgb(25, 172, 138)",
    },
  },
});

export const AuthContext = createContext();
export const UploadsContext = createContext();
export const AdvancedAnalysisContext = createContext();

// TODO make all pages scope based?
const allAvailablePages = {
  user: [
    "/home",
    "/uploads",
    "/upload-form",
    "/account",
    "/account-settings",
    "/metrics",
    "/advanced-analyses",
    "/advanced-analysis-form",
  ],
  admin: [
    "/uploads",
    "/add-new-account",
    "/user-info",
    "/customer-info",
    "/notifications-management",
    "/account-settings",
  ],
};

const stiffnessFactorDetails = {
  Auto: null,
  "Cardiac (1x)": 1,
  "Skeletal Muscle (12x)": 12,
  // Tanner (11/1/22): if we need to add an option for variable stiffness in the dropdown, a new version of pulse3d will need to be released
};

const dataTypeDetails = {
  Auto: null,
  Force: "Force",
  Calcium: "Calcium",
  Voltage: "Voltage",
};

const getAvailablePages = (accountInfo) => {
  if (!allAvailablePages[accountInfo.accountType]) {
    // accountType isn't set yet
    return [];
  }

  const pages = deepCopy(allAvailablePages[accountInfo.accountType]);
  // TODO find a way to define these only once and share with the ControlPanel component
  const productionConsoleScopes = [
    "mantarray:serial_number:list",
    "mantarray:serial_number:edit",
    "mantarray:firmware:edit",
    "mantarray:firmware:list",
  ];
  if (accountInfo.accountScope.some((scope) => productionConsoleScopes.includes(scope))) {
    pages.push("/production-console");
  }
  return pages;
};

const loadProductPage = () => {
  const storedProductPage = localStorage.getItem("productPage");
  return storedProductPage === "null" ? null : storedProductPage;
};

function Pulse({ Component, pageProps }) {
  const getLayout = Component.getLayout || ((page) => page);
  const router = useRouter();
  const [accountInfo, setAccountInfo] = useState({});
  const [showLoggedOutAlert, setLoggedOutAlert] = useState(false);
  const [usageQuota, setUsageQuota] = useState();
  const [availableScopes, setAvailableScopes] = useState({ admin: [], user: [] });
  const [isCuriAdmin, setIsCuriAdmin] = useState(false);
  const [preferences, setPreferences] = useState({});
  const [productPage, setProductPage] = useState();

  // UploadsContext
  const [uploads, setUploads] = useState();
  const [jobs, setJobs] = useState([]);
  const [pulse3dVersions, setPulse3dVersions] = useState([]);
  const [metaPulse3dVersions, setMetaPulse3dVersions] = useState([]);
  const [defaultUploadForReanalysis, setDefaultUploadForReanalysis] = useState();

  // AdvancedAnalysisContext
  const [advancedAnalysisJobs, setAdvancedAnalysisJobs] = useState([]);

  const { setDesiredConnectionStatus: setEvtSourceConnected } = useEventSource({
    productPage,
    uploads,
    setUploads,
    jobs,
    setJobs,
    usageQuota,
    setUsageQuota,
    accountId: accountInfo.accountId,
    accountType: accountInfo.accountType,
  });

  const updateProductPage = (product) => {
    localStorage.setItem("productPage", product);
    setProductPage(product);
  };

  // set product page in localStorage so that it persists through page refreshes. Check that this value is not
  // manually set by user to a product they do not have access to
  useEffect(() => {
    const { accountScope, accountType } = accountInfo;

    if (!accountType) {
      // nothing can be done yet if the account type isn't set
      return;
    }

    if (accountType === "admin") {
      if (productPage) {
        setProductPage(null);
      }
      localStorage.setItem("productPage", null);
    } else if (productPage) {
      // if the product page is already set for a user, nothing needs to be done
      return;
    } else {
      const storedProductPage = loadProductPage();
      if (storedProductPage) {
        // prevent access to products not in the user's scopes
        if (accountScope.some((scope) => scope.includes(storedProductPage))) {
          setProductPage(storedProductPage);
        } else {
          localStorage.setItem("productPage", null);
        }
      }
    }
  }, [productPage, accountInfo]);

  let swInterval = null;
  // register the SW once
  useEffect(() => {
    if ("serviceWorker" in navigator) {
      // env vars need to be set here because service worker does not have access to node process
      navigator.serviceWorker
        .register(
          `/serviceWorker.js?mantarray_url=${process.env.NEXT_PUBLIC_MANTARRAY_URL}&users_url=${process.env.NEXT_PUBLIC_USERS_URL}&pulse3d_url=${process.env.NEXT_PUBLIC_PULSE3D_URL}&events_url=${process.env.NEXT_PUBLIC_EVENTS_URL}&advanced_analysis_url=${process.env.NEXT_PUBLIC_ADVANCED_ANALYSIS_URL}`,
          { type: "module" }
        )
        .then(navigator.serviceWorker.ready)
        .then((registration) => {
          registration.update();
          console.log("Updating service worker");
        }) // update the service worker
        .then(() => {
          sendSWMessage({ msgType: "checkReloadNeeded", routerPathname: router.pathname });
          sendSWMessage({
            msgType: "authCheck",
            routerPathname: router.pathname,
            productPage: productPage || loadProductPage(),
          });
        })
        .catch((e) => console.log("SERVICE WORKER ERROR: ", e));

      navigator.serviceWorker.addEventListener("message", ({ data }) => {
        // might need auth check to include actual fetch request in SW to check token status if this becomes a problem
        // will not use the correct pathname if directly accessing router.pathname
        const currentPage = data.routerPathname;
        const isAccountPage = currentPage && ["/account/verify", "/account/reset"].includes(currentPage);

        if (data.msgType === "checkReloadNeeded") {
          if (data.reloadNeeded && currentPage === "/login") {
            // after a fresh install of the service worker, need to reload. Only perform the reload when already on the login page just in case this message is received on another page somehow
            location.reload();
          }
        } else if (!isAccountPage) {
          // ignore all the following messages if on the account page
          if (data.msgType === "logout") {
            setEvtSourceConnected(false);
            if (currentPage !== "/login") {
              // logged out due to inactivity message shouldn't show if already on the login page
              setLoggedOutAlert(true);
            }
          } else if (data.msgType === "authCheck") {
            const newAccountInfo = data.accountInfo;

            if (data.isLoggedIn) {
              setAvailableScopes({ admin: data.adminScopes, user: data.userScopes });
              setIsCuriAdmin(newAccountInfo.accountScope.find((scope) => scope === "curi:admin"));
              setEvtSourceConnected(true);
              // the router pathname must be sent to the SW and then sent back here since for some reason this message handler can't grab the current page
              setAccountInfo(newAccountInfo);
              setPreferences(data.preferences); // will be {} is None
              // if logged in and on a page that shouldn't be accessed, or if on the login page, redirect to home page (currently /uploads)
              if (currentPage === "/login" || !getAvailablePages(newAccountInfo).includes(currentPage)) {
                // TODO Tanner (8/23/22): this probably isn't the best solution for redirecting to other pages. Should look into a better way to do this
                router.replace(newAccountInfo.accountType === "user" ? "/home" : "/uploads", undefined, {
                  shallow: true,
                });
              } else if (
                currentPage !== "/home" &&
                newAccountInfo.accountType === "user" &&
                (!data.productPage ||
                  !newAccountInfo.accountScope.some((scope) => scope.includes(data.productPage)))
              ) {
                router.replace("/home", undefined, {
                  shallow: true,
                });
              }
            } else {
              setEvtSourceConnected(false);
              if (currentPage !== "/login") {
                // always redirect to login page if not logged in
                setAccountInfo(newAccountInfo);
                router.replace("/login", undefined, { shallow: true });
              }
            }
          }
        }
      });
    }
  }, []);

  // whenever the page updates, sends message to SW (if active) to check if a user is logged in
  useEffect(() => {
    sendSWMessage({
      msgType: "authCheck",
      routerPathname: router.pathname,
      productPage: productPage || loadProductPage(),
    });

    // if on a home or login page, clear productPage
    if (["/login", "/home"].includes(router.pathname)) {
      updateProductPage(null);
      setUploads(null);
    }

    // start pinging SW if not on login page to keep alive
    if (!["/login", "/account/verify", "/account/reset"].includes(router.pathname)) {
      keepSWALive();
    }
    if (["/account/verify", "/account/reset"].includes(router.pathname)) {
      // when a user gets redirected to page to reset password or verify account, it should redirect user to login and not consider them as logged in if they previously were.
      // even though this scenario is unlikely, just ensures they'll be logged out and protects against if an admin performs some of these actions while logged into an admin account previously.
      sendSWMessage({
        msgType: "clearData",
      });
    }
    // clear on teardown/page redirections
    return () => clearInterval(swInterval);
  }, [router.pathname]);

  const sendSWMessage = (msg) => {
    if ("serviceWorker" in navigator) {
      navigator.serviceWorker.ready.then((registration) => {
        registration.active.postMessage(msg);
      });
    }
  };

  const keepSWALive = () => {
    if ("serviceWorker" in navigator) {
      navigator.serviceWorker.ready.then((registration) => {
        swInterval = setInterval(
          () =>
            registration.active.postMessage({
              msgType: "stayAlive",
            }),
          20e3
        );
      });
    }
  };

  const getUploadsAndJobs = async (
    uploadType,
    filters,
    sortField = "last_analyzed",
    sortDirection = "DESC",
    skip = 0,
    limit = 300
  ) => {
    let uploadsArr = [];
    try {
      let url = `${process.env.NEXT_PUBLIC_PULSE3D_URL}/uploads`;
      let queryParams = [];

      if (uploadType) {
        queryParams.push(`upload_type=${uploadType}`);
      }
      if (sortField) {
        queryParams.push(`sort_field=${sortField}`);
        if (!["ASC", "DESC"].includes(sortDirection)) {
          sortDirection = "DESC";
        }
        queryParams.push(`sort_direction=${sortDirection}`);
      }
      if (skip != null) {
        queryParams.push(`skip=${skip}`);
      }
      if (limit != null) {
        queryParams.push(`limit=${limit}`);
      }
      if (filters && Object.keys(filters).length > 0) {
        for (const [filterName, filterValue] of Object.entries(filters)) {
          queryParams.push(`${filterName}=${filterValue}`);
        }
      }
      if (queryParams.length > 0) {
        url += "?" + queryParams.join("&");
      }

      const response = await fetch(url);

      if (response && response.status === 200) {
        uploadsArr = await response.json();
        setUploads([...uploadsArr]);
      }
    } catch (e) {
      console.log("ERROR getting uploads for user", e);
      return;
    }

    if (uploadsArr.length === 0) {
      return;
    }

    const uploadIds = uploadsArr.map(({ id }) => id);

    let jobsRes = [];
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_PULSE3D_URL}/jobs/info`, {
        method: "POST",
        body: JSON.stringify({ upload_ids: uploadIds, upload_type: uploadType }),
      });

      if (response && response.status === 200) {
        jobsRes = await response.json();
      }
    } catch (e) {
      console.log("ERROR fetching jobs", e);
      return;
    }

    try {
      const newJobs = jobsRes
        .map((job) => {
          return formatJob(job, {}, accountInfo.accountId);
        })
        .filter((j) => j !== null);

      setJobs([...newJobs]);
    } catch (e) {
      console.log("ERROR processing jobs", e);
      return;
    }
  };

  const getAdvancedAnalysisJobs = async (
    filters,
    sortField = "created_at",
    sortDirection = "DESC",
    skip = 0,
    limit = 300
  ) => {
    try {
      let url = `${process.env.NEXT_PUBLIC_ADVANCED_ANALYSIS_URL}/advanced-analyses`;
      let queryParams = [];

      if (sortField) {
        queryParams.push(`sort_field=${sortField}`);
        if (!["ASC", "DESC"].includes(sortDirection)) {
          sortDirection = "DESC";
        }
        queryParams.push(`sort_direction=${sortDirection}`);
      }
      if (skip != null) {
        queryParams.push(`skip=${skip}`);
      }
      if (limit != null) {
        queryParams.push(`limit=${limit}`);
      }
      if (filters && Object.keys(filters).length > 0) {
        for (const [filterName, filterValue] of Object.entries(filters)) {
          queryParams.push(`${filterName}=${filterValue}`);
        }
      }
      if (queryParams.length > 0) {
        url += "?" + queryParams.join("&");
      }

      const response = await fetch(url);

      if (response && response.status === 200) {
        const jobs = await response.json();
        setAdvancedAnalysisJobs(jobs);
      }
    } catch (e) {
      console.log("ERROR getting advanced analyses for user", e);
      return;
    }
  };

  return (
    <ThemeProvider theme={MUItheme}>
      <AuthContext.Provider
        value={{
          loginType: accountInfo.loginType,
          accountType: accountInfo.accountType,
          accountId: accountInfo.accountId,
          accountScope: accountInfo.accountScope,
          usageQuota,
          setUsageQuota,
          availableScopes,
          setAvailableScopes,
          productPage,
          updateProductPage,
          isCuriAdmin,
          preferences,
          setPreferences,
        }}
      >
        <UploadsContext.Provider
          value={{
            uploads,
            setUploads,
            jobs,
            setJobs,
            getUploadsAndJobs,
            pulse3dVersions,
            metaPulse3dVersions,
            stiffnessFactorDetails,
            dataTypeDetails,
            defaultUploadForReanalysis,
            setDefaultUploadForReanalysis,
            setPulse3dVersions,
            setMetaPulse3dVersions,
          }}
        >
          <AdvancedAnalysisContext.Provider value={{ advancedAnalysisJobs, getAdvancedAnalysisJobs }}>
            <Layout>
              <ModalWidget
                open={showLoggedOutAlert}
                closeModal={() => {
                  setLoggedOutAlert(false);
                  router.replace("/login", undefined, { shallow: true });
                }}
                header="Attention"
                labels={["You have been logged out due to inactivity"]}
              />
              {getLayout(<Component {...pageProps} />, pageProps.data)}
            </Layout>
          </AdvancedAnalysisContext.Provider>
        </UploadsContext.Provider>
      </AuthContext.Provider>
    </ThemeProvider>
  );
}

export default Pulse;
