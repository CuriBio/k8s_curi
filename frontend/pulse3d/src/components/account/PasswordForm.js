import styled from "styled-components";
import FormInput from "../basicWidgets/FormInput";
import Tooltip from "@mui/material/Tooltip";
import InfoOutlinedIcon from "@mui/icons-material/InfoOutlined";
import { useEffect, useState } from "react";

const TooltipText = styled.span`
  font-size: 15px;
`;
const InputContainer = styled.div`
  min-height: 170px;
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  width: inherit;
  padding: 0 32px;
`;
const TooltipContainer = styled.div`
  position: relative;
  margin-left: 5px;
`;
const Label = styled.label`
  position: relative;
  width: 80%;
  height: 40px;
  padding: 5px;
  line-height: 2;
  display: flex;
`;

export default function PasswordForm({ onChangePassword, setErrorMsg, password1, password2, children }) {
  const [password2Border, setPassword2Border] = useState("none");
  const [password1Border, setPassword1Border] = useState("none");

  const checkPasswordsMatch = () => {
    // only update this state once initial password passes requirements to prevent multiple error messages
    // preference for password requirement error message over not matching
    if (password1Border.includes("green")) {
      if (password2.length > 0) {
        // if a user has started to enter values in the password confirmation input
        // if the two passwords match, change border to green
        if (password2 === password1) {
          setPassword2Border("3px solid green");
          setErrorMsg("");
          // else change to red if they aren't matching
        } else {
          setErrorMsg("* Passwords do not match");
          setPassword2Border("3px solid red");
        }
      } else {
        // else set the border to none if user isn't inputting anything
        setPassword2Border("none");
        setErrorMsg("");
      }
    }
  };

  const validatePassword = () => {
    // this removes all borders/error messages once a user has backspaced to an empty input field
    if (password1.length > 0) {
      // min 10 chars, one number, one uppercase, one lowercase, one special character
      const reqRegex =
        /^(?=.*[a-z])(?=.*[A-Z])(?=.*[0-9])(?=.*[!@#$%^&*()~`|<>,.+=_"':;?/\\\[\]\{\}-]).{10,}/;
      const isValid = reqRegex.test(password1);

      if (isValid) {
        setPassword1Border("3px solid green");
        setErrorMsg("");
      } else {
        setPassword1Border("3px solid red");
        setErrorMsg("* Password does not meet requirements");
      }
    } else {
      // else set the border to none if user isn't inputting anything
      setPassword1Border("none");
      setErrorMsg("");
    }
  };

  useEffect(() => {
    validatePassword();
    checkPasswordsMatch();
  }, [password1, password2]);

  return (
    <InputContainer>
      <Label htmlFor="newPassword">
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
        name="password1"
        placeholder=""
        value={password1}
        type="password"
        onChangeFn={onChangePassword}
        borderStyle={password1Border}
      />
      <FormInput
        name="password2"
        label="Confirm Password"
        placeholder=""
        value={password2}
        type="password"
        onChangeFn={onChangePassword}
        borderStyle={password2Border}
      />
      {children}
    </InputContainer>
  );
}
