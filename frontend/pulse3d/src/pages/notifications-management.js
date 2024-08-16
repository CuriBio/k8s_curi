import ButtonWidget from "@/components/basicWidgets/ButtonWidget";
import CheckboxWidget from "@/components/basicWidgets/CheckboxWidget";
import FormInput from "@/components/basicWidgets/FormInput";
import ModalWidget from "@/components/basicWidgets/ModalWidget";
import Editor from "@/components/editor/Editor";
import DashboardLayout from "@/components/layouts/DashboardLayout";
import { useRef, useState } from "react";
import styled from "styled-components";
import "quill/dist/quill.snow.css";

const Container = styled.div`
  justify-content: center;
  position: relative;
  padding: 3rem;
`;

const ButtonContainer = styled.div`
  display: flex;
  flex-direction: row;
`;

const LabeledCheckboxContainer = styled.div`
  display: flex;
  width: 80%;
  padding-left: 15px;
  flex-direction: row;
  align-items: left;
`;

const ModalInputContainer = styled.div`
  height: 500px;
  display: flex;
  flex-direction: column;
  align-items: center;
`;

const Label = styled.label`
  position: relative;
  width: 80%;
  height: 35px;
  min-height: 35px;
  padding: 5px;
  line-height: 2;
`;

const CheckBoxLabel = styled.div`
  padding: 9px 40px 0 0;
  font-size: 14px;
`;

export default function NotificationsManagement() {
  const [showCreateNotificationModal, setShowCreateNotificationModal] = useState(false);
  const [subject, setSubject] = useState("");
  const [customers, setCustomers] = useState(false);
  const [users, setUsers] = useState(false);
  const quillRef = useRef(); // Use a ref to access the quill instance directly

  const handleCreateNotificationButtonClick = () => {
    setShowCreateNotificationModal(true);
  };

  const handleCreateNotificationModalButtons = async (idx, buttonLabel) => {
    if (buttonLabel === "Save") {
      console.log("Subject: " + subject);
      console.log("Body: " + quillRef.current.getSemanticHTML());
      console.log("Customers: " + customers);
      console.log("Users: " + users);
    }

    setShowCreateNotificationModal(false);
    setSubject("");
    setCustomers(false);
    setUsers(false);
  };

  return (
    <Container>
      <ButtonContainer>
        <ButtonWidget
          width="220px"
          height="50px"
          borderRadius="3px"
          label="Create Notification"
          clickFn={handleCreateNotificationButtonClick}
        />
      </ButtonContainer>
      <ModalWidget
        width={1000}
        open={showCreateNotificationModal}
        closeModal={handleCreateNotificationModalButtons}
        header={"Create Notification"}
        labels={[]}
        buttons={["Cancel", "Save"]}
      >
        <ModalInputContainer>
          <FormInput
            name="subject"
            label="Subject"
            value={subject}
            onChangeFn={(e) => {
              setSubject(e.target.value);
            }}
          />
          <Label>Body</Label>
          <Editor ref={quillRef} />
          <Label style={{ padding: "50px 5px 30px" }}>Audience</Label>
          <LabeledCheckboxContainer>
            <CheckboxWidget size={"sm"} checkedState={customers} handleCheckbox={setCustomers} />
            <CheckBoxLabel>Customers</CheckBoxLabel>
            <CheckboxWidget size={"sm"} checkedState={users} handleCheckbox={setUsers} />
            <CheckBoxLabel>Users</CheckBoxLabel>
          </LabeledCheckboxContainer>
        </ModalInputContainer>
      </ModalWidget>
    </Container>
  );
}

NotificationsManagement.getLayout = (page) => {
  return <DashboardLayout>{page}</DashboardLayout>;
};
