import ButtonWidget from "@/components/basicWidgets/ButtonWidget";
import DropDownWidget from "@/components/basicWidgets/DropDownWidget";
import FormInput from "@/components/basicWidgets/FormInput";
import ModalWidget from "@/components/basicWidgets/ModalWidget";
import Editor from "@/components/editor/Editor";
import DashboardLayout from "@/components/layouts/DashboardLayout";
import Table from "@/components/table/Table";
import { formatDateTime } from "@/utils/generic";
import { getShortUUIDWithTooltip } from "@/utils/jsx";
import { useEffect, useMemo, useRef, useState } from "react";
import styled from "styled-components";
import "quill/dist/quill.snow.css";
import dynamic from "next/dynamic";

const DOMPurify = dynamic(import("dompurify"), {
  ssr: false,
  loading: () => {},
});

const Container = styled.div`
  justify-content: center;
  position: relative;
  padding: 3rem;
`;

const TableContainer = styled.div`
  margin: 3% 0% 3% 0%;
  box-shadow: 0px 5px 5px -3px rgb(0 0 0 / 30%), 0px 8px 10px 1px rgb(0 0 0 / 20%),
    0px 3px 14px 2px rgb(0 0 0 / 12%);
`;

const ButtonContainer = styled.div`
  display: flex;
  flex-direction: row;
`;

const DropDownContainer = styled.div`
  width: 80%;
`;

const ModalContainer = styled.div`
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

const StaticInfo = styled.div`
  display: flex;
  padding: 5px;
  width: 80%;
`;

const StaticLabel = styled.div`
  width: 160px;
`;

const NotificationType = {
  customers_and_users: "Customers and Users",
  customers: "Customers",
  users: "Users",
};

export default function NotificationsManagement() {
  const [showCreateNotificationModal, setShowCreateNotificationModal] = useState(false);
  const [showNotificationDetailsModal, setShowNotificationDetailsModal] = useState(false);
  const [notificationDetails, setNotificationDetails] = useState({});
  const [showErrorModal, setShowErrorModal] = useState(false);
  const [subject, setSubject] = useState("");
  const [notificationType, setNotificationType] = useState(0);
  const [notificationsData, setNotificationsData] = useState([]);
  const quillRef = useRef(); // Use a ref to access the quill instance directly

  const sanitize = (input) => {
    try {
      return DOMPurify.sanitize(input);
    } catch {
      return <p>Loading...</p>;
    }
  };

  // gets notifications at load
  useEffect(() => {
    getAllNotifications();
  }, []);

  const getAllNotifications = async () => {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_PULSE3D_URL}/notifications`);

      if (response && response.status === 200) {
        const notificationsJson = await response.json();
        const notifications = notificationsJson.map(
          ({ id, created_at, subject, body, notification_type }) => ({
            id,
            createdAt: created_at,
            subject,
            body,
            notificationType: notification_type,
          })
        );

        setNotificationsData([...notifications]);
      }
    } catch (e) {
      console.log("ERROR fetching all notifications info", e);
    }
  };

  const columns = useMemo(
    () => [
      {
        accessorKey: "id",
        header: "Notification ID",
        size: 200,
        minSize: 200,
        Cell: ({ cell }) => getShortUUIDWithTooltip(cell.getValue(), 8),
      },
      {
        accessorKey: "subject",
        header: "Subject",
        size: 580,
        minSize: 400,
      },
      {
        accessorFn: (row) => new Date(row.createdAt),
        id: "createdAt",
        header: "Date Created",
        size: 200,
        minSize: 200,
        Cell: ({ cell }) => formatDateTime(cell.getValue()),
      },
      {
        accessorKey: "notificationType",
        header: "Notification Type",
        size: 200,
        minSize: 200,
        Cell: ({ cell }) => NotificationType[cell.getValue()],
      },
    ],
    []
  );

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
        await getAllNotifications();
        return;
      }

      console.log("ERROR - POST /notifications: unexpected response");
    } catch (e) {
      console.log("ERROR - POST /notifications:", e);
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

  const handleTableRowClick = (row) => {
    setNotificationDetails(row.original);
    setShowNotificationDetailsModal(true);
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
        <ModalContainer>
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
        </ModalContainer>
      </ModalWidget>
      <ModalWidget
        open={showErrorModal}
        closeModal={() => setShowErrorModal(false)}
        width={500}
        header={"Error Occurred!"}
        labels={["Something went wrong while performing this action.", "Please try again later."]}
        buttons={["Close"]}
      />
      <TableContainer>
        <Table
          columns={columns}
          rowData={notificationsData}
          defaultSortColumn={"createdAt"}
          rowClickFn={handleTableRowClick}
          rowSelection={false}
          setRowSelection={null}
          enableRowSelection={false}
          enablePagination={false}
          enableTopToolbar={false}
          enableSelectAll={false}
          enableStickyHeader={false}
          showColumnFilters={false}
        />
      </TableContainer>
      <ModalWidget
        width={1000}
        open={showNotificationDetailsModal}
        closeModal={() => setShowNotificationDetailsModal(false)}
        header={"Notification Details"}
        labels={[]}
        buttons={["Close"]}
      >
        <ModalContainer>
          <StaticInfo>
            <StaticLabel>Notification ID</StaticLabel>
            {notificationDetails.id}
          </StaticInfo>
          <StaticInfo>
            <StaticLabel>Date Created</StaticLabel>
            {formatDateTime(notificationDetails.createdAt)}
          </StaticInfo>
          <StaticInfo>
            <StaticLabel>Notification Type</StaticLabel>
            {NotificationType[notificationDetails.notificationType]}
          </StaticInfo>
          <StaticInfo>
            <StaticLabel>Subject</StaticLabel>
            {notificationDetails.subject}
          </StaticInfo>
          <StaticInfo>
            <StaticLabel>Body</StaticLabel>
          </StaticInfo>
          <StaticInfo>
            <div className="ql-editor">
              <div dangerouslySetInnerHTML={{ __html: sanitize(notificationDetails.body) }} />
            </div>
          </StaticInfo>
        </ModalContainer>
      </ModalWidget>
    </Container>
  );
}

NotificationsManagement.getLayout = (page) => {
  return <DashboardLayout>{page}</DashboardLayout>;
};
