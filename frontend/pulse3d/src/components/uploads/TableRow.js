import KeyboardArrowDownIcon from "@mui/icons-material/KeyboardArrowDown";
import KeyboardArrowUpIcon from "@mui/icons-material/KeyboardArrowUp";
import CheckboxWidget from "@/components/basicWidgets/CheckboxWidget";
import Box from "@mui/material/Box";
import Collapse from "@mui/material/Collapse";
import IconButton from "@mui/material/IconButton";
import { useContext, useState } from "react";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import styled from "styled-components";
import { AuthContext } from "@/pages/_app";

const BoxCell = styled((props) => <TableCell {...props} colSpan={6} />)(() => ({
  paddingBottom: 0,
  paddingTop: 0,
  backgroundColor: "var(--med-gray)",
  borderBottom: "3px solid var(--dark-gray)",
}));

const SubHeader = styled((props) => <TableHead {...props} />)(() => ({
  backgroundColor: "var(--dark-blue)",
  borderBottom: "2px solid var(--dark-gray)",
}));

const JobCell = styled((props) => <TableCell {...props} />)(() => ({
  padding: "9px",
  backgroundColor: "white",
}));

export default function Row({
  row,
  setCheckedJobs,
  checkedJobs,
  setCheckedUploads,
  checkedUploads,
  setModalButtons,
  setModalState,
  setModalLabels,
}) {
  const { accountType } = useContext(AuthContext);

  const [open, setOpen] = useState(false);

  const handleCheckedUpload = (uploadId, jobs, checked) => {
    const affectedJobs = jobs.map((job) => job.jobId);
    const pendingJobs = jobs.some(({ status }) => status === "pending");
    if (pendingJobs) {
      setModalLabels({
        header: "Warning!",
        messages: [
          "This upload has one or more jobs that are still pending.",
          "Please wait until complete to proceed.",
        ],
      });
      setModalButtons(["Close"]);
      setModalState("generic");
    } else if (checked) {
      // don't include duplicate job ids from individual selections
      const noDuplicateJobs = affectedJobs.filter((id) => !checkedJobs.includes(id));
      setCheckedUploads([...checkedUploads, uploadId]);
      setCheckedJobs([...checkedJobs, ...noDuplicateJobs]);
    } else {
      // get index and splice selected upload to unselect
      const uploadIdx = checkedUploads.indexOf(uploadId);
      checkedUploads.splice(uploadIdx, 1);
      setCheckedUploads([...checkedUploads]);
      // get index and splice all related jobs to unselect
      affectedJobs.map((id) => {
        const jobIdx = checkedJobs.indexOf(id);
        checkedJobs.splice(jobIdx, 1);
        setCheckedJobs([...checkedJobs]);
      });
    }
  };

  const handleCheckedJobs = (id, uploadId, checked) => {
    // make sure the jobs don't already include current id from selecting an upload
    if (checked && !checkedJobs.includes(id)) {
      setCheckedJobs([...checkedJobs, id]);
    } else {
      const jobIdx = checkedJobs.indexOf(id);
      checkedJobs.splice(jobIdx, 1);
      setCheckedJobs([...checkedJobs]);

      // if user unselects a job id when an upload it selected, then it will unselect both
      // users cannot unselect jobs of selected uploads because deleting an upload will auto delete related jobs
      const uploadIdx = checkedUploads.indexOf(uploadId);
      if (uploadIdx !== -1) {
        checkedUploads.splice(uploadIdx, 1);
        setCheckedUploads([...checkedUploads]);
      }
    }
  };

  const formatAnalysisParamColumn = (param, analyzedFile, value) => {
    const splitParam = param.split("_");
    if ("peaks_valleys" !== param) {
      return (
        <li key={analyzedFile + "__" + param}>
          {splitParam[0] + " " + splitParam[1]}: {JSON.stringify(value)}
        </li>
      );
    } else {
      if (value && Object.keys(value).length === 24)
        return <li key={analyzedFile + "__" + param}>user-defined peaks/valleys: true</li>;
    }
  };

  return (
    <>
      <TableRow sx={{ "& > *": { borderBottom: "unset", height: "60px" } }}>
        <TableCell>
          <IconButton aria-label="expand row" size="small" onClick={() => setOpen(!open)}>
            {open ? <KeyboardArrowUpIcon /> : <KeyboardArrowDownIcon />}
          </IconButton>
        </TableCell>
        {accountType === "admin" && (
          <TableCell component="th" scope="row">
            {row.username}
          </TableCell>
        )}
        <TableCell>{row.name}</TableCell>
        <TableCell align="center">{row.id}</TableCell>
        <TableCell align="center">{row.createdAt}</TableCell>
        <TableCell align="center">{row.lastAnalyzed}</TableCell>
        <TableCell align="center">
          <CheckboxWidget
            checkedState={checkedUploads.includes(row.id)}
            handleCheckbox={(checked) => {
              handleCheckedUpload(row.id, row.jobs, checked);
            }}
          />
        </TableCell>
      </TableRow>
      <TableRow>
        <BoxCell>
          <Collapse in={open} timeout="auto" unmountOnExit>
            <Box sx={{ margin: 2, borderRadius: 1, overflow: "hidden" }}>
              <Table size="medium">
                <SubHeader>
                  <TableRow sx={{ height: "60px" }}>
                    <TableCell sx={{ color: "white" }}>ANALYZED FILENAME</TableCell>
                    <TableCell sx={{ color: "white" }}>CREATED&nbsp;AT</TableCell>
                    <TableCell sx={{ color: "white" }} align="center">
                      ANALYSIS&nbsp;PARAMETERS
                    </TableCell>
                    <TableCell sx={{ color: "white" }} align="center">
                      STATUS
                    </TableCell>
                    <TableCell />
                  </TableRow>
                </SubHeader>
                <TableBody>
                  {row.jobs.map(({ jobId, analyzedFile, datetime, status, analysisParams }) => {
                    return (
                      <TableRow key={datetime} sx={{ height: "60px" }}>
                        <JobCell>{analyzedFile}</JobCell>
                        <JobCell>{datetime}</JobCell>
                        <JobCell align="center">
                          {analysisParams
                            ? // Tanner (8/23/22): older analyses did not store the analysis params in the metadata of their DB entries,
                              // so guarding against that case
                              Object.keys(analysisParams).map((param) => {
                                if (analysisParams[param]) {
                                  return formatAnalysisParamColumn(
                                    param,
                                    analyzedFile,
                                    analysisParams[param]
                                  );
                                }
                              })
                            : "Not Found"}
                        </JobCell>
                        <JobCell align="center">{status}</JobCell>
                        <JobCell align="center">
                          <CheckboxWidget
                            checkedState={checkedJobs.includes(jobId)}
                            disabled={status === "pending"} // disable if pending
                            handleCheckbox={(checked) => handleCheckedJobs(jobId, row.id, checked)}
                          />
                        </JobCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </Box>
          </Collapse>
        </BoxCell>
      </TableRow>
    </>
  );
}
