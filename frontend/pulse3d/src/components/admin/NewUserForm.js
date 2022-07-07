import styled from "styled-components";
import { useState } from "react";
import ButtonWidget from "@/components/basicWidgets/ButtonWidget";
import { useRouter } from "next/router";

const InputContainer = styled.div`
  height: 460px;
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
  line-height: 2;
`,
];

const Field = styled.input(formStyle);
const Label = styled.label(formStyle);

const ModalContainer = styled.div`
  height: 600px;
  width: 800px;
  background-color: white;
  position: relative;
  border-radius: 3%;
  overflow: hidden;
  margin-top: 100px;
`;
const ErrorText = styled.span`
  color: red;
  font-style: italic;
  text-align: left;
  position: relative;
  width: 80%;
  padding-top: 2%;
`;

const Header = styled.h2`
  position: relative;
  text-align: center;
  background-color: var(--dark-blue);
  align-content: center;
  color: var(--light-gray);
  height: 80px;
  margin: auto;
  line-height: 3;
`;

const ButtonContainer = styled.div`
  display: flex;
  flex-direction: row;
`;

export default function NewUserForm() {
  const router = useRouter();
  const [userData, setUserData] = useState({
    email: "",
    username: "",
    password1: "",
    password2: "",
  });

  const [errorMsg, setErrorMsg] = useState("");

  const resetForm = () => {
    setErrorMsg(""); // reset to show user something happened

    setUserData({
      email: "",
      username: "",
      password1: "",
      password2: "",
    });
  };

  const submitForm = async () => {
    setErrorMsg(""); // reset to show user something happened

    if (Object.values(userData).includes(""))
      setErrorMsg("* All fields are required");
    // this state gets passed to web worker to attempt login request
    else {
      const res = await fetch("http://localhost/register", {
        method: "POST",
        body: JSON.stringify(userData),
      });

      if (res) {
        if (res.status === 201) setErrorMsg("");
        else if (res.status === 422) {
          const error = await res.json();
          const message = error.detail[0].msg;
          setErrorMsg(`* ${message}`);
        } else if (res.status === 401)
          router.push("/login", null, { shallow: true });
        else setErrorMsg(`* Internal server error. Try again later.`);
      }
    }
  };
  return (
    <ModalContainer>
      <Header>New User Details</Header>
      <InputContainer>
        <Label htmlFor="email">Email</Label>
        <Field
          id="email" // must be snakecase to post to backend
          placeholder="User@CuriBio.com"
          type="text"
          onChange={(e) => {
            setUserData({
              ...userData,
              email: e.target.value,
            });
          }}
        />
        <Label htmlFor="username">Username</Label>
        <Field
          id="username"
          type="text"
          placeholder="User"
          onChange={(e) =>
            setUserData({ ...userData, username: e.target.value })
          }
        />

        <Label htmlFor="password">Password</Label>
        <Field
          id="passwordOne"
          type="password"
          placeholder="Password"
          onChange={(e) =>
            setUserData({ ...userData, password1: e.target.value })
          }
        />
        <Label htmlFor="password">Confirm Password</Label>
        <Field
          id="passwordTwo"
          type="password"
          placeholder="Password"
          onChange={(e) =>
            setUserData({ ...userData, password2: e.target.value })
          }
        />
        <ErrorText id="userError" role="errorMsg">
          {errorMsg}
        </ErrorText>
      </InputContainer>
      <ButtonContainer>
        {["Reset", "Add User"].map((label, idx) => (
          <ButtonWidget
            label={label}
            key={label}
            clickFn={() => (idx === 0 ? resetForm() : submitForm())}
          />
        ))}
      </ButtonContainer>
    </ModalContainer>
  );
}
