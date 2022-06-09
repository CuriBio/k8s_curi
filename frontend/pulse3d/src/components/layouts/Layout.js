import Image from "next/image";
import styled from "styled-components";
import DropDownMenu from "@/components/basicWidgets/DropDownMenu";
import { useEffect, useContext } from "react";
import { WorkerContext } from "@/components/WorkerWrapper";

// required for static export, default loader errors on build
const imageLoader = ({ src }) => {
  return `/public/${src}`;
};

const Header = styled.div`
  background-color: var(--dark-blue);
  height: 45px;
  width: 100vw;
  display: flex;
  align-items: center;
  padding: 0 2%;
  position: relative;
  justify-content: space-between;
`;

const Container = styled.div`
  height: 100%;
  background-color: var(--dark-gray);
`;

const Main = styled.main`
  position: relative;
  height: 95vh;
`;

export default function Layout({ children }) {
  const { setReqParams, response, setLoginStatus, loginStatus, router } =
    useContext(WorkerContext);

  const logoutUser = () => {
    setReqParams({
      type: "logout",
      endpoint: "users/logout",
      method: "post",
    });
  };

  useEffect(() => {
    if (response && response.status === 204 && response.type === "logout") {
      router.push("/login");
      setLoginStatus(false);
    }
  }, [response]);

  return (
    <Container>
      <Header>
        <title>Pulse Analysis</title>
        <link
          rel="icon"
          type="image/png"
          sizes="32x32"
          href="/favicon-32x32.png"
        />
        <link
          rel="icon"
          type="image/png"
          sizes="16x16"
          href="/favicon-16x16.png"
        />
        <link
          rel="apple-touch-icon"
          sizes="180x180"
          href="/apple-touch-icon.png"
        />
        <link rel="manifest" href="/site.webmanifest" />
        <link rel="mask-icon" href="/safari-pinned-tab.svg" color="#5bbad5" />
        <meta name="theme-color" content="#ffffff" />
        <Image
          src={"CuriBio_logo_white.png"}
          alt="CuriBio Logo"
          width={90}
          height={35}
          loader={imageLoader}
          unoptimized
        />
        {!loginStatus || <DropDownMenu items={["Logout"]} label={"Menu"} handleSelection={logoutUser} />}
      </Header>
      <Main>{children}</Main>
    </Container>
  );
}
