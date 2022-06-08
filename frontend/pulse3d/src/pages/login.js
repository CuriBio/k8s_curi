import styled from "styled-components";
import { useEffect, useState } from "react";
import ButtonWidget from "@/components/basicWidgets/ButtonWidget";

// TODO eventually need to find a better to way to handle some of these globally to use across app
const BackgroundContainer = styled.div`
  position: relative;
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100vh;
`;

const ModalContainer = styled.div`
  height: 400px;
  width: 450px;
  background-color: var(--light-gray);
  position: relative;
  border-radius: 3%;
  overflow: hidden;
`;

const InputContainer = styled.div`
  height: 85%;
  position: relative;
  display: flex;
  flex-direction: column;
  justify-content: space-evenly;
  align-items: center;
  padding: 5%;
  width: inherit;
`;

const Form = styled.form`
  height: inherit;
  position: relative;
  display: flex;
  flex-direction: column;
  width: inherit;
`;

const formStyle = [
  `
  position: relative;
  width: 80%;
  height: 40px;
  padding: 5px;
`,
];

const Field = styled.input(formStyle);

const Label = styled.label(formStyle);

const ErrorText = styled.span`
  color: red;
  font-style: italic;
  text-align: left;
  position: relative;
  width: 80%;
  padding-top: 2%;
`;

export default function Login({ makeRequest, error, response }) {
  const [errorMsg, setErrorMsg] = useState(null);
  const [userData, setUserData] = useState({
    customer_id: "",
    username: "",
    password: "",
  });

  useEffect(() => {
    // defaults to undefined when webworker state resets
    if (error && error.status && error.type === "login")
      error.status === 401 || error.status === 422
        ? setErrorMsg("*Invalid credentials. Try again.")
        : setErrorMsg("*Internal error. Please try again later.");
  }, [error]);

  const submitForm = async () => {
    setErrorMsg(""); // reset to show user something happened

    if (Object.values(userData).includes("")) setErrorMsg("*All fields are required");
    // this state gets passed to web worker to attempt login request
    else {
      makeRequest({
        method: "post",
        endpoint: "users/login",
        body: userData,
        type: "login",
      });
    }
  };

  return (
    <BackgroundContainer>
      <ModalContainer>
        <InputContainer>
          <Label htmlFor="customer_id">Customer ID</Label>
          <Field
            id="customer_id" // must be snakecase to post to backend
            placeholder="CuriBio"
            onChange={(e) => {
              setUserData({
                ...userData,
                customer_id: e.target.value,
              });
            }}
          />
          <Label htmlFor="username">Username</Label>
          <Field
            id="username"
            placeholder="User"
            onChange={(e) => setUserData({ ...userData, username: e.target.value })}
          />
          <Label htmlFor="password">Password</Label>
          <Field
            id="password"
            type="password"
            placeholder="Password"
            autoComplete="password" // chrome warns without this attribute
            onChange={(e) => setUserData({ ...userData, password: e.target.value })}
          />
          <ErrorText id="loginError" role="errorMsg">
            {errorMsg}
          </ErrorText>
        </InputContainer>
        <ButtonWidget label={"Submit"} clickFn={submitForm} />
      </ModalContainer>
    </BackgroundContainer>
  );
}
