import { useState } from "react";
import FormInput from "@/components/basicWidgets/FormInput";
import ButtonWidget from "@/components/basicWidgets/ButtonWidget";
import styled from "styled-components";

const Header = styled.h2`
  position: relative;
  text-align: center;
  background-color: var(--dark-blue);
  color: var(--light-gray);
  margin: 0px;
  width: 100%;
  height: 75px;
  line-height: 3;
`;

// TODO use whichever background color that the login form uses?
const Container = styled.div`
  width: 100%;
  min-width: 1200px;
  border: solid;
  border-color: var(--dark-gray);
  border-width: 2px;
  border-radius: 15px;
  background-color: white;
  overflow: hidden;
  display: flex;
  margin: 50px;
  flex-direction: column;
  align-items: center;
`;

const ButtonContainer = styled.div`
  display: flex;
  justify-content: flex-end;
  padding: 3rem 8rem;
  width: 100%;
`;

export default function AdminAccountOptions({ accountSettings, inProgress }) {
  const [accountSettingsEdits, setAccountSettingsEdits] = useState({});

  return (
    <Container>
      <Header>Account Settings</Header>
      <FormInput
        name="account_id_alias"
        label="Account ID Alias"
        placeholder={accountSettings.id_alias || "Orginization Name"}
        value={accountSettingsEdits.id_alias}
        onChangeFn={(e) => {
          setAccountSettingsEdits({
            ...accountSettingsEdits,
            id_alias: e.target.value,
          });
        }}
      />
      <ButtonContainer>
        <ButtonWidget
          width="200px"
          height="50px"
          position="relative"
          borderRadius="3px"
          left="10px"
          label={"Save"}
          clickFn={"TODO"}
          inProgress={inProgress}
          backgroundColor={inProgress ? "var(--teal-green)" : "var(--dark-blue)"}
        />
      </ButtonContainer>
    </Container>
  );
}
