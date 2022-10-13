import styled from "styled-components";
import { useEffect, useState } from "react";
import ButtonWidget from "@/components/basicWidgets/ButtonWidget";
import InfoOutlinedIcon from "@mui/icons-material/InfoOutlined";
import FormInput from "../basicWidgets/FormInput";
import ModalWidget from "../basicWidgets/ModalWidget";
import Tooltip from "@mui/material/Tooltip";

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

const TooltipText = styled.span`
  font-size: 15px;
`;

const ModalContainer = styled.div`
  height: 590px;
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

const Label = styled.label`
  position: relative;
  width: 80%;
  height: 40px;
  padding: 5px;
  line-height: 2;
  display: flex;
`;

const TooltipContainer = styled.div`
  position: relative;
  margin-left: 5px;
`;

export default function NewUserForm() {
  const [userData, setUserData] = useState({
    email: "",
    username: "",
    password1: "",
    password2: "",
  });

  const [errorMsg, setErrorMsg] = useState("");
  const [inProgress, setInProgress] = useState(false);
  const [userCreatedVisible, setUserCreatedVisible] = useState(false);
  const [password2Border, setPassword2Border] = useState("none");
  const [password1Border, setPassword1Border] = useState("none");
  const resetForm = () => {
    setErrorMsg(""); // reset to show user something happened
    setUserData({
      email: "",
      username: "",
      password1: "",
      password2: "",
    });
    setPassword2Border("none");
    setPassword1Border("none");
  };

  useEffect(() => resetForm(), []);

  const submitForm = async () => {
    setErrorMsg(""); // reset to show user something happened
    setInProgress(true);

    if (Object.values(userData).includes("")) setErrorMsg("* All fields are required");
    // this state gets passed to web worker to attempt login request
    else {
      const res = await fetch(`${process.env.NEXT_PUBLIC_USERS_URL}/register`, {
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
          const firstError = error.detail.find((d) => d.msg);
          const nameOfInvalidField = firstError.loc[1];
          const reason = firstError.msg;
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

  const checkPasswordsMatch = () => {
    if (userData.password2.length > 0) {
      // if a user has started to enter values in the password confirmation input
      // if the two passwords match, change border to green
      if (userData.password2 === userData.password1) {
        setPassword2Border("3px solid green");
        setErrorMsg("");
        // else change to red if they aren't matching
      } else {
        setErrorMsg("* Passwords do not match");
        setPassword2Border("3px solid red");
      }
    } else {
      setPassword2Border("none"); // else set the border to none if user isn't inputting anything
      setErrorMsg("");
    }
  };

  const validatePassword = () => {
    if (userData.password1.length > 0) {
      const reqRegex = new RegExp("^(?=.*[a-z])(?=.*[A-Z])(?=.*d)(?=.*[@$!%*?&])[A-Za-zd@$!%*?&]{10,}$");
      console.log(reqRegex);
      const isValid = reqRegex.test(userData.password1);
      console.log(isValid);
      if (isValid) setPassword1Border("3px solid green");
      else setPassword1Border("3px solid red");
    } else setPassword1Border("none");
  };

  useEffect(() => {
    validatePassword();
    checkPasswordsMatch();
  }, [userData.password1, userData.password2]);

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
        <Label htmlFor="passwordOne">
          Password{" "}
          <TooltipContainer>
            <Tooltip
              sx={{
                fontSize: "18px",
                marginTop: "7px",
                cursor: "pointer",
              }}
              title={
                <TooltipText>
                  <li>Must be at least 10 characters.</li>
                  <li>
                    Must contain at least one uppercase, one lowercase, one number, and one special character.
                  </li>
                </TooltipText>
              }
            >
              <InfoOutlinedIcon />
            </Tooltip>
          </TooltipContainer>
        </Label>
        <FormInput
          name="passwordOne"
          placeholder="Password"
          type="password"
          value={userData.password1}
          onChangeFn={(e) => {
            setUserData({
              ...userData,
              password1: e.target.value,
            });
          }}
          borderStyle={password1Border}
        />
        <FormInput
          name="passwordTwo"
          label="Confirm Password"
          placeholder="Password"
          type="password"
          value={userData.password2}
          onChangeFn={(e) => {
            setUserData({
              ...userData,
              password2: e.target.value,
            });
          }}
          borderStyle={password2Border}
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
