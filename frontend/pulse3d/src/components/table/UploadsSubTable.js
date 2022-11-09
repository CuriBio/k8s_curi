import { memo } from "react";
import styled from "styled-components";
import Checkbox from "@mui/material/Checkbox";

const Container = styled.div`
  padding: 0 3.5rem;
`;

const SubContainer = styled.div`
  width: 100%;
  display: flex;
  align-items: center;
  background-color: #ececed8f;
`;
const SubHeader = styled.div`
  background-color: var(--dark-blue);
  color: white;
  padding: 0.4rem 0;
  font-size: 0.85rem;
  border-radius: 3px;
  display: flex;
`;

const FilenameHeader = styled.div`
  padding-left: 3.9%;
  width: 40%;
`;
const Header = styled.div`
  width: 20%;
`;

const SubRowFileName = styled.div`
  font-size: 0.75rem;
  width: 40%;
`;
const SubRow = styled.div`
  font-size: 0.75rem;
  width: 20%;
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
        <SubRowFileName>
          <Checkbox
            id={job.jobId}
            disabled={job.status === "pending"}
            checked={checkedJobs.includes(job.jobId)}
            onChange={handleCheckedJobs}
          />
          {job.analyzedFile ? job.analyzedFile : "None"}
        </SubRowFileName>
        <SubRow>{job.datetime}</SubRow>
        <SubRow>{paramsString.length === 0 ? "None" : paramsString}</SubRow>
        <SubRow>
          {job.status === "finished" ? "Completed" : job.status[0].toUpperCase() + job.status.slice(1)}
        </SubRow>
      </SubContainer>
    );
  });
  return (
    <Container>
      <SubHeader>
        <FilenameHeader>Analyzed Filename</FilenameHeader>
        <Header>Created Date</Header>
        <Header>Analysis Parameters</Header>
        <Header>Status</Header>
      </SubHeader>
      {rows}
    </Container>
  );
});
