import "../styles/globals.css";
import "@fontsource/mulish";
import Layout from "@/components/layouts/Layout";
import { useWorker } from "@/components/hooks/useWorker";
import { createTheme, ThemeProvider } from "@mui/material/styles";
import { useEffect, useState } from "react";

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
  const { error, response } = useWorker(state);
  const getLayout = Component.getLayout || ((page) => page);

  // handles all requests across app so that only one worker gets used to hold auth token
  // eventually create context so it doesn't have to be passed so far
  const makeRequest = (e) => {
    setState(e);
  };

  return (
    <ThemeProvider theme={MUItheme}>
      <Layout>
        {getLayout(
          <Component
            {...pageProps}
            makeRequest={makeRequest}
            response={response}
            error={error}
          />
        )}
      </Layout>
    </ThemeProvider>
  );
}

export default Pulse;
