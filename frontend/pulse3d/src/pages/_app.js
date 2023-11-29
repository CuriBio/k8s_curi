import "../styles/globals.css";
import "@fontsource/mulish";
import Layout from "@/components/layouts/Layout";
import { createTheme, ThemeProvider } from "@mui/material/styles";
import { useEffect, createContext, useState } from "react";
import { useRouter } from "next/router";
import ModalWidget from "@/components/basicWidgets/ModalWidget";
import { deepCopy } from "@/utils/generic";

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

// TODO make all pages scope based?
const allAvailablePages = {
  user: ["/home", "/uploads", "/upload-form", "/account", "/account-settings", "/metrics"],
  admin: ["/uploads", "/add-new-account", "/users-info", "/account-settings"],
};

const getAvailablePages = (accountInfo) => {
  if (!allAvailablePages[accountInfo.accountType]) {
    // accountType isn't set yet
    return [];
  }

  const pages = deepCopy(allAvailablePages[accountInfo.accountType]);
  // TODO find a way to define these only once and share with the ControlPanel component
  const productionConsoleScopes = [
    "mantarray:serial_number:edit",
    "mantarray:firmware:edit",
    "mantarray:firmware:info",
  ];
  if (accountInfo.accountScope.some((scope) => productionConsoleScopes.includes(scope))) {
    pages.push("/production-console");
  }
  return pages;
};

function Pulse({ Component, pageProps }) {
  const getLayout = Component.getLayout || ((page) => page);
  const router = useRouter();
  const [accountInfo, setAccountInfo] = useState({});
  const [showLoggedOutAlert, setLoggedOutAlert] = useState(false);
  const [usageQuota, setUsageQuota] = useState();
  const [availableScopes, setAvailableScopes] = useState({ customer: [], user: [] });
  const [isCuriAdmin, setIsCuriAdmin] = useState(false);

  // TODO defaulting to mantarray for customer accounts until it's decided how to handle usage for multiple products
  const [productPage, setProductPage] = useState("mantarray");

  let swInterval = null;
  // register the SW once
  useEffect(() => {
    if ("serviceWorker" in navigator) {
      // env vars need to be set here because service worker does not have access to node process
      navigator.serviceWorker
        .register(
          `/serviceWorker.js?mantarray_url=${process.env.NEXT_PUBLIC_MANTARRAY_URL}&users_url=${process.env.NEXT_PUBLIC_USERS_URL}&pulse3d_url=${process.env.NEXT_PUBLIC_PULSE3D_URL}`,
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
            if (currentPage !== "/login") {
              // logged out due to inactivity message shouldn't show if already on the login page
              setLoggedOutAlert(true);
            }
          } else if (data.msgType === "authCheck") {
            const newAccountInfo = data.accountInfo;

            if (data.isLoggedIn) {
              setAvailableScopes({ customer: data.customerScopes, user: data.userScopes });
              setIsCuriAdmin(newAccountInfo.accountScope.find((scope) => scope === "curi:admin"));
              // the router pathname must be sent to the SW and then sent back here since for some reason this message handler can't grab the current page
              setAccountInfo(newAccountInfo);
              // if logged in and on a page that shouldn't be accessed, or if on the login page, redirect to home page (currently /uploads)
              if (currentPage === "/login" || !getAvailablePages(newAccountInfo).includes(currentPage)) {
                // TODO Tanner (8/23/22): this probably isn't the best solution for redirecting to other pages. Should look into a better way to do this
                router.replace(accountInfo.accountType == "User" ? " /home" : "/uploads", undefined, {
                  shallow: true,
                });
              }
            } else if (currentPage !== "/login") {
              // always redirect to login page if not logged in
              setAccountInfo(newAccountInfo);
              router.replace("/login", undefined, { shallow: true });
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
    });

    // start pinging SW if not on login page to keep alive
    if (!["/login", "/account/verify", "/account/reset"].includes(router.pathname)) keepSWALive();
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

  return (
    <ThemeProvider theme={MUItheme}>
      <AuthContext.Provider
        value={{
          accountType: accountInfo.accountType,
          accountId: accountInfo.accountId,
          accountScope: accountInfo.accountScope,
          usageQuota,
          setUsageQuota,
          availableScopes,
          setAvailableScopes,
          productPage,
          setProductPage,
          isCuriAdmin,
        }}
      >
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
      </AuthContext.Provider>
    </ThemeProvider>
  );
}

export default Pulse;
