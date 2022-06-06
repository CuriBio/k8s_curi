import "../styles/globals.css";
import "@fontsource/mulish";
import Layout from "@/components/layouts/Layout";
import { useWorker } from "@/components/hooks/useWorker";
import { createTheme, ThemeProvider } from "@mui/material/styles";
import { useEffect, useState } from "react";
import { useRouter } from "next/router";
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

function Pulse({ Component, pageProps }) {
  const [state, setState] = useState({});
  const [loginStatus, setLoginStatus] = useState(false);
  const { error, response } = useWorker(state);
  const router = useRouter();
  const getLayout = Component.getLayout || ((page) => page);

  useEffect(() => {
    if (response) {
      if (response.status === 200 && response.type === "login") {
        router.push("/uploads"); // routes to next page
        setLoginStatus(true);
      } else if (response.status === 204 && response.type === "logout") {
        router.push("/login");
        setLoginStatus(false);
      }
    }
  }, [response]);

  useEffect(() => {
    if (error && error.status === 401 && router.pathname !== "/login") {
      router.push("/login"); // routes back to login page when receiving unauthorized and not already on login
      setLoginStatus(false);
    }
  }, [error]);

  return (
    <ThemeProvider theme={MUItheme}>
      <Layout loginStatus={loginStatus} makeRequest={(e) => setState(e)}>
        {getLayout(
          <Component
            {...pageProps}
            makeRequest={(e) => setState(e)}
            response={response}
            error={error}
            loginStatus={loginStatus}
          />
        )}
      </Layout>
    </ThemeProvider>
  );
}

export default Pulse;
