import Image from "next/image";
import styled from "styled-components";
import DropDownMenu from "@/components/basicWidgets/ButtonDropDown";
import { useRouter } from "next/router";
import UsageProgressWidget from "../basicWidgets/UsageProgressWidget";

// required for static export, default loader errors on build
const imageLoader = ({ src }) => {
  return src;
};

const Header = styled.div`
  background-color: var(--dark-blue);
  height: 65px;
  width: 100%;
  display: flex;
  align-items: center;
  padding: 0 2%;
  position: fixed;
  justify-content: space-between;
  z-index: 5;
  border-bottom: 1px solid var(--dark-gray);
`;

const Container = styled.div`
  height: 100%;
  min-height: 100vh;
  background-color: var(--dark-gray);
  &::-webkit-scrollbar {
    display: none;
  }
`;

const Main = styled.main`
  position: relative;
  min-height: 95vh;
  display: flex;
  justify-content: center;
  align-items: center;
`;

export default function Layout({ children }) {
  const router = useRouter();

  const logoutUser = async () => {
    await fetch(`${process.env.NEXT_PUBLIC_USERS_URL}/logout`, {
      method: "POST",
      body: JSON.stringify({}),
    });
    // should not matter what the response is, should log user out
    router.replace("/login", undefined, { shallow: true });
  };

  return (
    <Container>
      <Header>
        <title>Pulse Analysis</title>
        <link rel="icon" type="image/png" sizes="32x32" href="/favicon-32x32.png" />
        <link rel="icon" type="image/png" sizes="16x16" href="/favicon-16x16.png" />
        <link rel="apple-touch-icon" sizes="180x180" href="/apple-touch-icon.png" />
        <link rel="manifest" href="/site.webmanifest" />
        <link rel="mask-icon" href="/safari-pinned-tab.svg" color="#5bbad5" />
        <meta name="theme-color" content="#ffffff" />
        <a href="https://curibio.com">
          <Image
            src={"/CuriBio_logo_white.png"}
            alt="CuriBio Logo"
            width={90}
            height={35}
            loader={imageLoader}
            style={{ cursor: "pointer" }}
            unoptimized
          />
        </a>
        {!["/login", "/account/verify", "/account/reset"].includes(router.pathname) && (
          <>
            <UsageProgressWidget colorOfTextLabel="white" />
            <DropDownMenu items={["Logout"]} label={"Menu"} handleSelection={logoutUser} />
          </>
        )}
      </Header>
      <Main>{children}</Main>
    </Container>
  );
}
