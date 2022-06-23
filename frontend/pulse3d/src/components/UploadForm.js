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
  const [analysisParams, setAnalysisParams] = useState({
    twitchWidths: null,
    startTime: null,
    endTime: null,
  });

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
    // TODO: if there are error messages, tell user to fix issues, then return
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

  return (
    <Container>
      <Uploads>
        <FileDragDrop
          handleFileChange={handleFileChange}
          dropZoneText={dropZoneText}
          fileSelection={file.name}
        />
        <AnalysisParamForm updateAnalysisParams={updateAnalysisParams} />
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
