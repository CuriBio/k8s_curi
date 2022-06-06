import Image from "next/image";
import styled from "styled-components";
import DropDownMenu from "@/components/basicWidgets/DropDownMenu";
// required for static export, default loader errors on build
const imageLoader = ({ src }) => {
  return `/public/${src}`;
};

const Header = styled.div`
  background-color: var(--dark-blue);
  height: 5vh;
  width: 100vw;
  display: flex;
  align-items: center;
  padding: 0 2%;
  position: relative;
  justify-content: space-between;
`;

const Container = styled.div`
  height: 100vh;
  background-color: var(--dark-gray);
`;

const Main = styled.main`
  position: relative;
  height: 95vh;
`;

export default function Layout({ children, loginStatus, makeRequest }) {
  const logoutUser = () => {
    makeRequest({
      type: "logout",
      endpoint: "logout",
      method: "post",
    });
  };

  return (
    <Container>
      <Header>
        <Image
          src={"CuriBio_logo_white.png"}
          alt="CuriBio Logo"
          width={90}
          height={35}
          loader={imageLoader}
          unoptimized
        />
        {!loginStatus || (
          <DropDownMenu
            items={["Logout"]}
            label={"Menu"}
            handleSelection={logoutUser}
          />
        )}
      </Header>
      <Main>{children}</Main>
    </Container>
  );
}
