import styled from "styled-components";
import { useEffect, useState, useContext } from "react";
import ButtonWidget from "@/components/basicWidgets/ButtonWidget";
import { useRouter } from "next/router";
// TODO eventually need to find a better to way to handle some of these globally to use across app
const BackgroundContainer = styled.div`
  position: relative;
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100%;
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

export default function Login() {
  const router = useRouter();
  const [errorMsg, setErrorMsg] = useState(null);
  const [userData, setUserData] = useState({
    customer_id: "",
    username: "",
    password: "",
  });

  const submitForm = async () => {
    setErrorMsg(""); // reset to show user something happened

    if (Object.values(userData).includes(""))
      setErrorMsg("*All fields are required");
    // this state gets passed to web worker to attempt login request
    else {
      const res = await fetch("http://localhost/users/login", {
        method: "POST",
        body: JSON.stringify(userData),
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
            onChange={(e) =>
              setUserData({ ...userData, username: e.target.value })
            }
          />
          <Label htmlFor="password">Password</Label>
          <Field
            id="password"
            type="password"
            autocomplete="current-password" // chrome warns without this attribute
            placeholder="Password"
            onChange={(e) =>
              setUserData({ ...userData, password: e.target.value })
            }
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
