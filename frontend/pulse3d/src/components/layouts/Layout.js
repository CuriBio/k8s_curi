import Image from "next/image";
import styled from "styled-components";
import DropDownMenu from "@/components/basicWidgets/ButtonDropDown";
import { useRouter } from "next/router";
import UsageProgressWidget from "../account/UsageProgressWidget";
import EmailIcon from "@mui/icons-material/Email";
import NavigateBeforeIcon from "@mui/icons-material/NavigateBefore";
import { styled as muiStyled } from "@mui/material/styles";
import { AuthContext } from "@/pages/_app";
import { useEffect, useState, useContext } from "react";

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

const LogoContainer = styled.a`
  margin-right: 30px;
  margin-top: 4px;
`;

const NavHomeIcon = muiStyled(NavigateBeforeIcon)`
  position: relative;
  font-size: 30px;
`;

const NotificationMessagesIcon = muiStyled(EmailIcon)`
  font-size: 30px;
  cursor: pointer;
  &:hover {
    color: var(--teal-green);
  }
`;

const NavHomeContainer = styled.div`
  color: var(--dark-gray);
  display: flex;
  align-items: center;
  flex-direction: row;
  line-height: 2.5;
  cursor: pointer;
  &:hover {
    color: var(--light-gray);
  }
`;

const MessagesAndMenuContainer = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
`;

const HeaderSideSectContainer = styled.div`
  width: 120px;
`;

const HeaderCenterSectContainer = styled.div`
  display: flex;
  flex-direction: row;
`;

export default function Layout({ children }) {
  const [showHomeArrow, setShowHomeArrow] = useState(false);
  const [envelopeColor, setEnvelopeColor] = useState("var(--light-gray)");

  const router = useRouter();
  const { accountType } = useContext(AuthContext);
  const isAuthorizedPage = !["/login", "/account/verify", "/account/reset"].includes(router.pathname);

  useEffect(() => {
    setShowHomeArrow(accountType === "user" && isAuthorizedPage && router.pathname !== "/home");
  }, [accountType, router]);

  useEffect(() => {
    setEnvelopeColor(
      router.pathname === "/notification-messages" ? "var(--teal-green)" : "var(--light-gray)"
    );
  }, [router]);

  const logoutUser = async () => {
    try {
      await fetch(`${process.env.NEXT_PUBLIC_USERS_URL}/logout`, {
        method: "POST",
        body: JSON.stringify({}),
      });
    } catch (e) {}

    // should not matter what the response is, should log user out
    router.replace("/login", undefined, { shallow: true });
  };

  const navigateHome = () => {
    router.replace("/home");
  };

  const navigateMessages = () => {
    router.replace("/notification-messages");
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
        <HeaderSideSectContainer>
          {showHomeArrow && (
            <NavHomeContainer onClick={navigateHome}>
              <NavHomeIcon />
              Home
            </NavHomeContainer>
          )}
        </HeaderSideSectContainer>
        <HeaderCenterSectContainer>
          <LogoContainer href="https://curibio.com">
            <Image
              src={"/CuriBio_logo_white.png"}
              alt="CuriBio Logo"
              width={90}
              height={35}
              loader={imageLoader}
              style={{ cursor: "pointer" }}
              unoptimized
            />
          </LogoContainer>
          {isAuthorizedPage && router.pathname !== "/home" && (
            <UsageProgressWidget colorOfTextLabel="white" />
          )}
        </HeaderCenterSectContainer>
        <HeaderSideSectContainer>
          {isAuthorizedPage && (
            <MessagesAndMenuContainer>
              <NotificationMessagesIcon sx={{ color: envelopeColor }} onClick={navigateMessages} />
              <DropDownMenu items={["Logout"]} label={"Menu"} handleSelection={logoutUser} />
            </MessagesAndMenuContainer>
          )}
        </HeaderSideSectContainer>
      </Header>
      <Main>{children}</Main>
    </Container>
  );
}
