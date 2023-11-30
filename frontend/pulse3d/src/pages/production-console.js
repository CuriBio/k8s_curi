import SerialNumberTable from "@/components/table/SerialNumberTable";
import Table from "@/components/table/Table";
import DashboardLayout from "@/components/layouts/DashboardLayout";
import ModalWidget from "@/components/basicWidgets/ModalWidget";
import DropDownWidget from "@/components/basicWidgets/DropDownWidget";
import styled from "styled-components";
import { AuthContext } from "@/pages/_app";
import { useState, useContext, useEffect, useMemo } from "react";

const Container = styled.div`
  margin: 0 3.5rem;
  padding: 3.5rem 3.5rem;
  width: 1240px;
`;

const PreviewText = styled.div`
  font-style: italic;

  &:hover {
    color: var(--teal-green);
    text-decoration: underline;
    cursor: pointer;
  }
`;

const TableContainer = styled.div`
  padding-bottom: 30px;
`;

const TableHeader = styled.div`
  padding-bottom: 10px;
  padding-left: 10px;
`;

const serNumScopes = ["mantarray:serial_number:edit"];
const fwScopes = ["mantarray:firmware:edit", "mantarray:firmware:info"];

function FirmwareSection({ accountScope }) {
  const canViewFwTables = accountScope.includes("mantarray:firmware:info");
  const canEditFw = accountScope.includes("mantarray:firmware:edit");

  return (
    <>
      {canEditFw && <FirmwareUpload />}
      {canViewFwTables && <FirmwareTables accountScope={accountScope} canEdit={canEditFw} />}
    </>
  );
}

function FirmwareUpload() {
  return <TableHeader>TODO FirmwareUpload</TableHeader>;
}

function FirmwareTables({ canEdit }) {
  const [fwInfo, setFwInfo] = useState({ main: [], channel: [] });

  const getFwInfo = async () => {
    const getFwInfoRes = await fetch(`${process.env.NEXT_PUBLIC_MANTARRAY_URL}/firmware/info`);
    const getFwInfoResJson = await getFwInfoRes.json();
    setFwInfo({ main: getFwInfoResJson.main_fw_info, channel: getFwInfoResJson.channel_fw_info });
  };

  // when component first loads, get FW info
  useEffect(() => {
    getFwInfo();
  }, []);

  return (
    <>
      <MainFwTable mainFwInfo={fwInfo.main} />
      <ChannelFwTable fwInfo={fwInfo} canEdit={canEdit} refreshTables={getFwInfo} />
    </>
  );
}

function MainFwTable({ mainFwInfo }) {
  const cols = useMemo(
    () => [
      {
        accessorFn: (row) => row.version,
        id: "version",
        header: "Version",
        size: 250,
      },
      {
        accessorFn: (row) => row.min_ma_controller_version,
        id: "maControllerVersion",
        header: "Mantarray Controller",
        size: 250,
      },
      {
        accessorFn: (row) => row.min_sting_controller_version,
        id: "stingControllerVersion",
        header: "Stingray Controller",
        size: 250,
      },
      {
        accessorFn: (row) => row.state,
        id: "state",
        header: "State",
        size: 250,
      },
      {
        accessorKey: "edit",
        id: "edit",
        enableColumnFilter: false,
        enableColumnResizing: false,
        enableSorting: false,
        header: "",
        size: 128,
        // Tanner (11/29/23): there is currently no edits that need to be made to main FW by users of this page
      },
    ],
    []
  );

  return (
    <TableContainer>
      <TableHeader>Main Firmware</TableHeader>
      <Table
        columns={cols}
        rowData={mainFwInfo}
        defaultSortColumn={"version"}
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
  );
}

