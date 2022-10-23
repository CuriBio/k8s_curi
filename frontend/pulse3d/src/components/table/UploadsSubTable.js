import { useState, memo } from "react";
import styled from "styled-components";
import Checkbox from "@mui/material/Checkbox";

const SubContainer = styled.div`
  display: flex;
  justify-content: space-around;
  margin: 0 1rem;
`;
const SubHeader = styled.div`
  display: flex;
  background-color: var(--dark-blue);
  color: white;
  margin: 0 1rem;
  padding: 0.4rem;
  justify-content: flex-start;
  font-size: 0.85rem;
  border-radius: 3px;
`;
const SubRow = styled.div`
  font-size: 0.75rem;
  margin: 1rem 0;
  width: 100%;
`;
const SubRowFileName = styled.div`
  font-size: 0.75rem;
  margin: 1rem 0;
  width: 200%;
`;
const SubRowCheckbox = styled.div`
  font-size: 0.75rem;
  width: 50%;
`;
export default memo(function UploadsSubTable({ handleCheckedJobs, checkedJobs, jobs }) {
  const rows = jobs.map((job) => {
    let paramsString = [];

    Object.keys(job.analysisParams).forEach((param) => {
      if (job.analysisParams[param] !== null) {
        const paramVal = param === "peaks_valleys" ? "user set" : job.analysisParams[param];
        paramsString.push(<div key={job.jobId + param}> {`${param.replace("_", " ")}: ${paramVal}`}</div>);
      }
    });

    return (
      <SubContainer key={Math.random()}>
        <SubRowCheckbox>
          <Checkbox id={job.jobId} checked={checkedJobs.includes(job.jobId)} onChange={handleCheckedJobs} />
        </SubRowCheckbox>
        <SubRowFileName>{job.analyzedFile ? job.analyzedFile : "None"}</SubRowFileName>
        <SubRow>{job.datetime}</SubRow>
        <SubRow>{paramsString.length === 0 ? "None" : paramsString}</SubRow>
        <SubRow>{job.status}</SubRow>
      </SubContainer>
    );
  });
  return (
    <div>
      <SubHeader>
        <div style={{ width: "8.9%" }}>Select</div>
        <div style={{ width: "36.6%" }}>Analyzed Filename</div>
        <div style={{ width: "18.2%" }}>Created Date</div>
        <div style={{ width: "18.2%" }}>Analysis Parameters</div>
        <div style={{ width: "0%" }}>Status</div>
      </SubHeader>
      {rows}
    </div>
  );
});
