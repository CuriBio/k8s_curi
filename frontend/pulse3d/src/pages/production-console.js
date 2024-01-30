import { useState, useContext, useEffect, useMemo } from "react";
import { AuthContext } from "@/pages/_app";
import FileDragDrop from "@/components/uploadForm/FileDragDrop";
import DropDownWidget from "@/components/basicWidgets/DropDownWidget";
import FormInput from "@/components/basicWidgets/FormInput";
import ButtonWidget from "@/components/basicWidgets/ButtonWidget";
import Table from "@/components/table/Table";
import DashboardLayout from "@/components/layouts/DashboardLayout";
import ModalWidget from "@/components/basicWidgets/ModalWidget";
import SerialNumberTable from "@/components/table/SerialNumberTable";
import styled from "styled-components";
import semverValid from "semver/functions/valid";
import { hexToBase64 } from "../utils/generic";
import SparkMD5 from "spark-md5";
import semverGt from "semver/functions/gt";

const semverSortFn = (a, b) => {
  return semverGt(a, b) ? 1 : -1;
};

const semverSortforTable = (key) => {
  const fn = (a, b) => {
    return semverSortFn(a.original[key], b.original[key]);
  };
  return fn;
};

const UploadContainer = styled.div`
  width: 80%;
  min-width: 1130px;
  border: solid;
  border-color: var(--dark-gray);
  border-width: 2px;
  border-radius: 15px;
  background-color: white;
  display: flex;
  overflow: hidden;
  flex-direction: column;
  align-items: center;
  margin-bottom: 30px;
`;

const FileUploaderContainer = styled.div`
  height: 250px;
  width: 121%;
  padding-left: 28%;
`;

const FileUploadOptionContainer = styled.div`
  width: 750px;
  display: flex;
  text-wrap: nowrap;
  margin-bottom: 50px;
  justify-content: center;
`;

const SuccessText = styled.span`
  color: green;
  font-style: italic;
  font-size: 15px;
  padding-right: 10px;
  line-height: 3;
`;

const FailureText = styled.span`
  color: red;
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
  width: 200px;
`;

const ButtonContainer = styled.div`
  display: flex;
  justify-content: flex-end;
  padding: 3rem 8rem;
  width: 100%;
`;

const Header = styled.h2`
  position: relative;
  text-align: center;
  background-color: var(--dark-blue);
  color: var(--light-gray);
  margin: auto;
  width: 100%;
  height: 75px;
  line-height: 3;
`;

