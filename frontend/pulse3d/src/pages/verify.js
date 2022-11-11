import styled from "styled-components";
import { useEffect, useState } from "react";
import { useRouter } from "next/router";
import ModalWidget from "@/components/basicWidgets/ModalWidget";

// TODO eventually need to find a better to way to handle some of these globally to use across app
const BackgroundContainer = styled.div`
  position: relative;
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100%;
`;

const modalLabels = {
  success: {
    header: "Success!",
    labels: ["Your account is now ready to be used, please proceed to the login page."],
    buttons: ["Continue"],
  },
  error: {
    header: "Error Occurred!",
    labels: ["Something went wrong while attempting to verify your account."],
    buttons: ["Close"],
  },
};

export default function Verify() {
  const router = useRouter();
  const [openModal, setOpenModal] = useState(false);
  const [modalToDisplay, setModalToDisplay] = useState(modalLabels.success);

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

      res.status === 204 ? setModalToDisplay(modalLabels.success) : setModalToDisplay(modalLabels.error);

      // open modal after setting correct labels
      setOpenModal(true);
    } catch (e) {
      console.log(`ERROR verifying new user account: ${e}`);
      // if error, open error modal to let user know it didn't work
      setModalToDisplay(modalLabels.error);
      setOpenModal(true);
    }
  };

  const closeModal = () => {
    setOpenModal(false);
    // redirect user to login page to exit verify page regardless of outcome
    router.replace("/login", undefined, { shallow: true });
  };

  return (
    <BackgroundContainer>
      <ModalWidget
        width={500}
        open={openModal}
        closeModal={closeModal}
        header={modalToDisplay.header}
        labels={modalToDisplay.labels}
        buttons={modalToDisplay.buttons}
      />
    </BackgroundContainer>
  );
}
