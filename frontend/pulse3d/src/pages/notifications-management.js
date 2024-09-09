import ButtonWidget from "@/components/basicWidgets/ButtonWidget";
import DropDownWidget from "@/components/basicWidgets/DropDownWidget";
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

const DropDownContainer = styled.div`
  width: 80%;
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

const NotificationType = {
  customers_and_users: "Customers and Users",
  customers: "Customers",
  users: "Users",
};

export default function NotificationsManagement() {
  const [showCreateNotificationModal, setShowCreateNotificationModal] = useState(false);
  const [showErrorModal, setShowErrorModal] = useState(false);
  const [subject, setSubject] = useState("");
  const [notificationType, setNotificationType] = useState(0);
  const quillRef = useRef(); // Use a ref to access the quill instance directly

  const saveNotification = async () => {
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_PULSE3D_URL}/notifications`, {
        method: "POST",
        body: JSON.stringify({
          subject,
          body: quillRef.current.getSemanticHTML(),
          notification_type: Object.keys(NotificationType)[notificationType],
        }),
      });

      if (res && res.status === 201) {
        return;
      }

      console.log("ERROR - POST /notifications: unexpected response");
    } catch (e) {
      console.log(`ERROR - POST /notifications: ${e}`);
    }

    setShowErrorModal(true);
  };

  const handleCreateNotificationButtonClick = () => {
    setShowCreateNotificationModal(true);
  };

  const handleCreateNotificationModalButtons = async (idx, buttonLabel) => {
    if (buttonLabel === "Save") {
      await saveNotification();
    }

    setShowCreateNotificationModal(false);
    setSubject("");
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
              setSubject(e.target.value.substring(0, 128));
            }}
          />
          <Label>Body</Label>
          <Editor ref={quillRef} />
          <Label style={{ padding: "50px 5px 30px" }}>Type</Label>
          <DropDownContainer>
            <DropDownWidget
              options={Object.values(NotificationType)}
              initialSelected={0}
              height={35}
              handleSelection={setNotificationType}
            />
          </DropDownContainer>
        </ModalInputContainer>
      </ModalWidget>
      <ModalWidget
        open={showErrorModal}
        closeModal={() => setShowErrorModal(false)}
        width={500}
        header={"Error Occurred!"}
        labels={["Something went wrong while performing this action.", "Please try again later."]}
        buttons={["Close"]}
      />
    </Container>
  );
}

NotificationsManagement.getLayout = (page) => {
  return <DashboardLayout>{page}</DashboardLayout>;
};
