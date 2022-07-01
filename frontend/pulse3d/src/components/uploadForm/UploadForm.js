import styled from "styled-components";
import { useEffect, useState, useContext } from "react";
import AnalysisParamForm from "./AnalysisParamForm";
import ButtonWidget from "@/components/basicWidgets/ButtonWidget";
import DropDownWidget from "@/components/basicWidgets/DropDownWidget";
import FileDragDrop from "@/components/uploadForm/FileDragDrop";
import SparkMD5 from "spark-md5";
import { hexToBase64 } from "../../utils/generic";
import { useRouter } from "next/router";
import { UploadsContext } from "@/components/layouts/DashboardLayout";

const Container = styled.div`
  width: 70%;
  height: inherit;
  justify-content: center;
  position: relative;
  padding-top: 5%;
  padding-left: 11%;
`;

const Header = styled.h2`
  position: relative;
  text-align: center;
`;

const Uploads = styled.div`
  width: 100%;
  height: 70%;
  border: solid;
  border-color: var(--dark-gray);
  border-width: 2px;
  border-radius: 15px;
  background-color: white;
`;

const ButtonContainer = styled.div`
  position: relative;
  top: 15%;
  justify-content: flex-end;
  display: flex;
  padding-right: 12%;
  align-items: center;
`;
const ErrorText = styled.span`
  color: red;
  font-style: italic;
  font-size: 15px;
  padding-right: 10px;
`;

const SuccessText = styled.span`
  color: green;
  font-style: italic;
  font-size: 15px;
  padding-right: 10px;
`;

const DropDownContainer = styled.div`
  width: 70%;
  display: flex;
  justify-content: center;
  left: 15%;
  position: relative;
  height: 15%;
  align-items: center;
  top: 5%;
`;

const dropZoneText = "Click here or drop .h5/.zip file to upload";

