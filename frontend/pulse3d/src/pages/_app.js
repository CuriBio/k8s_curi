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
  user: ["/uploads", "/upload-form", "/account"],
  admin: ["/uploads", "/new-user", "/users-info"],
};

function Pulse({ Component, pageProps }) {
  const getLayout = Component.getLayout || ((page) => page);
  const router = useRouter();
  const [accountType, setAccountType] = useState();
  const [showLoggedOutAlert, setLoggedOutAlert] = useState(false);
  const [usageQuota, setUsageQuota] = useState();

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
        .then(() => sendSWMessage())
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
        // this prevents the inactivity from popping up when a user is already on the login page or verified page
        // do this with multiple messages
        if (data.usageQuota) setUsageQuota(data.usageQuota);
<<<<<<< HEAD
        if (data.logout && currentPage && !currentPage.includes("/account") && currentPage !== "/login") {
=======

        if (data.logout && currentPage && currentPage !== "/verify" && currentPage !== "/login") {
>>>>>>> RC-12-08-22
          setLoggedOutAlert(true);
        } else if (data.isLoggedIn) {
          // the router pathname is sent to the SW and then sent back here since for some reason this message handler
          setAccountType(data.accountType);
          // if logged in and on a page that shouldn't be accessed, or on the login page, redirect to home page (currently /uploads)
          // TODO Tanner (8/23/22): this probably isn't the best solution for redirecting to other pages. Should look into a better way to do this
          if (currentPage === "/login" || !availablePages[data.accountType].includes(currentPage)) {
            router.replace("/uploads", undefined, { shallow: true });
          }
<<<<<<< HEAD
        } else if (
          !data.isLoggedIn &&
          currentPage &&
          currentPage !== "/login" &&
          !currentPage.includes("/account")
        ) {
=======
        } else if (!data.isLoggedIn && currentPage !== "/login" && currentPage !== "/verify") {
>>>>>>> RC-12-08-22
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
    sendSWMessage();

    // start pinging SW if not on login page to keep alive
    if (!router.pathname.includes("login")) keepSWALive();
    // clear on teardown/page redirections
    return () => clearInterval(swInterval);
  }, [router.pathname]);

  const sendSWMessage = () => {
    if ("serviceWorker" in navigator) {
      navigator.serviceWorker.ready.then((registration) => {
        registration.active.postMessage({
          msgType: "authCheck",
          routerPathname: router.pathname,
        });
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
      <AuthContext.Provider value={{ accountType, usageQuota }}>
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
