import Image from "next/image";
import styled from "styled-components";

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
`;

const Container = styled.div`
  height: 100vh;
  background-color: var(--dark-gray);
`;

const Main = styled.main`
  position: relative;
  height: 95vh;
`;

export default function Layout({ children }) {
  return (
    <Container>
      <Header>
        <Image
          src={"CuriBio_logo_white.png"}
          alt="CuriBio Logo"
          width={100}
          height={40}
          loader={imageLoader}
          unoptimized
        />
      </Header>
      <Main>{children}</Main>
    </Container>
  );
}
