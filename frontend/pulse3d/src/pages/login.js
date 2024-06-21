import styled from "styled-components";
import { useState } from "react";
import ButtonWidget from "@/components/basicWidgets/ButtonWidget";
import LoginForm from "@/components/account/LoginForm";
import FormInput from "@/components/basicWidgets/FormInput";
import Image from "next/image";
import { useRouter } from "next/router";
import ModalWidget from "@/components/basicWidgets/ModalWidget";
import { PublicClientApplication } from "@azure/msal-browser";

// required for static export, default loader errors on build
const imageLoader = ({ src }) => {
  return src;
};

// TODO eventually need to find a better to way to handle some of these globally to use across app
const BackgroundContainer = styled.div`
  position: relative;
  display: flex;
  flex-direction: column;
  top: 45px;
  gap: 10px;
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

const ImageButtonContainer = styled.div`
  position: relative;
  width: 250px;
  height: 50px;
  &:hover {
    cursor: pointer;
  }
`;

export default function Login() {
  const router = useRouter();
  const [errorMsg, setErrorMsg] = useState();
  const [emailErrorMsg, setEmailErrorMsg] = useState();
  const [loginType, setLoginType] = useState("User");
  const [userData, setUserData] = useState({});
  const [displayForgotPW, setDisplayForgotPW] = useState(false);
  const [userEmail, setUserEmail] = useState();
  const [inProgress, setInProgress] = useState(false);
  const [emailSent, setEmailSent] = useState(false);
  const [openAccountLocked, setOpenAccountLocked] = useState(false);
  const [accountLockedLabels, setAccountLockedLabels] = useState([]);

  const validateEmail = (email) => {
    const re = /\S+@\S+\.\S+/;
    if (re.test(email) || email.length == 0) setEmailErrorMsg();
    else setEmailErrorMsg("*Please enter a valid email address");
  };

  const submitForm = async () => {
    setInProgress(true);
    setErrorMsg(""); // reset to show user something happened

    const values = Object.values(userData);

    if (values.length === 0 || Object.values(userData).some((v) => v == null || v === "")) {
      setErrorMsg("*All fields are required");
      // this state gets passed to web worker to attempt login request
    } else {
      try {
        let loginURL = `${process.env.NEXT_PUBLIC_USERS_URL}/login`;
        if (loginType === "Admin") {
          loginURL += "/admin";
        }

        const res = await fetch(loginURL, {
          method: "POST",
          body: JSON.stringify({
            ...userData,
            client_type: `dashboard:${process.env.NEXT_PUBLIC_FE_VERSION}`,
          }),
          mode: "no-cors",
        });
        if (res) {
          if (res.status === 200) {
            // route to next page
            if (loginType === "User") {
              router.push("/home");
            } else {
              router.push("/uploads?checkUsage=true", "/uploads");
            }
          } else {
            let errToDisplay = "*Internal error. Please try again later.";

            if (res.status === 401) {
              const errMsg = await res.json();
              errToDisplay = `*${errMsg.detail}`;

              if (errMsg.detail.includes("Account locked")) {
                setAccountLockedLabels([
                  "This account has been locked because it has reached the maximum login attempts.",
                  loginType === "Admin"
                    ? "Please contact CuriBio at contact@curibio.com to unlock this account."
                    : "Please contact your administrator to unlock this account.",
                ]);
                setOpenAccountLocked(true);
              }
            }

            setErrorMsg(errToDisplay);
          }
        }
      } catch (e) {
        console.log("ERROR logging in");
        setErrorMsg("*Internal error. Please try again later.");
      }
    }
    setInProgress(false);
  };

  const submitMicrosoftSSO = async () => {
    try {
      const loginRequest = { scopes: ["email"] };
      const msalConfig = {
        auth: {
          clientId: `${process.env.NEXT_PUBLIC_MICROSOFT_SSO_APP_ID}`,
          authority: `${process.env.NEXT_PUBLIC_MICROSOFT_SSO_AUTHORITY_URI}`,
        },
      };

      const msalPCA = new PublicClientApplication(msalConfig);
      await msalPCA.initialize();

      const response = await msalPCA.loginPopup({
        ...loginRequest,
        redirectUri: "/",
      });
      await handleMicrosoftSSOResponse(response);
    } catch (e) {
      console.log("*submitMicrosoftSSO error: " + e);
      setErrorMsg("*SSO error. Please try again later.");
    }
  };

  async function handleMicrosoftSSOResponse(response) {
    if (response !== null) {
      if (response.idToken) {
        await submitIdToken(response.idToken);
        return;
      } else {
        console.log("handleMicrosoftSSOResponse error: response has no idToken");
      }
    } else {
      console.log("handleMicrosoftSSOResponse error: response is null");
    }
    setErrorMsg("*SSO error. Please try again later.");
  }

  async function submitIdToken(idToken) {
    try {
      let ssoURL = `${process.env.NEXT_PUBLIC_USERS_URL}/sso`;
      if (loginType === "Admin") {
        ssoURL += "/admin";
      }

      const res = await fetch(ssoURL, {
        method: "POST",
        body: JSON.stringify({
          id_token: idToken,
          client_type: `dashboard:${process.env.NEXT_PUBLIC_FE_VERSION}`,
        }),
        mode: "no-cors",
      });

      if (res) {
        if (res.status === 200) {
          if (loginType === "User") {
            router.push("/home");
          } else {
            router.push("/uploads?checkUsage=true", "/uploads");
          }
          return;
        } else {
          console.log("submitIdToken error: response status not OK");
        }
      } else {
        console.log("submitIdToken error: no response");
      }
    } catch (e) {
      console.log("submitIdToken error: " + e);
    }
    setErrorMsg("*SSO error. Please try again later.");
  }

  const onForgetPassword = () => {
    setDisplayForgotPW(true);
  };

  const closePWModal = async (idx) => {
    // reset email error message for every button click on both modals
    setEmailErrorMsg();

    // first modal to appear contains input to enter email address when emailSent is false
    if (emailSent) {
      // this will close the modal that let user know an email has been sent if email is found in DB
      setEmailSent(false);
      setDisplayForgotPW(false);
    } else {
      // if 'Cancel' then just close modal
      if (idx === 0) {
        setDisplayForgotPW(false);
      } else {
        // else if 'Send' then send request to BE to send new password email
        // emailSent to true will change modal labels to let user know it's been sent if email is found associated with an account
        if (!userEmail || userEmail.length === 0) {
          setEmailErrorMsg("*Field required");
        } else {
          try {
            const res = await fetch(
              `${process.env.NEXT_PUBLIC_USERS_URL}/email?email=${encodeURIComponent(
                userEmail
              )}&type=reset&user=${loginType == "User"}`
            );

            if (res) {
              if (res.status === 204) {
                setEmailSent(true);
              } else {
                throw Error();
              }
            }
          } catch (e) {
            console.log("ERROR resetting password");
            setEmailErrorMsg("*Internal server error. Please try again later.");
          }
        }
      }
    }
    // set email back to null after request with email is sent
    setUserEmail();
  };

  return (
    <BackgroundContainer>
      <ModalContainer
        onKeyDown={(e) => {
          if (e.key === "Enter") {
            submitForm();
          }
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
                  setUserData({});
                  setLoginType(type);
                }}
              />
            );
          })}
        </ButtonContainer>
        <LoginForm userData={userData} setUserData={setUserData} loginType={loginType}>
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
      <ImageButtonContainer>
        <Image
          src={"/ms-symbollockup_signin_dark.svg"}
          alt={"Sign in with Microsoft"}
          loader={imageLoader}
          layout={"fill"}
          onClick={submitMicrosoftSSO}
        />
      </ImageButtonContainer>
      <ModalWidget
        open={displayForgotPW}
        width={500}
        closeModal={closePWModal}
        header={emailSent ? "Sent!" : "Reset Password"}
        labels={
          emailSent
            ? [
                "If there's a password-based account associated with that email, we've sent a link to reset the password.",
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
      <ModalWidget
        open={openAccountLocked}
        width={500}
        closeModal={() => setOpenAccountLocked(false)}
        header={"Warning!"}
        labels={accountLockedLabels}
        buttons={["Close"]}
      />
    </BackgroundContainer>
  );
}
