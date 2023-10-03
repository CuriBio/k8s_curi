import styled from "styled-components";
import { useEffect, useState } from "react";
import ButtonWidget from "@/components/basicWidgets/ButtonWidget";
import FormInput from "../basicWidgets/FormInput";
import ModalWidget from "../basicWidgets/ModalWidget";
import ScopeWidget from "./ScopeWidget";

const InputContainer = styled.div`
  min-height: 260px;
  position: relative;
  display: flex;
  flex-direction: column;
  justify-content: space-evenly;
  align-items: center;
  padding: 4%;
  width: inherit;
`;
const ModalContainer = styled.div`
  width: 800px;
  background-color: white;
  position: relative;
  border-radius: 3%;
  overflow: hidden;
  margin-top: 100px;
  box-shadow: 0px 5px 5px -3px rgb(0 0 0 / 30%), 0px 8px 10px 1px rgb(0 0 0 / 20%),
    0px 3px 14px 2px rgb(0 0 0 / 12%);
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
  height: 72px;
  margin: auto;
  line-height: 3;
`;

const ButtonContainer = styled.div`
  display: flex;
  flex-direction: row;
`;

export default function NewUserForm() {
  const [userData, setUserData] = useState({
    email: "",
    username: "",
    scope: [],
  });

  const [errorMsg, setErrorMsg] = useState(" ");
  const [inProgress, setInProgress] = useState(false);
  const [userCreatedVisible, setUserCreatedVisible] = useState(false);

  const resetForm = () => {
    setErrorMsg(""); // reset to show user something happened
    setUserData({
      email: "",
      username: "",
      scope: [],
    });
  };

  useEffect(() => resetForm(), []);

  const submitForm = async () => {
    setErrorMsg(""); // reset to show user something happened
    setInProgress(true);
    if (Object.values(userData).includes("") || userData.scope.length === 0)
      setErrorMsg("* All fields are required");
    // this state gets passed to web worker to attempt login request
    else {
      const res = await fetch(`${process.env.NEXT_PUBLIC_USERS_URL}/register/user`, {
        method: "POST",
        body: JSON.stringify(userData),
      });

      if (res) {
        if (res.status === 201) {
          setUserCreatedVisible(true);
          resetForm();
        } else if (res.status === 422) {
          const error = await res.json();
          // some very unuseful errors get returned from the serve, so filter those out and use the first meaningful error message
          const usernameError = error.detail.find((d) => d.loc.includes("username"));
          const nameOfInvalidField = usernameError.loc[1];
          const reason = usernameError.msg;

          setErrorMessage(nameOfInvalidField, reason);
        } else if (res.status === 400) {
          const error = await res.json();
          setErrorMsg(`* ${error.detail}`);
        } else setErrorMsg(`* Internal server error. Try again later.`);
      } else setErrorMsg(`* Internal server error. Try again later.`);
    }

    setInProgress(false);
  };

  const setErrorMessage = (nameOfInvalidField, reason) => {
    const errorMsg = nameOfInvalidField === "email" ? "Please enter a valid email" : reason;
    if (errorMsg) setErrorMsg(`* ${errorMsg}`);
  };

  const handleSelectedScopes = (scope) => {
    setUserData({ ...userData, scope });
  };

  return (
    <ModalContainer>
      <ModalWidget
        open={userCreatedVisible}
        closeModal={() => setUserCreatedVisible(false)}
        header="Success"
        labels={[
          "User was created successfully!",
          "Please have them check their inbox for a verification email to begin accessing their account. Link will expire after 24 hours.",
        ]}
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
              email: e.target.value.toLowerCase(),
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
              username: e.target.value.toLowerCase(),
            });
          }}
        />
        <ScopeWidget selectedScopes={userData.scope} setSelectedScopes={handleSelectedScopes} />
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