function ChannelFwTable({ fwInfo, refreshTables, canEdit }) {
  const [channelFwEdit, setChannelFwEdit] = useState({});

  const cols = useMemo(
    () => [
      {
        accessorFn: (row) => row.version,
        id: "version",
        header: "Version",
        size: 250,
      },
      {
        accessorFn: (row) => row.main_fw_version,
        id: "mainFwVersion",
        header: "Main FW",
        size: 250,
      },
      {
        accessorFn: (row) => row.hw_version,
        id: "hwVersion",
        header: "HW",
        size: 250,
      },
      {
        accessorFn: (row) => row.state,
        id: "state",
        header: "State",
        size: 250,
      },
      {
        accessorKey: "edit",
        id: "edit",
        enableColumnFilter: false,
        enableColumnResizing: false,
        enableSorting: false,
        header: "",
        size: 128,
        Cell: ({ cell }) => {
          return (
            canEdit && <PreviewText onClick={() => setChannelFwEdit(cell.row.original)}>Edit</PreviewText>
          );
        },
      },
    ],
    []
  );

  return (
    <>
      <TableContainer>
        <TableHeader>Channel Firmware</TableHeader>
        <Table
          columns={cols}
          rowData={fwInfo.channel}
          defaultSortColumn={"version"}
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
      <ChannelFwEditModal
        channelFwEdit={channelFwEdit}
        setChannelFwEdit={setChannelFwEdit}
        mainFwInfo={fwInfo.main}
        refreshTables={refreshTables}
      ></ChannelFwEditModal>
    </>
  );
}

function ChannelFwEditModal({ channelFwEdit, setChannelFwEdit, mainFwInfo, refreshTables }) {
  const [buttons, setButtons] = useState([]);
  const [labels, setLabels] = useState([]);
  const [rowInfo, setRowInfo] = useState({});

  useEffect(() => {
    setButtons(["Close", "Save"]);
    setLabels(["Main FW Version"]);
    setRowInfo({ mainFwVersion: channelFwEdit.main_fw_version });
  }, [channelFwEdit]);

  const mainFwVersions = mainFwInfo.map((row) => row.version);

  const handleUpdate = async (idx) => {
    if (idx === 1) {
      try {
        const res = await fetch(
          `${process.env.NEXT_PUBLIC_MANTARRAY_URL}/firmware/channel/${channelFwEdit.version}`,
          {
            method: "PUT",
            body: JSON.stringify({ main_fw_version: rowInfo.mainFwVersion }),
          }
        );
        if (res.status === 200) {
          setChannelFwEdit({});
          refreshTables();
        } else {
          throw Error;
        }
      } catch (e) {
        setButtons(["Close"]);
        setLabels(["An error occurred while updating user.", "Please try again later."]);
      }
    } else {
      setChannelFwEdit({});
    }
  };

  return (
    <>
      <ModalWidget
        open={Boolean(channelFwEdit.version)}
        header={`Edit Channel FW v${channelFwEdit.version}`}
        labels={labels}
        buttons={buttons}
        closeModal={handleUpdate}
      >
        <DropDownWidget
          options={mainFwVersions}
          initialSelected={mainFwVersions.indexOf(channelFwEdit.main_fw_version)}
          handleSelection={(idx) => {
            setRowInfo({
              ...rowInfo,
              mainFwVersion: mainFwVersions[idx],
            });
          }}
        />
      </ModalWidget>
    </>
  );
}

function SerialNumberSection() {
  return (
    <TableContainer>
      <TableHeader>Serial Numbers</TableHeader>
      <SerialNumberTable />
    </TableContainer>
  );
}

export default function ProductionConsole() {
  const { accountScope } = useContext(AuthContext);

  let canViewSerNumSection = false;
  let canViewFwSection = false;
  if (accountScope) {
    canViewSerNumSection = accountScope.some((scope) => serNumScopes.includes(scope));
    canViewFwSection = accountScope.some((scope) => fwScopes.includes(scope));
  }

  return (
    <Container>
      {canViewFwSection && <FirmwareSection accountScope={accountScope} />}
      {canViewSerNumSection && <SerialNumberSection />}
    </Container>
  );
}

ProductionConsole.getLayout = (page) => {
  return <DashboardLayout>{page}</DashboardLayout>;
};
