import "../styles/globals.css";
import "@fontsource/mulish";
import Layout from "@/components/layouts/Layout";
import { createTheme, ThemeProvider } from "@mui/material/styles";
import { useEffect, createContext, useState } from "react";
import { useRouter } from "next/router";
import ModalWidget from "@/components/basicWidgets/ModalWidget";

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

const availablePages = {
  user: ["/uploads", "/upload-form", "/account", "/account-settings"],
  admin: ["/uploads", "/new-user", "/users-info"],
};

function Pulse({ Component, pageProps }) {
  const getLayout = Component.getLayout || ((page) => page);
  const router = useRouter();
  const [accountType, setAccountType] = useState();
  const [showLoggedOutAlert, setLoggedOutAlert] = useState(false);
  const [usageQuota, setUsageQuota] = useState(null);
  const [defaultUploadForReanalysis, setDefaultUploadForReanalysis] = useState();
  let swInterval = null;
  // register the SW once
  useEffect(() => {
    if ("serviceWorker" in navigator) {
      // env vars need to be set here because service worker does not have access to node process
      navigator.serviceWorker
        .register(
          `/serviceWorker.js?pulse3d_url=${process.env.NEXT_PUBLIC_PULSE3D_URL}&users_url=${process.env.NEXT_PUBLIC_USERS_URL}`,
          { type: "module" }
        )
        .then(navigator.serviceWorker.ready)
        .then((registration) => {
          registration.update();
          console.log("Updating service worker");
        }) // update the service worker
        .then(() =>
          sendSWMessage({
            msgType: "authCheck",
            routerPathname: router.pathname,
          })
        )

        .catch((e) => console.log("SERVICE WORKER ERROR: ", e));

      navigator.serviceWorker.addEventListener("message", ({ data }) => {
        /* --------------------
        Current messages received:

        auth check: {isLoggedIn: bool, accountType: str, routerPathname: str, usageQuota: obj}
        logout: {logout: bool}
        usage: {uploads_reached: bool, jobs_reached: bool}
        ---------------------*/

        // might need auth check to include actual fetch request in SW to check token status if this becomes a problem
        // will not use the correct pathname if directly accessing router.pathname
        const currentPage = data.routerPathname;
        const isAccountPage = currentPage && ["/account/verify", "/account/reset"].includes(currentPage);
        // this prevents the inactivity from popping up when a user is already on the login page or verified page
        // do this with multiple messages
        if (data.logout && !isAccountPage && currentPage !== "/login") {
          setLoggedOutAlert(true);
        } else if (data.isLoggedIn && !isAccountPage) {
          // the router pathname is sent to the SW and then sent back here since for some reason this message handler
          setAccountType(data.accountType);
          // if logged in and on a page that shouldn't be accessed, or on the login page, redirect to home page (currently /uploads)
          // TODO Tanner (8/23/22): this probably isn't the best solution for redirecting to other pages. Should look into a better way to do this
          if (currentPage === "/login" || !availablePages[data.accountType].includes(currentPage)) {
            router.replace("/uploads", undefined, { shallow: true });
          }
        } else if (!data.isLoggedIn && !isAccountPage && currentPage !== "/login") {
          setAccountType(data.accountType);
          // always redirect to login page if not logged in and not an account verification
          // protects unauthorized page access
          router.replace("/login", undefined, { shallow: true });
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

  useEffect(() => {
    //clear default file when user leaves the re-analyze page
    if (router.query.id !== "Re-analyze Existing Upload") {
      setDefaultUploadForReanalysis(null);
    }
  }, [router.query]);

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
          accountType,
          usageQuota,
          setUsageQuota,
          defaultUploadForReanalysis,
          setDefaultUploadForReanalysis,
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
