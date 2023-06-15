import styled from "styled-components";
import { useState } from "react";
import ButtonWidget from "@/components/basicWidgets/ButtonWidget";
import LoginForm from "@/components/account/LoginForm";
import FormInput from "@/components/basicWidgets/FormInput";
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

const ModalContainer = styled.div`
  width: 450px;
  background-color: var(--light-gray);
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  border-radius: 3%;
  overflow: hidden;
  box-shadow: 0px 5px 5px -3px rgb(0 0 0 / 30%), 0px 8px 10px 1px rgb(0 0 0 / 20%),
    0px 3px 14px 2px rgb(0 0 0 / 12%);
`;

const ErrorText = styled.span`
  color: red;
  font-style: italic;
  text-align: left;
  position: relative;
  width: 85%;
  padding-top: 2%;
  font-size: 15px;
`;

const ButtonContainer = styled.div`
  display: flex;
  flex-direction: row;
  width: 100%;
`;
const ForgotPWLabel = styled.span`
  font-style: italic;
  font-size: 15px;
  color: var(--light-blue);
  padding-left: 30%;
  margin-bottom: 3%;
  &:hover {
    color: var(--teal-green);
    cursor: pointer;
    text-decoration: underline;
  }
`;

const ModalInputContainer = styled.div`
  height: 130px;
  display: flex;
  flex-direction: column;
  align-items: center;
`;

export default function Login() {
  const router = useRouter();
  const [errorMsg, setErrorMsg] = useState();
  const [emailErrorMsg, setEmailErrorMsg] = useState();
  const [loginType, setLoginType] = useState("User");
  const [userData, setUserData] = useState({ service: "pulse3d" });
  const [displayForgotPW, setDisplayForgotPW] = useState(false);
  const [userEmail, setUserEmail] = useState();
  const [inProgress, setInProgress] = useState(false);
  const [emailSent, setEmailSent] = useState(false);

  const validateEmail = (email) => {
    const re = /\S+@\S+\.\S+/;
    if (re.test(email) || email.length == 0) setEmailErrorMsg();
    else setEmailErrorMsg("*Please enter a valid email address");
  };

  const submitForm = async () => {
    setInProgress(true);
    setErrorMsg(""); // reset to show user something happened

    if (Object.values(userData).includes("")) {
      setErrorMsg("*All fields are required");
      // this state gets passed to web worker to attempt login request
    } else {
      try {
        console.log(navigator.ServiceWorker);
        const res = await fetch(`${process.env.NEXT_PUBLIC_USERS_URL}/login`, {
          method: "POST",
          body: JSON.stringify({ ...userData, client_type: "dashboard" }),
          mode: "no-cors",
        });

        if (res) {
          if (res.status === 200) {
            router.push("/uploads?checkUsage=true", "/uploads"); // routes to next page
          } else {
            res.status === 401 || res.status === 422
              ? setErrorMsg("*Invalid credentials. Try again.")
              : setErrorMsg("*Internal error. Please try again later.");
          }
        }
      } catch (e) {
        console.log("ERROR logging in");
        setErrorMsg("*Internal error. Please try again later.");
      }
    }
    setInProgress(false);
  };

  const onForgetPassword = () => {
    setDisplayForgotPW(true);
  };

  const closePWModal = async (idx) => {
    // reset email error message for every button click on both modals
    setEmailErrorMsg();

    // first modal to appear contains input to enter email address when emailSent is false
    if (!emailSent) {
      // if 'Cancel' then just close modal
      if (idx === 0) {
        setDisplayForgotPW(false);
      } else {
        // else if 'Send' then send request to BE to send new password email
        // emailSent to true will change modal labels to let user know it's been sent if email is found associated with an account
        if (!userEmail || userEmail.length === 0) setEmailErrorMsg("*Field required");
        else {
          try {
            const res = await fetch(
              `${process.env.NEXT_PUBLIC_USERS_URL}/email?email=${userEmail}&type=reset&user=${
                loginType == "User"
              }`
            );

            if (res) {
              if (res.status === 204) {
                setEmailSent(true);
              } else throw Error();
            }
          } catch (e) {
            console.log("ERROR resetting password");
            setEmailErrorMsg("*Internal server error. Please try again later.");
          }
        }
      }
    } else {
      // this will close the modal that let user know an email has been sent if email is found in DB
      setEmailSent(false);
      setDisplayForgotPW(false);
    }
    // set email back to null after request with email is sent
    setUserEmail();
  };

  return (
    <BackgroundContainer>
      <ModalContainer
        onKeyDown={(e) => {
          e.key === "Enter" ? submitForm() : null;
        }}
      >
        <ButtonContainer>
          {["User", "Admin"].map((type, idx) => {
            const isSelected = type === loginType;
            return (
              <ButtonWidget
                label={type}
                key={idx}
                isSelected={isSelected}
                backgroundColor={isSelected ? "var(--teal-green)" : "var(--dark-blue)"}
                clickFn={() => {
                  setErrorMsg("");
                  setUserData({ service: "pulse3d" });
                  setLoginType(type);
                }}
              />
            );
          })}
        </ButtonContainer>
        <LoginForm
          userData={userData}
          setUserData={setUserData}
          loginType={loginType}
          submitForm={submitForm}
        >
          <ErrorText id="loginError" role="errorMsg">
            {errorMsg}
          </ErrorText>
        </LoginForm>
        <ForgotPWLabel onClick={onForgetPassword}>Forgot Password?</ForgotPWLabel>
        <ButtonWidget
          label={"Submit"}
          clickFn={submitForm}
          inProgress={inProgress}
          backgroundColor={inProgress ? "var(--teal-green)" : "var(--dark-blue)"}
        />
      </ModalContainer>
      <ModalWidget
        open={displayForgotPW}
        width={500}
        closeModal={closePWModal}
        header={emailSent ? "Sent!" : "Reset Password"}
        labels={
          emailSent
            ? [
                "If there's an account associated with that email, we've sent a link to reset the password.",
                "Please check your inbox.",
              ]
            : []
        }
        buttons={emailSent ? ["Close"] : ["Cancel", "Send"]}
      >
        {!emailSent && (
          <ModalInputContainer>
            <FormInput
              name="email"
              label="Enter Email"
              placeholder="user@curibio.com"
              value={userEmail}
              onChangeFn={(e) => {
                validateEmail(e.target.value);
                setUserEmail(e.target.value);
              }}
            />
            <ErrorText id="emailError" role="errorMsg">
              {emailErrorMsg}
            </ErrorText>
          </ModalInputContainer>
        )}
      </ModalWidget>
    </BackgroundContainer>
  );
}
