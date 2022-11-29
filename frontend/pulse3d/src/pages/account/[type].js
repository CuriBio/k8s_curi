import styled from "styled-components";
import { useEffect, useState } from "react";
import { useRouter } from "next/router";
import PasswordForm from "@/components/account/PasswordForm";
import ButtonWidget from "@/components/basicWidgets/ButtonWidget";
import ModalWidget from "@/components/basicWidgets/ModalWidget";
import FormInput from "@/components/basicWidgets/FormInput";

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

const ModalInputContainer = styled.div`
  height: 130px;
  display: flex;
  flex-direction: column;
  align-items: center;
`;

const modalLabels = {
  error: {
    header: "Error Occurred!",
    labels: ["Something went wrong while performing this action. Please try again later."],
    buttons: ["Close"],
  },
  alreadyVerified: {
    header: "Warning!",
    labels: [
      "This account has already been verified.",
      "If you forgot your password, please click 'Forgot Password?' to be sent a new link.",
    ],
    buttons: ["Close"],
  },
  linksBeenUsed: {
    header: "Warning!",
    labels: [
      "This link has already been used.",
      "If you need a new one, please select 'Forgot Password?' again.",
    ],
    buttons: ["Close"],
  },
  expiredLink: {
    header: "Warning!",
    labels: ["This link has expired.", "Please select below to receive a new one."],
    buttons: ["Cancel", "Resend"],
  },
  emailSent: {
    header: "Sent!",
    labels: [
      "If there's an account associated with that email, we've sent a new link.",
      "Please check your inbox.",
    ],
    buttons: ["Close"],
  },
  enterEmail: {
    header: "Confirm",
    labels: [],
    buttons: ["Cancel", "Send"],
  },
};
export default function UpdatePassword() {
  const router = useRouter();
  const [errorMsg, setErrorMsg] = useState();
  const [passwords, setPasswords] = useState({ password1: "", password2: "" });
  const [inProgress, setInProgress] = useState(false);
  const [shortTermToken, setShortTermToken] = useState();
  const [openModal, setOpenModal] = useState(false);
  const [modalToDisplay, setModalToDisplay] = useState(modalLabels.error);
  const [modalHeader, setModalHeader] = useState("Verify Account");
  const [userEmail, setUserEmail] = useState();
  const [emailErrorMsg, setEmailErrorMsg] = useState();
  const { type, token } = router.query;

  useEffect(() => {
    if (type && token) {
      if (["reset", "verify"].includes(type)) {
        setShortTermToken(token);
        // this removes token param from url to make it not visible to users
        router.replace(`/account/${type}`, undefined, { shallow: true });

        if (type === "verify") setModalHeader("Verify Account");
        else if (type === "reset") setModalHeader("Change Password");
      }
    } else if (type && !token && !["reset", "verify"].includes(type)) {
      // protect this page from being a catch all with any path param, redirect to login
      router.replace("/login", undefined, { shallow: true });
    }
  }, [type]);

  const verifyPassword = async () => {
    try {
      // attach jwt token to verify request
      const headers = new Headers({
        "Content-Type": "application/json",
        Authorization: `Bearer ${shortTermToken}`,
      });

      const res = await fetch(`${process.env.NEXT_PUBLIC_USERS_URL}/update`, {
        method: "PUT",
        body: JSON.stringify({ ...passwords, verify: type === "verify" }),
        headers,
      });

      const resBody = await res.json();

      if (res.status === 200) {
        if (!resBody)
          // redirect user to login page to exit verify page regardless of outcome
          router.replace("/login", undefined, { shallow: true });
        else {
          if (resBody.message.includes("already been verified"))
            setModalToDisplay(modalLabels.alreadyVerified);
          else setModalToDisplay(modalLabels.linksBeenUsed);

          setOpenModal(true);
        }
      } else if (res.status === 401) {
        setModalToDisplay(modalLabels.expiredLink);
        setOpenModal(true);
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
    if (passwords.password1 === "" || passwords.password2 == "") setErrorMsg("*All fields are required");
    else if (!errorMsg || errorMsg === "") {
      // set spinner on button component to true
      setInProgress(true);
      verifyPassword();
    }
  };

  const onChangePassword = ({ target }) => {
    setPasswords({ ...passwords, [target.id]: target.value });
  };

  const validateEmail = (email) => {
    const re = /\S+@\S+\.\S+/;
    if (re.test(email) || email.length == 0) setEmailErrorMsg();
    else setEmailErrorMsg("*Please enter a valid email address");
  };

  const resendLink = async () => {
    try {
      return await fetch(`${process.env.NEXT_PUBLIC_USERS_URL}/email?email=${userEmail}&type=${type}`);
    } catch (e) {
      console.log("ERROR resending verification email", e);
      setModalToDisplay(modalLabels.error);
    }
  };

  const closeModal = async (idx) => {
    if (idx === 0) {
      setOpenModal(false);
      // redirect user to login page to exit verify page regardless of outcome
      router.replace("/login", undefined, { shallow: true });
    } else if (modalToDisplay.buttons[idx] === "Resend") {
      setModalToDisplay(modalLabels.enterEmail);
    } else if (modalToDisplay.buttons[idx] === "Send") {
      const res = await resendLink();
      if (res.status === 204) {
        setModalToDisplay(modalLabels.emailSent);
      } else {
        setModalToDisplay(modalLabels.error);
      }
    }
  };

  return (
    <BackgroundContainer>
      <ModalContainer>
        <Header>{modalHeader}</Header>
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
        <ButtonWidget
          inProgress={inProgress}
          label={"Submit"}
          clickFn={submitForm}
          backgroundColor={inProgress ? "var(--teal-green)" : "var(--dark-blue)"}
        />
      </ModalContainer>
      <ModalWidget
        width={500}
        open={openModal}
        closeModal={closeModal}
        header={modalToDisplay.header}
        labels={modalToDisplay.labels}
        buttons={modalToDisplay.buttons}
      >
        {modalToDisplay === modalLabels.enterEmail && (
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
