import SerialNumberTable from "@/components/table/SerialNumberTable";
import Table from "@/components/table/Table";
import DashboardLayout from "@/components/layouts/DashboardLayout";
import styled from "styled-components";
import { AuthContext } from "@/pages/_app";
import { useState, useContext, useEffect, useMemo } from "react";

const Container = styled.div`
  padding: 3.5rem 3.5rem;
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
  const canUploadFw = accountScope.includes("mantarray:firmware:edit");

  return (
    <>
      {canUploadFw && <FirmwareUpload />}
      {canViewFwTables && <FirmwareTables />}
    </>
  );
}

function FirmwareUpload() {
  return <TableHeader>TODO</TableHeader>;
}

function FirmwareTables() {
  const [fwInfo, setFwInfo] = useState({ main: [], channel: [] });

  const getFwInfo = async () => {
    const getFwInfoRes = await fetch(`${process.env.NEXT_PUBLIC_MANTARRAY_URL}/firmware/info`);
    const getFwInfoResJson = await getFwInfoRes.json();
    console.log("getFwInfoResJson", getFwInfoResJson);
    setFwInfo({ main: getFwInfoResJson.main_fw_info, channel: getFwInfoResJson.channel_fw_info });
  };

  // when component first loads, get FW info
  useEffect(() => {
    getFwInfo();
  }, []);

  return (
    <>
      <MainFwTable mainFwInfo={fwInfo.main} />
      <ChannelFwTable channelFwInfo={fwInfo.channel} />
    </>
  );
}

function MainFwTable({ mainFwInfo }) {
  const [rowSelection, setRowSelection] = useState({});

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
        rowSelection={rowSelection}
        setRowSelection={setRowSelection}
        enablePagination={false}
        enableTopToolbar={false}
        enableSelectAll={false}
        enableStickyHeader={false}
        enableRowSelection={(row) => false}
        showColumnFilters={false}
      />
    </TableContainer>
  );
}

function ChannelFwTable({ channelFwInfo }) {
  const [rowSelection, setRowSelection] = useState({});

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
    ],
    []
  );

  return (
    <TableContainer>
      <TableHeader>Channel Firmware</TableHeader>
      <Table
        columns={cols}
        rowData={channelFwInfo}
        defaultSortColumn={"version"}
        rowSelection={rowSelection}
        setRowSelection={setRowSelection}
        enablePagination={false}
        enableTopToolbar={false}
        enableSelectAll={false}
        enableStickyHeader={false}
        // getRowId={(row) => row.jobId}
        showColumnFilters={false}
      />
    </TableContainer>
  );
}

function SerialNumberSecion() {
  return (
    <TableContainer>
      <TableHeader>Serial Numbers</TableHeader>
      <SerialNumberTable />
    </TableContainer>
  );
}

export default function ProductionConsole() {
  const { accountScope } = useContext(AuthContext);

  console.log(accountScope);

  let canViewSerNumSection = false;
  let canViewFwSection = false;
  if (accountScope) {
    canViewSerNumSection = accountScope.some((scope) => serNumScopes.includes(scope));
    canViewFwSection = accountScope.some((scope) => fwScopes.includes(scope));
  }

  return (
    <Container>
      {canViewFwSection && <FirmwareSection accountScope={accountScope} />}
      {canViewSerNumSection && <SerialNumberSecion />}
    </Container>
  );
}

ProductionConsole.getLayout = (page) => {
  return <DashboardLayout>{page}</DashboardLayout>;
};
