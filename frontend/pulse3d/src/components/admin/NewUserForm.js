import styled from "styled-components";
import { useEffect, useState } from "react";
import ButtonWidget from "@/components/basicWidgets/ButtonWidget";
import { useRouter } from "next/router";
import FormInput from "../basicWidgets/FormInput";
import ModalWidget from "../basicWidgets/ModalWidget";

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

const ModalContainer = styled.div`
  height: 590px;
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
  background-color: var(--dark-gray);
  align-content: center;
  color: var(--dark-blue);
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
  const [inProgress, setInProgress] = useState(false);
  const [userCreatedVisible, setUserCreatedVisible] = useState(false);

  const resetForm = () => {
    setErrorMsg(""); // reset to show user something happened
    setUserData({
      email: "",
      username: "",
      password1: "",
      password2: "",
    });
  };

  useEffect(() => resetForm(), []);

  const submitForm = async () => {
    setErrorMsg(""); // reset to show user something happened
    setInProgress(true);

    if (Object.values(userData).includes(""))
      setErrorMsg("* All fields are required");
    // this state gets passed to web worker to attempt login request
    else {
      const res = await fetch("https://curibio.com/register", {
        method: "POST",
        body: JSON.stringify(userData),
      });

      if (res) {
        if (res.status === 201) {
          setUserCreatedVisible(true);
          resetForm();
        } else if (res.status === 422) {
          const error = await res.json();
          const message = error.detail[0].loc[1];
          setErrorMessage(message);
        } else if (res.status === 400) {
          const error = await res.json();
          setErrorMsg(`* ${error.detail}`);
        } else setErrorMsg(`* Internal server error. Try again later.`);
      } else setErrorMsg(`* Internal server error. Try again later.`);
    }

    setInProgress(false);
  };

  const setErrorMessage = (msg) => {
    let newMsg = null;
    switch (msg) {
      case "email":
        newMsg = "Please enter a valid email";
        break;
      case "username":
        newMsg =
          "Username must be at least 5 characters long, and only contain letters and numbers";
        break;
      case "password1":
        newMsg =
          "Please enter a valid password. Must contain at least one uppercase, one lowercase, one number, one special character, and be at least ten characters long.";
        break;
      case "password2":
        newMsg = "Passwords do not match";
        break;
    }

    if (newMsg) setErrorMsg(`* ${newMsg}`);
  };

  return (
    <ModalContainer>
      <ModalWidget
        open={userCreatedVisible}
        closeModal={() => setUserCreatedVisible(false)}
        header="Success"
        labels={["User was created successfully"]}
      />
      <Header>New User Details</Header>
      <InputContainer>
        <FormInput
          name="email"
          label="Email"
          placeholder="user@curibio.com"
          value={userData.email}
          onChangeFn={(e) => {
            setErrorMsg("");
            setUserData({
              ...userData,
              email: e.target.value,
            });
          }}
        />
        <FormInput
          name="username"
          label="Username"
          placeholder="User"
          value={userData.username}
          onChangeFn={(e) => {
            setErrorMsg("");
            setUserData({
              ...userData,
              username: e.target.value,
            });
          }}
        />
        <FormInput
          name="passwordOne"
          label="Password"
          placeholder="Password"
          type="password"
          value={userData.password1}
          onChangeFn={(e) => {
            setErrorMsg("");
            setUserData({
              ...userData,
              password1: e.target.value,
            });
          }}
        />
        <FormInput
          name="passwordTwo"
          label="Password"
          placeholder="Password"
          type="password"
          value={userData.password2}
          onChangeFn={(e) => {
            setErrorMsg("");
            setUserData({
              ...userData,
              password2: e.target.value,
            });
          }}
        />
        <ErrorText id="userError" role="errorMsg">
          {errorMsg}
        </ErrorText>
      </InputContainer>
      <ButtonContainer>
        {[
          { label: "Reset", inProgress: false },
          { label: "Add User", inProgress },
        ].map(({ label, inProgress }, idx) => (
          <ButtonWidget
            label={label}
            backgroundColor={"var(--dark-gray)"}
            color={"var(--dark-blue)"}
            key={label}
            height={"50px"}
            inProgress={inProgress}
            clickFn={() => (idx === 0 ? resetForm() : submitForm())}
          />
        ))}
      </ButtonContainer>
    </ModalContainer>
  );
}
