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
  width: 20%;
  text-align: center;
`;

export default memo(function UploadsSubTable(props) {
  const [isChecked, setIsChecked] = useState(
    props.jobs.map((job) => job.checked)
  );
  const rows = props.jobs.map((job, idx) => {
    return (
      <SubContainer key={Math.random()}>
        <input
          type="checkbox"
          checked={isChecked[idx]}
          onChange={() => {
            if (!isChecked[idx]) {
              props.setJobToEdit({ id: job.jobId, action: "add" });

              setIsChecked(
                isChecked.map((checked, index) =>
                  idx === index ? !checked : checked
                )
              );
            } else {
              props.setJobToEdit({ id: job.jobId, action: "remove" });
              setIsChecked(
                isChecked.map((checked, index) =>
                  idx === index ? !checked : checked
                )
              );
            }
          }}
        />
        <SubRow>{job.jobId}</SubRow>
        <SubRow>{job.datetime}</SubRow>
        <SubRow>{job.analysisParams ? "true" : "false"}</SubRow>
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