export default function UploadForm() {
  const { query } = useRouter();
  const { uploads } = useContext(UploadsContext);

  const [file, setFile] = useState({});
  const [uniqueUploads, setUniqueUploads] = useState([]);
  const [isButtonDisabled, setIsButtonDisabled] = useState(true);
  const [paramErrors, setParamErrors] = useState({});
  const [inProgress, setInProgress] = useState(false);
  const [uploadError, setUploadError] = useState(false);
  const [uploadSuccess, setUploadSuccess] = useState(false);
  const [checked, setChecked] = useState(false);
  const [tabSelection, setTabSelection] = useState(query.id);
  const [analysisParams, setAnalysisParams] = useState({
    twitchWidths: "",
    startTime: "",
    endTime: "",
  });

  useEffect(() => {
    // checks if error value exists, no file is selected, or upload is in progress
    const checkConditions =
      !Object.values(paramErrors).every((val) => val.length === 0) ||
      !(file instanceof File || uploads.includes(file)) ||
      inProgress;

    setIsButtonDisabled(checkConditions);
  }, [paramErrors, file, inProgress]);

  useEffect(() => {
    // resets state when upload status changes
    if (uploadError || uploadSuccess) {
      resetState();
    }
  }, [uploadError, uploadSuccess]);

  useEffect(() => {
    // resets upload status when user makes changes
    if (
      file instanceof File ||
      Object.values(analysisParams).some((val) => val.length > 0)
    ) {
      setUploadError(false);
      setUploadSuccess(false);
    }
  }, [file, analysisParams]);

  useEffect(() => {
    setTabSelection(query.id);
    resetState();
  }, [query]);

  useEffect(() => {
    const uploadFilenames = uploads.map(
      ({ meta }) => JSON.parse(meta).filename
    );

    const formattedUploads = uploads.filter(({ meta }, idx) => {
      const { filename } = JSON.parse(meta);
      return uploadFilenames.indexOf(filename) === idx;
    });

    setUniqueUploads([...formattedUploads]);
  }, [uploads]);

  const resetState = () => {
    setFile(null);
    setAnalysisParams({
      twitchWidths: "",
      startTime: "",
      endTime: "",
    });

    setChecked(false);
    setParamErrors({});
  };

  const postNewJob = async (uploadId) => {
    const { twitchWidths, startTime, endTime } = analysisParams;
    const jobResponse = await fetch("http://localhost/jobs", {
      method: "POST",
      body: JSON.stringify({
        upload_id: uploadId,
        twitch_widths: twitchWidths === "" ? null : twitchWidths,
        start_time: startTime === "" ? null : startTime,
        end_time: endTime === "" ? null : endTime,
      }),
    });

    if (jobResponse.status !== 200) {
      console.log("ERROR posting new job: ", await jobResponse.json());
    }
  };

  const handleUpload = async () => {
    // update state to trigger in progress spinner over submit button
    setInProgress(true);

    if (file instanceof File) await uploadFile();
    else if (uploads.includes(file)) await requestReAnalysis();
    else console.log("No file selected");
  };

  const requestReAnalysis = async () => {
    const { filename } = JSON.parse(file.meta);

    const uploadResponse = await fetch("http://localhost/re_analysis", {
      method: "POST",
      body: JSON.stringify({
        filename: filename,
        upload_id: file.id,
      }),
    });

    // break flow if initial request returns error status code
    if (uploadResponse.status !== 200) {
      setUploadError(true);
      console.log("ERROR starting re analysis:  ", await uploadResponse.json());
      return;
    }

    setUploadSuccess(true);
    setInProgress(false);

    const { id } = await uploadResponse.json();
    await postNewJob(id);
  };

  const uploadFile = async () => {
    let fileReader = new FileReader();
    fileReader.onload = async function (e) {
      if (file.size != e.target.result.byteLength) {
        console.log(
          "ERROR:</strong> Browser reported success but could not read the file until the end."
        );
        return;
      }

      let hash = SparkMD5.ArrayBuffer.hash(e.target.result);
      const uploadResponse = await fetch("http://localhost/uploads", {
        method: "POST",
        body: JSON.stringify({
          filename: file.name,
          md5s: hexToBase64(hash),
        }),
      });

      // break flow if initial request returns error status code
      if (uploadResponse.status !== 200) {
        setUploadError(true);
        console.log(
          "ERROR uploading file metadata to DB:  ",
          await uploadResponse.json()
        );
        return;
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

      setInProgress(false);

      if (uploadPostRes.status === 204) {
        // start job
        setUploadSuccess(true);
        await postNewJob(uploadId);
      } else {
        setUploadError(true);
        console.log(
          "ERROR uploading file to s3:  ",
          await uploadPostRes.json()
        );
      }
    };

    fileReader.onerror = function () {
      console.log(
        "ERROR: FileReader onerror was triggered, maybe the browser aborted due to high memory usage."
      );
      return;
    };

    fileReader.readAsArrayBuffer(file);
  };

  const handleDropDownSelect = (idx) => {
    setFile(uploads[idx]);
    setUploadError(false);
    setUploadSuccess(false);
  };
  return (
    <Container>
      <Header>Run Analysis</Header>
      <Uploads>
        {tabSelection === "1" ? (
          <FileDragDrop // TODO figure out how to notify user if they attempt to upload existing recording
            handleFileChange={(file) => {
              setFile(file);
            }}
            dropZoneText={dropZoneText}
            fileSelection={file ? file.name : null}
          />
        ) : (
          <DropDownContainer>
            <DropDownWidget
              options={uniqueUploads.map(
                ({ meta }) => JSON.parse(meta).filename
              )}
              label="Select Recording"
              handleSelection={handleDropDownSelect}
            />
          </DropDownContainer>
        )}
        <AnalysisParamForm
          errorMessages={paramErrors}
          inputVals={analysisParams}
          checked={checked}
          setChecked={setChecked}
          paramErrors={paramErrors}
          setParamErrors={setParamErrors}
          setAnalysisParams={setAnalysisParams}
          analysisParams={analysisParams}
        />
        <ButtonContainer>
          {uploadError ? (
            <ErrorText>Error occurred! Try again.</ErrorText>
          ) : null}
          {uploadSuccess ? <SuccessText>Upload Successful!</SuccessText> : null}
          <ButtonWidget
            width={"135px"}
            height={"45px"}
            position={"relative"}
            borderRadius={"3px"}
            label="Reset"
            clickFn={resetState}
          />
          <ButtonWidget
            width={"135px"}
            height={"45px"}
            position={"relative"}
            borderRadius={"3px"}
            backgroundColor={
              isButtonDisabled ? "var(--dark-gray)" : "var(--dark-blue)"
            }
            disabled={isButtonDisabled}
            inProgress={inProgress}
            label="Submit"
            clickFn={handleUpload}
          />
        </ButtonContainer>
      </Uploads>
    </Container>
  );
}
