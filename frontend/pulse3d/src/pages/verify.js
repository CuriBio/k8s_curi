import styled from "styled-components";
import { useEffect, useState } from "react";
import { useRouter } from "next/router";
import PasswordForm from "@/components/account/PasswordForm";
import ButtonWidget from "@/components/basicWidgets/ButtonWidget";
import ModalWidget from "@/components/basicWidgets/ModalWidget";

const BackgroundContainer = styled.div`
  position: relative;
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100%;
`;

const ErrorText = styled.span`
  color: red;
  font-style: italic;
  text-align: left;
  position: relative;
  width: 85%;
  padding-top: 2%;
`;
const InputContainer = styled.div`
  margin-bottom: 17px;
`;
const ModalContainer = styled.div`
  width: 450px;
  background-color: var(--light-gray);
  position: relative;
  border-radius: 3%;
  overflow: hidden;
  box-shadow: 0px 5px 5px -3px rgb(0 0 0 / 30%), 0px 8px 10px 1px rgb(0 0 0 / 20%),
    0px 3px 14px 2px rgb(0 0 0 / 12%);
`;
const Header = styled.div`
  height: 60px;
  background: var(--dark-blue);
  font-size: 22px;
  color: var(--light-gray);
  width: 100%;
  line-height: 2;
  padding: 2% 5%;
  text-align: center;
  margin-bottom: 2%;
`;
const modalLabels = {
  error: {
    header: "Error Occurred!",
    labels: ["Something went wrong while attempting to verify your account."],
    buttons: ["Close"],
  },
};
export default function Verify() {
  const router = useRouter();
  const [errorMsg, setErrorMsg] = useState();
  const [passwords, setPasswords] = useState({ password1: "", password2: "" });
  const [inProgress, setInProgress] = useState(false);
  const [shortTermToken, setShortTermToken] = useState();
  const [openModal, setOpenModal] = useState(false);
  const [modalToDisplay, setModalToDisplay] = useState(modalLabels.error);

  useEffect(() => {
    if (router.pathname.includes("verify") && router.query.token) {
      setShortTermToken(router.query);
      // this removes token param from url to make it not visible to users
      router.replace("/verify", undefined, { shallow: true });
    }
  }, [router]);

  const verify = async () => {
    try {
      // attach jwt token to verify request
      const headers = new Headers({
        "Content-Type": "application/json",
        Authorization: `Bearer ${shortTermToken}`,
      });
      const res = await fetch(`${process.env.NEXT_PUBLIC_USERS_URL}/verify`, {
        method: "PUT",
        body: JSON.stringify(passwords),
        headers,
      });

      if (res.status === 204) {
        // redirect user to login page to exit verify page regardless of outcome
        router.replace("/login", undefined, { shallow: true });
      } else {
        throw Error();
      }
    } catch (e) {
      console.log(`ERROR verifying new user account: ${e}`);
      // if error, open error modal to let user know it didn't work
      setOpenModal(true);
    }
    // always set back to false regardless of response
    setInProgress(false);
  };

  const submitForm = () => {
    if (!errorMsg || errorMsg === "") {
      // set spinner on button component to true
      setInProgress(true);
      verify();
    }
  };

  const onChangePassword = ({ target }) => {
    setPasswords({ ...passwords, [target.id]: target.value });
  };

  const closeModal = () => {
    setOpenModal(false);
    // redirect user to login page to exit verify page regardless of outcome
    router.replace("/login", undefined, { shallow: true });
  };
  return (
    <BackgroundContainer>
      <ModalContainer>
        <Header>Verify Account</Header>
        <InputContainer>
          <PasswordForm
            password1={passwords.password1}
            password2={passwords.password2}
            onChangePassword={onChangePassword}
            setErrorMsg={setErrorMsg}
          >
            <ErrorText id="verifyError" role="errorMsg">
              {errorMsg}
            </ErrorText>
          </PasswordForm>
        </InputContainer>
        <ButtonWidget inProgress={inProgress} label={"Submit"} clickFn={submitForm} />
      </ModalContainer>
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
