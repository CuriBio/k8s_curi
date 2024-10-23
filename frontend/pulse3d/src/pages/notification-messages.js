import ModalWidget from "@/components/basicWidgets/ModalWidget";
import DashboardLayout from "@/components/layouts/DashboardLayout";
import Table from "@/components/table/Table";
import { NotificationMessagesContext } from "@/pages/_app";
import { formatDateTime } from "@/utils/generic";
import { useContext, useEffect, useMemo, useState } from "react";
import styled from "styled-components";
import dynamic from "next/dynamic";

// server-side rendering needs to be disabled for components that use client-side browser objects
// e.g. the TinyMCE editor uses the 'window' browser object
const BundledTinyMCEEditorNoSSR = dynamic(() => import("@/components/editor/BundledTinyMCEEditor"), {
  ssr: false,
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

const ModalContainer = styled.div`
  height: 500px;
  display: flex;
  flex-direction: column;
  align-items: center;
`;

const StaticInfo = styled.div`
  display: flex;
  justify-content: flex-end;
  padding: 5px;
  width: 80%;
`;

const UnreadMessageFormatting = styled.span`
  cursor: pointer;
  font-weight: bold;
  font-family: Helvetica;
`;

const ReadMessageFormatting = styled.span`
  cursor: pointer;
  font-family: Helvetica;
`;

export default function NotificationMessages() {
  const { notificationMessages, setNotificationMessages } = useContext(NotificationMessagesContext);

  const [showNotificationMessageDetailsModal, setShowNotificationMessageDetailsModal] = useState(false);
  const [notificationMessageDetails, setNotificationMessageDetails] = useState({});
  const [displayRows, setDisplayRows] = useState([]);

  useEffect(() => {
    if (notificationMessages != null) {
      setDisplayRows([...notificationMessages]);
    }
  }, [notificationMessages]);

  const columns = useMemo(
    () => [
      {
        accessorFn: (row) => new Date(row.createdAt),
        id: "createdAt",
        header: "Date Created",
        size: 200,
        minSize: 200,
        enableColumnActions: false,
        Cell: ({ cell, row }) =>
          row.original.viewed ? (
            <ReadMessageFormatting>{formatDateTime(cell.getValue())}</ReadMessageFormatting>
          ) : (
            <UnreadMessageFormatting>{formatDateTime(cell.getValue())}</UnreadMessageFormatting>
          ),
      },
      {
        accessorKey: "subject",
        header: "Subject",
        size: 1000,
        minSize: 500,
        enableSorting: false,
        enableColumnActions: false,
        Cell: ({ cell, row }) =>
          row.original.viewed ? (
            <ReadMessageFormatting>{cell.getValue()}</ReadMessageFormatting>
          ) : (
            <UnreadMessageFormatting>{cell.getValue()}</UnreadMessageFormatting>
          ),
      },
    ],
    []
  );

  const viewNotificationMessage = async (id) => {
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_PULSE3D_URL}/notification_messages`, {
        method: "POST",
        body: JSON.stringify({ id }),
      });

      if (res && res.status === 200) {
        setNotificationMessages(
          notificationMessages.map((notificationMessage) => {
            if (notificationMessage.id === id) {
              return { ...notificationMessage, viewed: true };
            } else {
              return notificationMessage;
            }
          })
        );
        return;
      }

      console.log("ERROR - POST /notification_messages: unexpected response");
    } catch (e) {
      console.log("ERROR - POST /notification_messages:", e);
    }
  };

  const handleTableRowClick = async (row) => {
    setNotificationMessageDetails(row.original);
    setShowNotificationMessageDetailsModal(true);

    if (!row.original.viewed) {
      await viewNotificationMessage(row.original.id);
    }
  };

  return (
    <Container>
      <TableContainer>
        <Table
          columns={columns}
          rowData={displayRows}
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
        open={showNotificationMessageDetailsModal}
        closeModal={() => setShowNotificationMessageDetailsModal(false)}
        header={notificationMessageDetails.subject}
        labels={[]}
        buttons={["Close"]}
      >
        <ModalContainer>
          <StaticInfo>{formatDateTime(notificationMessageDetails.createdAt)}</StaticInfo>
          <BundledTinyMCEEditorNoSSR
            disabled={true}
            height={"85%"}
            initialValue={notificationMessageDetails.body}
          />
        </ModalContainer>
      </ModalWidget>
    </Container>
  );
}

NotificationMessages.getLayout = (page) => {
  return <DashboardLayout>{page}</DashboardLayout>;
};
