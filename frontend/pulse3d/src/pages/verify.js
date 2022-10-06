import styled from "styled-components";
import { useEffect, useState } from "react";
import { useRouter } from "next/router";
import CircularSpinner from "@/components/basicWidgets/CircularSpinner";
import ModalWidget from "@/components/basicWidgets/ModalWidget";

// TODO eventually need to find a better to way to handle some of these globally to use across app
const BackgroundContainer = styled.div`
  position: relative;
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100%;
`;

const ModalContainer = styled.div(
  ({ user }) => `
  height: ${user ? "460px" : "380px"};
  width: 450px;
  background-color: var(--light-gray);
  position: relative;
  border-radius: 3%;
  overflow: hidden;
  box-shadow: 0px 5px 5px -3px rgb(0 0 0 / 30%),
    0px 8px 10px 1px rgb(0 0 0 / 20%), 0px 3px 14px 2px rgb(0 0 0 / 12%);
`
);

const Label = styled.div`
  font-size: 25px;
  position: relative;
  width: 100%;
  text-align: center;
  margin-top: 15px;
`;

const SpinnerContainer = styled.div`
  height: 80%;
  display: flex;
  align-items: center;
  position: relative;
  justify-content: center;
`;
export default function Verify() {
  const router = useRouter();
  const [openErrorModal, setOpenErrorModal] = useState(false);

  useEffect(() => {
    if (router.pathname.includes("verify") && router.query.token) {
      verifyEmail(router.query);
      // this removes token param from url to make it not visible to users
      router.replace("/verify", undefined, { shallow: true });
    }
  }, [router]);

  const verifyEmail = async ({ token }) => {
    try {
      // attach jwt token to verify request
      const headers = new Headers({
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      });
      const res = await fetch(`${process.env.NEXT_PUBLIC_USERS_URL}/verify`, {
        method: "PUT",
        headers,
      });

      if (res.status === 204) {
        // once verified, auto redirect user to login page
        router.replace("/login", undefined, { shallow: true });
      } else {
        // else open error modal to let user know it didn't work
        setOpenErrorModal(true);
      }
    } catch (e) {
      console.log(`ERROR verifying new user account: ${e}`);
      // if error, open error modal to let user know it didn't work
      setOpenErrorModal(true);
    }
  };

  const closeErrorModal = () => {
    setOpenErrorModal(false);
    // redirect user to login page to exit verify page regardless of outcome
    router.replace("/login", undefined, { shallow: true });
  };

  return (
    <BackgroundContainer>
      <ModalContainer>
        <Label>Verifying...</Label>
        <SpinnerContainer>
          <CircularSpinner size={200} />
        </SpinnerContainer>
      </ModalContainer>
      <ModalWidget
        open={openErrorModal}
        closeModal={closeErrorModal}
        header="Error Occurred!"
        labels={["Something went wrong while attempting to verify your account."]}
      />
    </BackgroundContainer>
  );
}
