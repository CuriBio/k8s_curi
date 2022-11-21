import styled from "styled-components";
import { useEffect, useState } from "react";
import { useRouter } from "next/router";
import PasswordForm from "@/components/account/PasswordForm";
import ButtonWidget from "@/components/basicWidgets/ButtonWidget";
// TODO eventually need to find a better to way to handle some of these globally to use across app
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

export default function Verify() {
  const router = useRouter();
  const [errorMsg, setErrorMsg] = useState(null);
  const [passwords, setPasswords] = useState({ password1: "", password2: "" });
  // useEffect(() => {
  //   if (router.pathname.includes("verify") && router.query.token) {
  //     verifyEmail(router.query);
  //     // this removes token param from url to make it not visible to users
  //     router.replace("/verify", undefined, { shallow: true });
  //   }
  // }, [router]);

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
    } catch (e) {
      console.log(`ERROR verifying new user account: ${e}`);
      // if error, open error modal to let user know it didn't work
    }
  };

  const submitForm = () => {
    setOpenModal(false);
    // redirect user to login page to exit verify page regardless of outcome
    router.replace("/login", undefined, { shallow: true });
  };

  const onChangePassword = ({ target }) => {
    setPasswords({ ...passwords, [target.id]: target.value });
    console.log(passwords);
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
        <ButtonWidget label={"Submit"} clickFn={submitForm} />
      </ModalContainer>
    </BackgroundContainer>
  );
}
