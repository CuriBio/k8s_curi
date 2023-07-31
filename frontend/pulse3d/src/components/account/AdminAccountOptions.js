import { useState, useEffect } from "react";
import FormInput from "@/components/basicWidgets/FormInput";
import ButtonWidget from "@/components/basicWidgets/ButtonWidget";
import styled from "styled-components";

const ButtonContainer = styled.div`
  display: flex;
  justify-content: flex-end;
  padding-top: 50px;
  padding-right: 30px;
  width: 100%;
`;

const SaveButtonTextContainer = styled.span`
  font-style: italic;
  font-size: 15px;
  padding-right: 10px;
  line-height: 3;
`;

const ErrorText = styled.span`
  color: red;
  font-style: italic;
  text-align: left;
  position: relative;
  width: 150%;
  font-size: 13px;
`;

const InputContainer = styled.div`
  padding-right: 20%;
  display: flex;
  flex-direction: column;
`;

const UPDATE_STATUSES = {
  NO_EDITS: "no_edits",
  EDITING: "editing",
  PENDING: "pending",
  SUCCESS: "success",
  FAILURE: "failure",
};

export default function AdminAccountOptions({ accountId }) {
  const [accountSettings, setAccountSettings] = useState({});
  const [accountSettingsEdits, setAccountSettingsEdits] = useState({});
  const [errorMessages, setErrorMessages] = useState({});

  const [updateStatus, setUpdateStatus] = useState(UPDATE_STATUSES.NO_EDITS);

  const inProgress = updateStatus === UPDATE_STATUSES.PENDING;
  const isButtonDisabled =
    Object.values(errorMessages).some((val) => val.length > 0) ||
    inProgress ||
    // disable button if the current inputs are up to date
    [UPDATE_STATUSES.NO_EDITS, UPDATE_STATUSES.SUCCESS].includes(updateStatus);

  const getSaveButtonText = () => {
    if (updateStatus === UPDATE_STATUSES.SUCCESS) {
      return <SaveButtonTextContainer style={{ color: "green" }}>Update Successful!</SaveButtonTextContainer>;
    } else if (updateStatus === UPDATE_STATUSES.FAILURE) {
      return (
        <SaveButtonTextContainer style={{ color: "red" }}>Error, Update Failed.</SaveButtonTextContainer>
      );
    }
    return <></>;
  };

  // get account settings at load
  useEffect(() => {
    getAccountSettings();
  }, []);

  const getAccountSettings = async () => {
    const res = await fetch(`${process.env.NEXT_PUBLIC_USERS_URL}/${accountId}`);
    const data = await res.json();
    setAccountSettings(data);
    setAccountSettingsEdits(data);
  };

  const updateErrorMessages = (newErrorMessages) => {
    setErrorMessages({
      ...errorMessages,
      ...newErrorMessages,
    });
  };

  const updateAccountSettingsEdits = (newValues) => {
    setUpdateStatus(UPDATE_STATUSES.EDITING);

    const { alias: newAlias } = newValues;
    if (newAlias != null) {
      let errorMsg = "";
      if (newAlias.length > 0) {
        if (newAlias.length < 6 || 128 < newAlias.length) {
          errorMsg = "Must be 6-128 characters long";
        } else if (/^\s/.test(newAlias) || /\s$/.test(newAlias)) {
          errorMsg = "Cannot start or end with whitespace";
        } else if (/\s\s/.test(newAlias)) {
          errorMsg = "Cannot contain consecutive whitespace characters";
        }
      }
      updateErrorMessages({ alias: errorMsg });
      setAccountSettingsEdits({
        ...accountSettingsEdits,
        alias: newAlias,
      });
    }
  };

  const confirmChanges = async () => {
    if (isButtonDisabled) return;

    const requestBody = {
      action_type: "set_alias",
      new_alias: accountSettingsEdits.alias,
    };

    const newAccountSettings = {
      ...accountSettings,
      ...accountSettingsEdits,
    };

    setUpdateStatus(UPDATE_STATUSES.PENDING);

    const res = await fetch(`${process.env.NEXT_PUBLIC_USERS_URL}/${accountId}`, {
      method: "PUT",
      body: JSON.stringify(requestBody),
    });
    if (res.status === 200) {
      setAccountSettings(newAccountSettings);
      setUpdateStatus(UPDATE_STATUSES.SUCCESS);
    } else {
      setUpdateStatus(UPDATE_STATUSES.FAILURE);
    }
  };

  return (
    <>
      <InputContainer>
        <FormInput
          name="account_alias"
          label="Account Alias"
          placeholder={accountSettings.alias ? "Leave empty to remove the current alias" : "None set"}
          value={accountSettingsEdits.alias || ""}
          tooltipText={
            "Set an alias for the Customer ID field used when logging into a user account (6-128 characters)."
          }
          onChangeFn={(e) => {
            updateAccountSettingsEdits({ alias: e.target.value });
          }}
        />
        <ErrorText id={"Account Alias Error"} role="errorMsg">
          {errorMessages.alias}
        </ErrorText>
      </InputContainer>
      <ButtonContainer>
        {getSaveButtonText()}
        <ButtonWidget
          width="200px"
          height="50px"
          position="relative"
          borderRadius="3px"
          left="10px"
          label={"Save"}
          clickFn={confirmChanges}
          backgroundColor={isButtonDisabled ? "var(--dark-gray)" : "var(--dark-blue)"}
          disabled={isButtonDisabled}
          inProgress={inProgress}
        />
      </ButtonContainer>
    </>
  );
}
