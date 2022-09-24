import styled from "styled-components";
import { useState } from "react";
import ButtonWidget from "@/components/basicWidgets/ButtonWidget";
import LoginForm from "@/components/account/LoginForm";
import { useRouter } from "next/router";
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

const ErrorText = styled.span`
  color: red;
  font-style: italic;
  text-align: left;
  position: relative;
  width: 80%;
  padding-top: 2%;
`;

const ButtonContainer = styled.div`
  display: flex;
  flex-direction: row;
`;

export default function Login() {
  const router = useRouter();
  const [errorMsg, setErrorMsg] = useState(null);
  const [loginType, setLoginType] = useState("User");
  const [userData, setUserData] = useState({});

  const submitForm = async () => {
    setErrorMsg(""); // reset to show user something happened

    if (Object.values(userData).includes(""))
      setErrorMsg("*All fields are required");
    // this state gets passed to web worker to attempt login request
    else {
      try {
        const res = await fetch(`${process.env.NEXT_PUBLIC_USERS_URL}/login`, {
          method: "POST",
          body: JSON.stringify(userData),
          mode: "no-cors",
        });

        if (res) {
          if (res.status === 200) {
            router.push("/uploads"); // routes to next page
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
  };

  return (
    <BackgroundContainer>
      <ModalContainer user={loginType === "User"}>
        <ButtonContainer>
          {["User", "Admin"].map((type, idx) => {
            const isSelected = type === loginType;
            return (
              <ButtonWidget
                label={type}
                key={idx}
                isSelected={isSelected}
                backgroundColor={
                  isSelected ? "var(--teal-green)" : "var(--dark-blue)"
                }
                clickFn={() => {
                  setUserData({});
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
        >
          <ErrorText id="loginError" role="errorMsg">
            {errorMsg}
          </ErrorText>
        </LoginForm>
        <ButtonWidget label={"Submit"} clickFn={submitForm} />
      </ModalContainer>
    </BackgroundContainer>
  );
}
