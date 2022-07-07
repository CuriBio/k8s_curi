import styled from "styled-components";
import { useContext, useState } from "react";
import ButtonWidget from "@/components/basicWidgets/ButtonWidget";
import LoginForm from "@/components/account/LoginForm";
import { AuthContext } from "./_app";
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
  const [userType, setUserType] = useState("User");
  const [userData, setUserData] = useState({});
  const { setAccountType } = useContext(AuthContext);

  const submitForm = async () => {
    setErrorMsg(""); // reset to show user something happened

    if (Object.values(userData).includes(""))
      setErrorMsg("*All fields are required");
    // this state gets passed to web worker to attempt login request
    else {
      // const res = await fetch("http://localhost/users/login", {
      const res = await fetch("http://localhost/login", {
        method: "POST",
        body: JSON.stringify(userData),
      });

      if (res) {
        if (res.status === 200) {
          setAccountType(userType); // set account type globally
          userType === "Admin"
            ? router.push("/admin/new-user")
            : router.push("/uploads"); // routes to next page
        } else {
          res.status === 401 || res.status === 422
            ? setErrorMsg("*Invalid credentials. Try again.")
            : setErrorMsg("*Internal error. Please try again later.");
        }
      }
    }
  };

  return (
    <BackgroundContainer>
      <ModalContainer user={userType === "User"}>
        <ButtonContainer>
          {["User", "Admin"].map((type, idx) => {
            const isSelected = type === userType;
            return (
              <ButtonWidget
                label={type}
                key={idx}
                isSelected={isSelected}
                backgroundColor={
                  isSelected ? "var(--teal-green)" : "var(--dark-blue)"
                }
                clickFn={() => setUserType(type)}
              />
            );
          })}
        </ButtonContainer>
        <LoginForm
          userData={userData}
          setUserData={setUserData}
          userType={userType}
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
