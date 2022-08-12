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
}) {
  const [open, setOpen] = useState(false);

  const handleCheckedUpload = (uploadId, jobs, checked) => {
    const affectedJobs = jobs.map((job) => job.jobId);

    if (checked) {
      setCheckedUploads([...checkedUploads, uploadId]);
      setCheckedJobs([...checkedJobs, ...affectedJobs]);
    } else {
      // get index and splice selected upload to unselect
      const uploadIdx = checkedJobs.indexOf(uploadId);
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

  const handleCheckedJobs = (id) => {
    setCheckedJobs([...checkedJobs, id]);
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
                            handleCheckbox={(_) => handleCheckedJobs(jobId)}
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
