import styled from "styled-components";
import { useEffect, useState, useContext } from "react";
import ButtonWidget from "@/components/basicWidgets/ButtonWidget";
import DropDownWidget from "@/components/basicWidgets/DropDownWidget";
import FormInput from "@/components/basicWidgets/FormInput";
import ModalWidget from "@/components/basicWidgets/ModalWidget";
import ScopeWidget from "./ScopeWidget";
import { AuthContext } from "@/pages/_app";

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

const DropDownContainer = styled.div`
  width: 80%;
  height: 35px;
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

const Label = styled.div`
  position: relative;
  width: 80%;
  height: 35px;
  min-height: 35px;
  padding: 5px;
  line-height: 2;
`

const ButtonContainer = styled.div`
  display: flex;
  flex-direction: row;
`;

const LoginType = {
  "password": "Username / Password",
  "sso_microsoft": "Microsoft SSO"
}

const getDefaultAccountInfo = (type) => {
  const info = {
    admin: {
      email: "",
      scopes: [],
      login_type: Object.keys(LoginType)[0]
    },
    user: {
      email: "",
      username: "",
      scopes: [],
    },
  };
  return info[type];
};

export default function NewAccountForm({ type }) {
  const isForUser = type === "user";

  const { loginType: customerLoginType, availableScopes } = useContext(AuthContext);

  const [newAccountInfo, setNewAccountInfo] = useState(getDefaultAccountInfo(type));
  const [accountTitle, setAccountTitle] = useState(type);
  const [errorMsg, setErrorMsg] = useState(" ");
  const [inProgress, setInProgress] = useState(false);
  const [userCreatedVisible, setUserCreatedVisible] = useState(false);
  const [userCreatedMsg, setUserCreatedMsg] = useState(" ");

  const getUserCreatedMsg = () => {
    if ((isForUser && customerLoginType === Object.keys(LoginType)[0]) ||
        (!isForUser && newAccountInfo.login_type === Object.keys(LoginType)[0])) {
      return "Please have them check their inbox for a verification email to begin accessing their account. Link will expire after 24 hours."
    }

    return "Please have them check their inbox for an email to begin accessing their account."
  }

  const resetForm = () => {
    setErrorMsg(""); // reset to show user something happened
    setNewAccountInfo(getDefaultAccountInfo(type));
  };

  useEffect(() => resetForm(), []);
  useEffect(() => {
    if (type) {
      setAccountTitle(type.charAt(0).toUpperCase() + type.slice(1));
      setNewAccountInfo(getDefaultAccountInfo(type));
    }
  }, [type]);

  const submitForm = async () => {
    setErrorMsg(""); // reset to show user something happened
    setInProgress(true);

    if (Object.values(newAccountInfo).includes("") || newAccountInfo.scopes.length === 0)
      setErrorMsg("* All fields are required");
    // this state gets passed to web worker to attempt login request
    else {
      const res = await fetch(`${process.env.NEXT_PUBLIC_USERS_URL}/register/${type}`, {
        method: "POST",
        body: JSON.stringify(newAccountInfo),
      });

      if (res) {
        if (res.status === 201) {
          setUserCreatedMsg(getUserCreatedMsg())
          setUserCreatedVisible(true);
          resetForm();
        } else if (res.status === 422) {
          const error = await res.json();
          console.log(error);
          // some very unuseful errors get returned from the serve, so filter those out and use the first meaningful error message
          const errorMsg = error.detail.find((d) => d.msg);
          const nameOfInvalidField = errorMsg.loc[1];
          const reason = errorMsg.msg;

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

  const handleSelectedScopes = (scopes) => {
    setNewAccountInfo({ ...newAccountInfo, scopes });
  };

  return (
    <ModalContainer>
      <ModalWidget
        open={userCreatedVisible}
        closeModal={() => setUserCreatedVisible(false)}
        header="Success"
        labels={[
          `${accountTitle} was created successfully!`,
          userCreatedMsg,
        ]}
      />
      <Header>{`New ${accountTitle} Details`}</Header>
      <InputContainer>
        <FormInput
          name="email"
          label="Email"
          placeholder="user@curibio.com"
          value={newAccountInfo.email}
          onChangeFn={(e) => {
            setErrorMsg("");
            setNewAccountInfo({
              ...newAccountInfo,
              email: e.target.value.toLowerCase(),
            });
          }}
        />
        {isForUser && (
          <FormInput
            name="username"
            label="Username"
            placeholder="User"
            value={newAccountInfo.username}
            onChangeFn={(e) => {
              setErrorMsg("");
              setNewAccountInfo({
                ...newAccountInfo,
                username: e.target.value.toLowerCase(),
              });
            }}
          />
        )}
        <ScopeWidget
          selectedScopes={newAccountInfo.scopes}
          setSelectedScopes={handleSelectedScopes}
          availableScopes={availableScopes[type]}
        />
        {!isForUser && (
          <>
            <Label>Login Type</Label>
            <DropDownContainer>
              <DropDownWidget
                label="Choose a Login Type"
                options={Object.values(LoginType)}
                initialSelected={0}
                height={35}
                handleSelection={(i) => {
                  setNewAccountInfo(prevState => {
                    return {...prevState, login_type: Object.keys(LoginType)[i]}
                  });
                }}
              />
            </DropDownContainer>
          </>
        )}
        <ErrorText id="userError" role="errorMsg">
          {errorMsg}
        </ErrorText>
      </InputContainer>
      <ButtonContainer>
        {[
          { label: "Reset", inProgress: false },
          { label: `Add`, inProgress },
        ].map(({ label, inProgress }, idx) => (
          <ButtonWidget
            label={label}
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
