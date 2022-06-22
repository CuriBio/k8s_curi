import styled from "styled-components";
import { useState } from "react";
import { useRouter } from "next/router";
import AnalysisParamForm from "./AnalysisParamForm";
import ButtonWidget from "@/components/basicWidgets/ButtonWidget";
import FileDragDrop from "./FileDragDrop";
import SparkMD5 from "spark-md5";
import hexToBase64 from "../utils/generic";

const Container = styled.div`
  width: 100%;
  height: inherit;
  justify-content: center;
  position: relative;
  padding-top: 5%;
  padding-left: 5%;
`;

const Uploads = styled.div`
  width: 90%;
  height: 90%;
  border: solid;
  border-color: var(--dark-gray);
  border-width: 2px;
  border-radius: 15px;
  background-color: var(--light-gray);
`;

const dropZoneText = "Click here or drop .h5/.zip file to upload";

export default function UploadForm() {
  const router = useRouter();
  const [file, setFile] = useState({});

  const [analysisParams, setAnalysisParams] = useState({});
  const [paramErrors, setParamErrors] = useState({});

  const handleFileChange = (file) => {
    setFile(file);
  };

  const postNewJob = async (uploadId) => {
    const jobResponse = await fetch("http://localhost/jobs", {
      method: "POST",
      body: JSON.stringify({
        upload_id: uploadId,
        twitch_widths: analysisParams.twitchWidths,
        start_time: analysisParams.startTime,
        end_time: analysisParams.endTime,
      }),
    });
    if (jobResponse.status !== 200) {
      console.log("ERROR posting new job: ", await jobResponse.json());
    }
    console.log("Starting analysis...");
  };

  const updateAnalysisParams = (newParams) => {
    let updatedParams = { ...analysisParams, ...newParams };
    try {
      updatedParams.twitchWidths = JSON.parse(updatedParams.twitchWidths);
      // TODO also assert that it's a list and it contains numbers
    } catch {
      // TODO display error message
      console.log(`Invalid twitchWidths array: ${updatedParams.twitchWidths}`);
    }
    setAnalysisParams(updatedParams);
  };

  const handleUpload = async () => {
    if (!file.name) {
      console.log("No file selected");
      // TODO: tell the user no file is selected
      return;
    }
    // if (true /* TODO check paramErrors for any error messages */) {
    //   console.log("Fix invalid params before uploading");
    //   // TODO: tell user to fix issues
    //   return;
    // }

    console.log("uploading...");

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

      if (uploadResponse.status !== 200) {
        console.log(
          "ERROR uploading file metadata to DB:  ",
          await uploadResponse.json()
        );
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
        console.log(
          "ERROR uploading file to s3:  ",
          await uploadPostRes.json()
        );
      }

      // start job
      await postNewJob(uploadId);
    };

    fileReader.onerror = function () {
      console.log(
        "ERROR: FileReader onerror was triggered, maybe the browser aborted due to high memory usage."
      );
      return;
    };

    fileReader.readAsArrayBuffer(file);
  };

  const updateParams = (newParams) => {
    const updatedParams = { ...analysisParams, ...newParams };
    console.log("updateParams new params:", JSON.stringify(updatedParams));

    if (newParams.twitchWidths !== undefined) {
      validateTwitchWidths(updatedParams);
    }
    if (newParams.startTime !== undefined || newParams.endTime !== undefined) {
      // need to validate start and end time together
      validateWindowBounds(updatedParams);
    }

    setAnalysisParams(updatedParams);
    console.log(
      "updateParams formatted params:",
      JSON.stringify(updatedParams)
    );
  };

  const validateTwitchWidths = (updatedParams) => {
    const newValue = updatedParams.twitchWidths;
    console.log("validateTwitchWidths:", newValue);
    let formattedTwitchWidths;
    if (newValue === null || newValue === "") {
      formattedTwitchWidths = null;
    } else {
      let twitchWidthArr;
      // make sure it's a valid list
      try {
        twitchWidthArr = JSON.parse(`[${newValue}]`);
      } catch (e) {
        console.log(`Invalid twitchWidths: ${newValue}, ${e}`);
        setParamErrors({
          ...paramErrors,
          twitchWidths: "Must be comma-separated, positive numbers",
        });
        return;
      }
      // make sure it's an array of positive numbers
      if (isArrayOfNumbers(twitchWidthArr, true)) {
        formattedTwitchWidths = Array.from(new Set(twitchWidthArr));
        console.log("formattedTwitchWidths:", formattedTwitchWidths);
      } else {
        console.log(`Invalid twitchWidths: ${newValue}`);
        setParamErrors({
          ...paramErrors,
          twitchWidths: "Must be comma-separated, positive numbers",
        });
        return;
      }
    }
    console.log("VALID TW");
    setParamErrors({ ...paramErrors, twitchWidths: "" });
    updatedParams.twitchWidths = formattedTwitchWidths;
  };

  const validateWindowBounds = (updatedParams) => {
    const { startTime, endTime } = updatedParams;
    const updatedParamErrors = { ...paramErrors };

    for (const [boundName, boundValueStr] of Object.entries({
      startTime,
      endTime,
    })) {
      let error = "";
      if (boundValueStr) {
        const boundValue = +boundValueStr;
        updatedParams[boundName] = boundValue;
        if (boundValue < 0) {
          error = "Must be a non-negative number";
        }
      }

      updatedParamErrors[boundName] = error;
    }

    if (
      !updatedParamErrors.startTime &&
      !updatedParamErrors.endTime &&
      updatedParams.startTime &&
      updatedParams.endTime &&
      updatedParams.startTime >= updatedParams.endTime
    ) {
      updatedParamErrors.endTime = "Must be greater than Start Time";
    }
    setParamErrors(updatedParamErrors);
  };

  return (
    <Container>
      <Uploads>
        <FileDragDrop
          handleFileChange={handleFileChange}
          dropZoneText={dropZoneText}
          fileSelection={file.name}
        />
        <AnalysisParamForm
          errorMessages={paramErrors}
          updateParams={updateParams}
        />
        <ButtonWidget
          top={"20%"}
          left={"80%"}
          width={"115px"}
          height={"30px"}
          position={"relative"}
          borderRadius={"3px"}
          label="Submit"
          clickFn={handleUpload}
        />
      </Uploads>
    </Container>
  );
}
