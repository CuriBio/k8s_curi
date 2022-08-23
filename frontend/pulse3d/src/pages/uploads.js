import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableContainer from "@mui/material/TableContainer";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import Paper from "@mui/material/Paper";
import CircularSpinner from "@/components/basicWidgets/CircularSpinner";
import DropDownWidget from "@/components/basicWidgets/DropDownWidget";
import ModalWidget from "@/components/basicWidgets/ModalWidget";
import DashboardLayout, {
  UploadsContext,
} from "@/components/layouts/DashboardLayout";
import styled from "styled-components";
import { useContext, useState, useEffect } from "react";
import Row from "@/components/uploads/TableRow";
import InteractiveAnalysisModal from "@/components/uploads/InteractiveAnalysisModal";

const Container = styled.div`
  display: flex;
  position: relative;
  justify-content: start;
  padding: 0% 3% 3% 3%;
  flex-direction: column;
`;
const SpinnerContainer = styled.div`
  display: flex;
  justify-content: center;
  align-items: center;
  width: 80%;
`;
const PageContainer = styled.div`
  width: 80%;
`;
const DropDownContainer = styled.div`
  width: 250px;
  background-color: white;
  border-radius: 5px;
  left: 70%;
  position: relative;
  margin: 3% 1% 1% 1%;
`;
const ModalSpinnerContainer = styled.div`
  position: relative;
  display: flex;
  justify-content: center;
  height: 315px;
  align-items: center;
`;

const modalObjs = {
  delete: {
    header: "Are you sure?",
    messages: [
      "Please confirm the deletion.",
      "Be aware that this action cannot be undone.",
    ],
  },
  downloadError: {
    header: "Error Occurred!",
    messages: [
      "An error occurred while attempting to download.",
      "Please try again.",
    ],
  },
  empty: {
    header: null,
    messages: [],
  },
  containsFailedJob: {
    header: "Warning!",
    messages: [
      "You are trying to download one or more analyses with an 'error' status. Please note that these will be ignored.",
      "Would you like to continue?",
    ],
  },
  failedDeletion: {
    header: "Error Occurred!",
    messages: [
      "There was an issue while deleting the files you selected.",
      "Please try again later.",
    ],
  },
  nothingToDownload: {
    header: "Oops..",
    messages: [
      "There is nothing to download.",
      "Please make sure you are attempting to download finished analyses.",
    ],
  },
};