const SectionContainer = styled.div`
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

const serNumScopes = ["mantarray:serial_number:edit", "mantarray:serial_number:list"];
const fwScopes = ["mantarray:firmware:edit", "mantarray:firmware:list"];

const fwTypes = ["Main", "Channel"];

function FirmwareSection({ accountScope }) {
  const canViewFwTables = accountScope.includes("mantarray:firmware:list");
  const canEditFw = accountScope.includes("mantarray:firmware:edit");

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
      {canEditFw && <FirmwareUpload fwInfo={fwInfo} refreshTables={getFwInfo} />}
      {canViewFwTables && <FirmwareTables fwInfo={fwInfo} canEdit={canEditFw} getFwInfo={getFwInfo} />}
    </>
  );
}

const UPLOAD_STATES = {
  IDLE: "IDLE",
  IN_PROGRESS: "IN_PROGRESS",
  SUCCESS: "SUCCESS",
  FAILED: "FAILED",
};

const dropZoneText = "CLICK HERE or DROP";

function FirmwareUpload({ fwInfo, refreshTables }) {
  const [file, setFile] = useState();
  const [resetDragDrop, setResetDragDrop] = useState(false);
  const [resetInputWidgets, setResetInputWidgets] = useState(false);
  const [uploadOptions, setUploadOptions] = useState({});
  const [uploadOptionErrors, setUploadOptionErrors] = useState({});
  const [isButtonDisabled, setIsButtonDisabled] = useState(true);
  const [uploadState, setUploadState] = useState(UPLOAD_STATES.IDLE);

  const mainFwVersions = fwInfo.main.map((row) => row.version).sort(semverSortFn);
  const inProgress = uploadState === UPLOAD_STATES.IN_PROGRESS;

  useEffect(() => {
    const canUpload =
      getFileName(file) &&
      fwTypes.includes(uploadOptions.fwType) &&
      uploadOptions.version &&
      noErrors() &&
      checkFwTypeSpecificOptions();

    setIsButtonDisabled(!canUpload || inProgress);
  }, [file, uploadOptions, uploadOptionErrors, inProgress]);

  useEffect(() => {
    if (resetInputWidgets) {
      setResetInputWidgets(false);
    }
  }, [resetInputWidgets]);

  const resetInputs = () => {
    setFile(null);
    setResetInputWidgets(true);
    setUploadOptions({});
    setUploadOptionErrors({});
  };

  const getFileName = (file) => {
    return file ? file.name : null;
  };

  const noErrors = () => {
    return Object.values(uploadOptionErrors).every((val) => val.length === 0);
  };

  const checkFwTypeSpecificOptions = () => {
    if (uploadOptions.fwType === "Main") {
      return uploadOptions.maSwCompatible != null && uploadOptions.stingSwCompatible != null;
    } else {
      return uploadOptions.hwVersion != null && uploadOptions.mainFwVersion != null;
    }
  };

  const updateUploadOptions = (key, val) => {
    if ([UPLOAD_STATES.SUCCESS, UPLOAD_STATES.FAILED].includes(uploadState)) {
      setUploadState(UPLOAD_STATES.IDLE);
    }

    let updatedOptions = { ...uploadOptions, [key]: val };
    let updatedOptionErrors = { ...uploadOptionErrors };

    if (["version", "mainFwVersion", "hwVersion"].includes(key)) {
      const errorMsg = semverValid(val) ? "" : "Must be a valid version";
      updatedOptionErrors[key] = errorMsg;
    } else if (key === "fwType") {
      // remove all other keys except version
      updatedOptions = {
        version: updatedOptions.version,
        [key]: val,
      };
    }

    const dupVersionErrMsg = "FW type + version already present";
    if (
      ["fwType", "version"].includes(key) &&
      updatedOptions.fwType &&
      updatedOptions.version &&
      ["", dupVersionErrMsg].includes(updatedOptionErrors.version)
    ) {
      const fwTypeKey = updatedOptions.fwType.toLowerCase();
      const versionsForFwTypes = fwInfo[fwTypeKey].map((row) => row.version);
      const errorMsg = versionsForFwTypes.includes(updatedOptions.version) ? dupVersionErrMsg : "";
      updatedOptionErrors.version = errorMsg;
    }

    setUploadOptions(updatedOptions);
    setUploadOptionErrors(updatedOptionErrors);
  };

  const handleSubmit = async () => {
    if (!(file instanceof File)) {
      return;
    }
    setUploadState(UPLOAD_STATES.IN_PROGRESS);

    const result = await uploadFwFile(file);

    setUploadState(result);
    if (result === UPLOAD_STATES.SUCCESS) {
      resetInputs();
      refreshTables();
    }
  };

  const uploadFwFile = async (file) => {
    let fileReader = new FileReader();
    const filename = file.name;

    try {
      let fileHash;
      try {
        // Tanner (8/11/21): Need to use a promise here since FileReader API does not support using async functions, only callbacks
        fileHash = await new Promise((resolve, reject) => {
          fileReader.onload = function (e) {
            if (file.size != e.target.result.byteLength) {
              console.log(
                "ERROR:</strong> Browser reported success but could not read the file until the end."
              );
              reject();
            }

            resolve(SparkMD5.ArrayBuffer.hash(e.target.result));
          };

          fileReader.onerror = function () {
            console.log(
              "ERROR: FileReader onerror was triggered, maybe the browser aborted due to high memory usage."
            );
            reject();
          };

          fileReader.readAsArrayBuffer(file);
        });
      } catch (e) {
        return UPLOAD_STATES.FAILED;
      }

      const body = { version: uploadOptions.version, md5s: hexToBase64(fileHash) };
      if (uploadOptions.fwType === "Main") {
        body.is_compatible_with_current_ma_sw = uploadOptions.maSwCompatible;
        body.is_compatible_with_current_sting_sw = uploadOptions.stingSwCompatible;
      } else {
        body.main_fw_version = uploadOptions.mainFwVersion;
        body.hw_version = uploadOptions.hwVersion;
      }

      const uploadResponse = await fetch(
        `${process.env.NEXT_PUBLIC_MANTARRAY_URL}/firmware/${uploadOptions.fwType.toLowerCase()}/${
          uploadOptions.version
        }`,
        {
          method: "POST",
          body: JSON.stringify(body),
        }
      );

      if (uploadResponse.status !== 200) {
        // break flow if initial request returns error status code
        console.log("ERROR getting presigned upload URL for FW file:  ", await uploadResponse.json());
        return UPLOAD_STATES.FAILED;
      }

      const data = await uploadResponse.json();

      const uploadDetails = data.params;
      const uploadId = data.id;
      const formData = new FormData();

      Object.entries(uploadDetails.fields).forEach(([k, v]) => {
        formData.append(k, v);
      });

      formData.append("file", file);

      const uploadPostRes = await fetch(uploadDetails.url, {
        method: "POST",
        body: formData,
      });

      if (uploadPostRes.status !== 204) {
        console.log("ERROR uploading file to s3:  ", await uploadPostRes.json());
        return UPLOAD_STATES.FAILED;
      }
    } catch (e) {
      // catch all if service worker isn't working
      console.log("ERROR posting to presigned url");
      return UPLOAD_STATES.FAILED;
    }

    return UPLOAD_STATES.SUCCESS;
  };

  return (
    <UploadContainer>
      <Header>Upload Firmware File</Header>
      <FileUploaderContainer>
        <FileDragDrop
          handleFileChange={setFile}
          dropZoneText={dropZoneText}
          fileSelection={getFileName(file) || "No file selected"}
          setResetDragDrop={setResetDragDrop}
          resetDragDrop={resetDragDrop}
          fileTypes={["bin"]}
          multiple={false}
        />
      </FileUploaderContainer>
      <FileUploadOptionContainer>
        <TableHeader style={{ width: "100px", marginRight: "50px", justifyContent: "center" }}>
          Firmware Version
        </TableHeader>
        <InputContainer>
          <FormInput
            name="uploadFwVersion"
            placeholder={"1.2.3"}
            value={uploadOptions.version}
            onChangeFn={(e) => updateUploadOptions("version", e.target.value)}
          >
            <ErrorText id="uploadFwVersionError" role="errorMsg">
              {uploadOptionErrors.version}
            </ErrorText>
          </FormInput>
        </InputContainer>
      </FileUploadOptionContainer>
      <FileUploadOptionContainer>
        <TableHeader style={{ width: "100px", marginRight: "50px", justifyContent: "center" }}>
          Firmware Type
        </TableHeader>
        <InputContainer>
          <DropDownWidget
            options={fwTypes}
            handleSelection={(idx) => updateUploadOptions("fwType", fwTypes[idx])}
            reset={resetInputWidgets}
          />
        </InputContainer>
      </FileUploadOptionContainer>
      {uploadOptions.fwType === "Main" && (
        <>
          <FileUploadOptionContainer>
            <TableHeader style={{ width: "400px", marginRight: "50px", justifyContent: "center" }}>
              Is Compatible with Current MA SW Version?
            </TableHeader>
            <InputContainer>
              <DropDownWidget
                options={["False", "True"]}
                handleSelection={(idx) => updateUploadOptions("maSwCompatible", Boolean(idx))}
                reset={uploadOptions.fwType === "Main" || resetInputWidgets}
              />
            </InputContainer>
          </FileUploadOptionContainer>
          <FileUploadOptionContainer>
            <TableHeader style={{ width: "400px", marginRight: "50px", justifyContent: "center" }}>
              Is Compatible with Current Stingray SW Version?
            </TableHeader>
            <InputContainer>
              <DropDownWidget
                options={["False", "True"]}
                handleSelection={(idx) => updateUploadOptions("stingSwCompatible", Boolean(idx))}
                reset={uploadOptions.fwType === "Main" || resetInputWidgets}
              />
            </InputContainer>
          </FileUploadOptionContainer>
        </>
      )}
      {uploadOptions.fwType === "Channel" && (
        <>
          <FileUploadOptionContainer>
            <TableHeader style={{ width: "100px", marginRight: "50px", justifyContent: "center" }}>
              Main FW Version
            </TableHeader>
            <InputContainer>
              <DropDownWidget
                options={mainFwVersions}
                handleSelection={(idx) => updateUploadOptions("mainFwVersion", mainFwVersions[idx])}
                reset={uploadOptions.fwType === "Channel" || resetInputWidgets}
              />
            </InputContainer>
          </FileUploadOptionContainer>
          <FileUploadOptionContainer>
            <TableHeader style={{ width: "100px", marginRight: "50px", justifyContent: "center" }}>
              HW Version
            </TableHeader>
            <InputContainer>
              <FormInput
                name="hwVersion"
                placeholder={"1.2.3"}
                value={uploadOptions.hwVersion}
                onChangeFn={(e) => updateUploadOptions("hwVersion", e.target.value)}
              >
                <ErrorText id="hwVersionError" role="errorMsg">
                  {uploadOptionErrors.hwVersion}
                </ErrorText>
              </FormInput>
            </InputContainer>
          </FileUploadOptionContainer>
        </>
      )}
      <ButtonContainer>
        {uploadState === UPLOAD_STATES.SUCCESS && <SuccessText>Upload Successful!</SuccessText>}
        {uploadState === UPLOAD_STATES.FAILED && <FailureText>Upload Failed</FailureText>}
        <ButtonWidget
          width="200px"
          height="50px"
          position="relative"
          borderRadius="3px"
          left="10px"
          backgroundColor={isButtonDisabled ? "var(--dark-gray)" : "var(--dark-blue)"}
          disabled={isButtonDisabled}
          inProgress={inProgress}
          label="Submit"
          clickFn={handleSubmit}
        />
      </ButtonContainer>
    </UploadContainer>
  );
}

function FirmwareTables({ canEdit, fwInfo, getFwInfo }) {
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
        sortingFn: semverSortforTable("version"),
        size: 250,
      },
      {
        accessorFn: (row) => row.min_ma_controller_version,
        id: "maControllerVersion",
        header: "Mantarray Controller",
        sortingFn: semverSortforTable("min_ma_controller_version"),
        size: 250,
      },
      {
        accessorFn: (row) => row.min_sting_controller_version,
        id: "stingControllerVersion",
        header: "Stingray Controller",
        sortingFn: semverSortforTable("min_sting_controller_version"),
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
        sortingFn: semverSortforTable("version"),
        size: 250,
      },
      {
        accessorFn: (row) => row.main_fw_version,
        id: "mainFwVersion",
        header: "Main FW",
        sortingFn: semverSortforTable("main_fw_version"),
        size: 250,
      },
      {
        accessorFn: (row) => row.hw_version,
        id: "hwVersion",
        header: "HW",
        sortingFn: semverSortforTable("hw_version"),
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

  const mainFwVersions = mainFwInfo.map((row) => row.version).sort(semverSortFn);

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
    <SectionContainer>
      {/* TODO break these out into their own files once we find a way to reuse styling */}
      {canViewFwSection && <FirmwareSection accountScope={accountScope} />}
      {/* TODO need to handle case where user only has mantarray:serial_number:list */}
      {canViewSerNumSection && <SerialNumberSection />}
    </SectionContainer>
  );
}

ProductionConsole.getLayout = (page) => {
  return <DashboardLayout>{page}</DashboardLayout>;
};
