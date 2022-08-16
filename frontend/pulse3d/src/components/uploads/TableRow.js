import KeyboardArrowDownIcon from "@mui/icons-material/KeyboardArrowDown";
import KeyboardArrowUpIcon from "@mui/icons-material/KeyboardArrowUp";
import CheckboxWidget from "@/components/basicWidgets/CheckboxWidget";
import Box from "@mui/material/Box";
import Collapse from "@mui/material/Collapse";
import IconButton from "@mui/material/IconButton";
import { useState } from "react";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";

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
      const noDuplicateJobs = affectedJobs.filter(
        (id) => !checkedJobs.includes(id)
      );
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

  return (
    <>
      <TableRow sx={{ "& > *": { borderBottom: "unset" } }}>
        <TableCell>
          <IconButton
            aria-label="expand row"
            size="small"
            onClick={() => setOpen(!open)}
          >
            {open ? <KeyboardArrowUpIcon /> : <KeyboardArrowDownIcon />}
          </IconButton>
        </TableCell>
        <TableCell component="th" scope="row">
          {row.name}
        </TableCell>
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
        <TableCell style={{ paddingBottom: 0, paddingTop: 0 }} colSpan={6}>
          <Collapse in={open} timeout="auto" unmountOnExit>
            <Box sx={{ margin: 1 }}>
              <Table size="small">
                <TableHead sx={{ backgroundColor: "var(--med-gray)" }}>
                  <TableRow>
                    <TableCell>ANALYZED FILENAME</TableCell>
                    <TableCell>CREATED&nbsp;AT</TableCell>
                    <TableCell align="center">
                      ANALYSIS&nbsp;PARAMETERS
                    </TableCell>
                    <TableCell align="center">STATUS</TableCell>
                    <TableCell />
                  </TableRow>
                </TableHead>
                <TableBody>
                  {row.jobs.map(
                    ({
                      jobId,
                      analyzedFile,
                      datetime,
                      status,
                      analysisParams,
                    }) => (
                      <TableRow key={datetime}>
                        <TableCell component="th" scope="row">
                          {analyzedFile}
                        </TableCell>
                        <TableCell>{datetime}</TableCell>
                        <TableCell align="center">
                          {Object.keys(analysisParams).map((param) => {
                            if (analysisParams[param]) {
                              const splitParam = param.split("_");
                              return (
                                <li key={analyzedFile + "__" + param}>
                                  {splitParam[0] + " " + splitParam[1]}:{" "}
                                  {JSON.stringify(analysisParams[param])}
                                </li>
                              );
                            }
                          })}
                        </TableCell>
                        <TableCell align="center">{status}</TableCell>
                        <TableCell align="center">
                          <CheckboxWidget
                            checkedState={checkedJobs.includes(jobId)}
                            disabled={status === "pending"} // disable if pending
                            handleCheckbox={(checked) =>
                              handleCheckedJobs(jobId, row.id, checked)
                            }
                          />
                        </TableCell>
                      </TableRow>
                    )
                  )}
                </TableBody>
              </Table>
            </Box>
          </Collapse>
        </TableCell>
      </TableRow>
    </>
  );
}