export default function Uploads() {
  const { uploads, setFetchUploads } = useContext(UploadsContext);
  const [jobs, setJobs] = useState();
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(false);
  const [checkedJobs, setCheckedJobs] = useState([]);
  const [checkedUploads, setCheckedUploads] = useState([]);
  const [resetDropdown, setResetDropdown] = useState(false);
  const [modalState, setModalState] = useState(false);
  const [modalLabels, setModalLabels] = useState({ header: "", messages: [] });
  const [modalButtons, setModalButtons] = useState([]);
  const [openInteractiveAnalysis, setOpenInteractiveAnalysis] = useState(false);

  const getAllJobs = async () => {
    try {
      const response = await fetch("https://curibio.com/jobs?download=False");

      if (response && response.status === 200) {
        const { jobs } = await response.json();

        jobs = jobs.map(
          ({ id, upload_id, created_at, object_key, status, meta }) => {
            const analyzedFile = object_key
              ? object_key.split("/")[object_key.split("/").length - 1]
              : "";
            const formattedTime = formatDateTime(created_at);
            const analysisParams = JSON.parse(meta)["analysis_params"];
            return {
              jobId: id,
              uploadId: upload_id,
              analyzedFile,
              datetime: formattedTime,
              status,
              analysisParams,
            };
          }
        );

        setJobs(jobs);
      }
    } catch (e) {
      console.log("ERROR fetching jobs in /uploads");
    }
  };

  const formatDateTime = (datetime) => {
    return new Date(datetime + "Z").toLocaleDateString(undefined, {
      hour: "numeric",
      minute: "numeric",
    });
  };

  useEffect(() => {
    getAllJobs();
    // start 10 second interval
    const uploadsInterval = setInterval(() => getAllJobs(), [1e4]);
    //clear interval when switching pages
    return () => clearInterval(uploadsInterval);
  }, [uploads]);

  useEffect(() => {
    if (jobs) {
      const formattedUploads = uploads
        .map(({ id, filename, created_at }) => {
          const formattedTime = formatDateTime(created_at);
          const recName = filename ? filename.split(".")[0] : null;
          const uploadJobs = jobs
            .filter(({ uploadId }) => uploadId === id)
            .sort((a, b) => new Date(b.datetime) - new Date(a.datetime));

          const lastAnalyzed = uploadJobs[0]
            ? uploadJobs[0].datetime
            : formattedTime;

          return {
            name: recName,
            id,
            createdAt: formattedTime,
            lastAnalyzed,
            jobs: uploadJobs,
          };
        })
        .sort((a, b) => new Date(b.lastAnalyzed) - new Date(a.lastAnalyzed));

      setRows([...formattedUploads]);
      setLoading(false);
    }
  }, [jobs]);

  const handleDropdownSelection = (option) => {
    if (option === 1) {
      setModalButtons(["Close", "Confirm"]);
      setModalLabels(modalObjs.delete);
      setModalState("generic");
    } else if (option === 0) {
      // if download, check that no job contains an error status
      const failedJobs = jobs.filter(
        ({ jobId, status }) => checkedJobs.includes(jobId) && status === "error"
      );

      if (failedJobs.length === 0) {
        setModalLabels(modalObjs.empty);
        setModalState("downloading");
        downloadAnalyses();
      } else {
        setModalButtons(["Close", "Continue"]);
        setModalLabels(modalObjs.containsFailedJob);
        setModalState("generic");
      }
    } else if (option === 2) {
      setOpenInteractiveAnalysis(true);
    }

    setResetDropdown(false);
  };

  const handleDeletions = async () => {
    try {
      const failedDeletion = false;
      // soft delete all jobs
      if (checkedUploads.length > 0) {
        const uploadsURL = `https://curibio.com/uploads?`;
        checkedUploads.map((id) => (uploadsURL += `upload_ids=${id}&`));
        const uploadsResponse = await fetch(uploadsURL.slice(0, -1), {
          method: "DELETE",
        });
        if (uploadsResponse.status !== 200) failedDeletion = true;
      }
      // soft delete all jobs
      if (checkedJobs.length > 0) {
        const jobsuURL = `https://curibio.com/jobs?`;
        checkedJobs.map((id) => (jobsuURL += `job_ids=${id}&`));
        const jobsResponse = await fetch(jobsuURL.slice(0, -1), {
          method: "DELETE",
        });

        if (jobsResponse.status !== 200) failedDeletion = true;
      }

      if (failedDeletion) {
        setModalButtons(["Close"]);
        setModalLabels(modalObjs.failedDeletion);
        setModalState("generic");
      }
      // rerender table with updated deletions
      await setFetchUploads();
      return failedDeletion;
    } catch (e) {
      console.log("ERROR attempting to soft delete selected jobs and uploads");
    }
  };

  const handleModalClose = async (idx) => {
    if (modalButtons[idx] === "Continue") {
      // this block gets hit when user chooses to continue without 'error' status analyses
      setModalLabels(modalObjs.empty);
      setModalState("downloading");
      downloadAnalyses();
    } else if (modalButtons[idx] === "Confirm") {
      // set in progress
      setModalLabels(modalObjs.empty);
      setModalState("deleting");
      const failedDeletion = await handleDeletions();
      // wait a second to remove deleted files
      // really helps with flow of when in progress modal closes
      await new Promise((r) => setTimeout(r, 1000));

      // failed Deletions has it's own modal so prevent closure else reset
      if (!failedDeletion) {
        setModalState(false);
        setResetDropdown(true);
        setCheckedUploads([]);
        setCheckedJobs([]);
      }
    } else {
      // close in progress modal
      // also resets for any 'Close' modal button events
      // index 0 in buttons
      setModalState(false);
      setResetDropdown(true);
      setCheckedUploads([]);
      setCheckedJobs([]);
    }
  };

  const downloadAnalyses = async () => {
    try {
      // removes any jobs with error + pending statuses
      const finishedJobs = jobs.filter(
        ({ jobId, status }) =>
          checkedJobs.includes(jobId) && status === "finished"
      );
      const numberOfJobs = finishedJobs.length;

      if (numberOfJobs > 0) {
        //request only presigned urls for selected jobs
        const url = `https://curibio.com/jobs?`;
        finishedJobs.map(({ jobId }) => (url += `job_ids=${jobId}&`));
        const response = await fetch(url.slice(0, -1));
        // set modal buttons before status modal opens
        setModalButtons(["Close"]);
        if (response.status === 200) {
          const { jobs } = await response.json();

          for (const job of jobs) {
            const presignedUrl = job.url;
            // hopefully no errors, for fail safe in case one returns no url when not found in s3
            if (presignedUrl) {
              const fileName = presignedUrl.split("/")[presignedUrl.length - 1];

              // setup temporary download link
              const link = document.createElement("a");
              link.href = presignedUrl; // assign link to hit presigned url
              link.download = fileName; // set new downloaded files name to analyzed file name
              document.body.appendChild(link);

              // click to download
              link.click();
              link.remove();
            }
          }

          setModalLabels({
            header: "Success!",
            messages: [
              `The following number of analyses have been successfully downloaded: ${numberOfJobs}`,
              "They can be found in your local downloads folder.",
            ],
          });

          setModalState("generic");
        } else {
          throw Error();
        }
      } else {
        // let user know in the off chance that the only files they selected are not finished analyzing or failed
        setModalLabels(modalObjs.nothingToDownload);
        setModalButtons(["Close"]);
        setModalState("generic");
      }
    } catch (e) {
      console.log("ERROR fetching presigned url to download analysis");
      setModalLabels(modalObjs.downloadError);
      setModalState("generic");
    }
  };

  return (
    <>
      {loading ? (
        <SpinnerContainer id="spinnerContainer">
          <CircularSpinner color={"secondary"} size={200} />
        </SpinnerContainer>
      ) : (
        <PageContainer>
          <DropDownContainer>
            <DropDownWidget
              label="Actions"
              options={["Download", "Delete", "Interactive Analysis"]}
              disableOptions={[
                ...Array(2).fill(
                  checkedJobs.length === 0 && checkedUploads.length === 0
                ),
                checkedJobs.length !== 1,
              ]}
              optionsTooltipText={[
                ...Array(2).fill(
                  "Must make a selection below before actions become available."
                ),
                "Can only be performed on one job at a time",
              ]}
              handleSelection={handleDropdownSelection}
              reset={resetDropdown}
            />
          </DropDownContainer>
          <Container>
            <TableContainer
              component={Paper}
              sx={{ backgroundColor: "var(--light-gray" }}
            >
              <Table aria-label="collapsible table" size="small">
                <TableHead
                  sx={{
                    backgroundColor: "var(--dark-blue)",
                  }}
                >
                  <TableRow
                    sx={{
                      height: "60px",
                    }}
                  >
                    <TableCell />
                    <TableCell
                      sx={{
                        color: "var(--light-gray)",
                      }}
                    >
                      RECORDING&nbsp;NAME
                    </TableCell>
                    <TableCell
                      sx={{
                        color: "var(--light-gray)",
                      }}
                      align="center"
                    >
                      UPLOAD&nbsp;ID
                    </TableCell>
                    <TableCell
                      sx={{
                        color: "var(--light-gray)",
                      }}
                      align="center"
                    >
                      CREATED&nbsp;AT
                    </TableCell>
                    <TableCell
                      sx={{
                        color: "var(--light-gray)",
                      }}
                      align="center"
                    >
                      LAST&nbsp;ANALYZED
                    </TableCell>
                    <TableCell />
                  </TableRow>
                </TableHead>
                <TableBody>
                  {rows.map((row) => (
                    <Row
                      key={row.id}
                      row={row}
                      setCheckedJobs={setCheckedJobs}
                      checkedJobs={checkedJobs}
                      setCheckedUploads={setCheckedUploads}
                      checkedUploads={checkedUploads}
                      setModalLabels={setModalLabels}
                      setModalButtons={setModalButtons}
                      setModalState={setModalState}
                    />
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </Container>
        </PageContainer>
      )}
      <ModalWidget
        open={modalState === "generic"}
        labels={modalLabels.messages}
        buttons={modalButtons}
        closeModal={handleModalClose}
        header={modalLabels.header}
      />
      <ModalWidget
        open={["downloading", "deleting"].includes(modalState)}
        labels={[]}
        buttons={[]}
        header={
          modalState === "downloading"
            ? "Downloading in progress..."
            : "Deleting in progress..."
        }
      >
        <ModalSpinnerContainer>
          <CircularSpinner size={200} color={"secondary"} />
        </ModalSpinnerContainer>
      </ModalWidget>
      <ModalWidget
        open={openInteractiveAnalysis}
        labels={[]}
        buttons={[]}
        header="Interactive Waveform Analysis"
        width={1500}
      >
        <InteractiveAnalysisModal />
      </ModalWidget>
    </>
  );
}

Uploads.getLayout = (page) => {
  return <DashboardLayout>{page}</DashboardLayout>;
};
