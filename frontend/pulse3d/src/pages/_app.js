import "../styles/globals.css";
import "@fontsource/mulish";
import Layout from "@/components/Layout";

function Pulse({ Component, pageProps }) {
  return (
    <Layout>
      <Component {...pageProps} />
    </Layout>
  );
}

export default Pulse;
