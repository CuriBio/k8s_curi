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
  User: ["/uploads", "/upload-form", "/account"],
  Admin: ["/uploads", "/new-user"],
};

function Pulse({ Component, pageProps }) {
  const getLayout = Component.getLayout || ((page) => page);
  const router = useRouter();
  const [authCheck, setAuthCheck] = useState(false);
  const [accountType, setAccountType] = useState();
  const [showLoggedOutAlert, setLoggedOutAlert] = useState(false);

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
        // data returned is a boolean if auth tokens are present. Otherwise return user to login
        // might need auth check to include actual fetch request in SW to check token status if this becomes a problem
        if (data.logout) {
          setLoggedOutAlert(true);
          return;
        }
        setAuthCheck(data.authCheck);
        setAccountType(data.accountType);
        console.log(
          "AUTH CHECK:",
          data.authCheck,
          data.accountType,
          data.routerPathname
        );

        if (!data.authCheck) {
          router.replace("/login", undefined, { shallow: true });
        } else if (
          // the router pathname is send to the SW and back here since for some reason this message handler
          // will not use the correct pathname if directly accessing router.pathname
          // TODO try using router.pathname again
          !availablePages[data.accountType].includes(data.routerPathname)
        ) {
          console.log(
            `${data.routerPathname} is not available to ${data.accountType}s`
          );
          // Tanner (8/23/22): TODO this isn't the best solution for preventing navigation pages
          // that the given account type shouldn't be able to reach. Should look into a better way to do this
          router.replace("/uploads", undefined, { shallow: true });
        }
      });
    }
  }, []);

  useEffect(() => {
    // sends message to active SW to check if user is authenticated if not login page. Login page handles own clearing.
    console.log("NEW PATH:", router.pathname);
    sendSWMessage();
  }, [router.pathname]);

  useEffect(() => {
    if (accountType) {
      // Tanner (8/23/22): guard against case where the page is reloaded and accountType changes back to null
      sendSetAccountTypeMsg();
    }
  }, [accountType]);

  const sendSWMessage = () => {
    console.log("sendSWMessage:", router.pathname);
    if ("serviceWorker" in navigator) {
      if (router.pathname !== "/login")
        navigator.serviceWorker.ready.then((registration) => {
          registration.active.postMessage({
            msgType: "authCheck",
            routerPathname: router.pathname,
          });
        });
      else {
        // clear tokens if login page has been reached
        navigator.serviceWorker.ready.then((registration) => {
          registration.active.postMessage({ msgType: "clear" });
        });
        // set context state to false once tokens are cleared
        setAuthCheck(false);
      }
    }
  };

  const sendSetAccountTypeMsg = () => {
    if ("serviceWorker" in navigator) {
      navigator.serviceWorker.ready.then((registration) => {
        registration.active.postMessage({
          msgType: "setAccountType",
          accountType,
        });
      });
    }
  };

  return (
    <ThemeProvider theme={MUItheme}>
      <AuthContext.Provider value={{ authCheck, accountType, setAccountType }}>
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
