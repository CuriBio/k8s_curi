import { useState, memo } from "react";
import styled from "styled-components";

const SubContainer = styled.div`
  display: flex;
  justify-content: space-around;
`;
const SubHeader = styled.div`
  display: flex;
  background-color: var(--dark-blue);
  color: white;
  margin: 0 1rem;
  padding: 0.4rem;
  justify-content: space-around;
`;
const SubRow = styled.div`
  font-size: 0.75rem;
  width: 20%;
  text-align: center;
  margin: 1rem 0;
`;

export default memo(function UploadsSubTable(props) {
  const [isChecked, setIsChecked] = useState(props.jobs.map((job) => job.checked));
  const rows = props.jobs.map((job, idx) => {
    let paramsString = [];
    Object.keys(job.analysisParams).forEach((param) => {
      if (job.analysisParams[param] !== null) {
        if (param === "peaks_valleys") {
          paramsString.push(<div key={Math.random()}>{`${param} : user set`}</div>);
          return;
        }
        paramsString.push(<div key={Math.random()}>{`${param} : ${job.analysisParams[param]}`}</div>);
      }
    });

    return (
      <SubContainer key={Math.random()}>
        <input
          type="checkbox"
          checked={isChecked[idx]}
          onChange={() => {
            if (!isChecked[idx]) {
              props.setJobToEdit({ id: job.jobId, action: "add" });

              setIsChecked(isChecked.map((checked, index) => (idx === index ? !checked : checked)));
            } else {
              props.setJobToEdit({ id: job.jobId, action: "remove" });
              setIsChecked(isChecked.map((checked, index) => (idx === index ? !checked : checked)));
            }
          }}
        />
        <SubRow>{job.jobId}</SubRow>
        <SubRow>{job.datetime}</SubRow>
        <SubRow>{paramsString.length === 0 ? "None" : paramsString}</SubRow>
        <SubRow>{job.status}</SubRow>
      </SubContainer>
    );
  });
  return (
    <div>
      <SubHeader>
        <div>Analyzed Filename</div>
        <div>Created Date</div>
        <div>Analysis Parameters</div>
        <div>Status</div>
      </SubHeader>
      {rows}
    </div>
  );
});
