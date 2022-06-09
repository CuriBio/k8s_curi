import "../styles/globals.css";
import "@fontsource/mulish";
import Layout from "@/components/layouts/Layout";
import { WorkerWrapper } from "@/components/WorkerWrapper";
import { createTheme, ThemeProvider } from "@mui/material/styles";

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
  const getLayout = Component.getLayout || ((page) => page);

  return (
    <ThemeProvider theme={MUItheme}>
      <WorkerWrapper>
        <Layout>{getLayout(<Component {...pageProps} />)}</Layout>
      </WorkerWrapper>
    </ThemeProvider>
  );
}

export default Pulse;
