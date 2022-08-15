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

export default function Uploads() {
  const { uploads } = useContext(UploadsContext);
  const [jobs, setJobs] = useState();
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(false);
  const [checkedJobs, setCheckedJobs] = useState([]);
  const [checkedUploads, setCheckedUploads] = useState([]);
  const [resetDropdown, setResetDropdown] = useState(false);
  const [modalState, setModalState] = useState(false);
  const [modalLabels, setModalLabels] = useState({ header: "", messages: [] });
  const [modalButtons, setModalButtons] = useState([]);
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
      } else if (response && [401].includes(response.status)) {
        router.replace("/login", null, { shallow: true });
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
    // const uploadsInterval = setInterval(() => getAllJobs(), [1e4]);
    // // clear interval when switching pages
    // return () => clearInterval(uploadsInterval);
  }, [uploads]);

  useEffect(() => {
    if (jobs) {
      const formattedUploads = uploads
        .map(({ id, filename, created_at }) => {
          const formattedTime = formatDateTime(created_at);
          const recName = filename.split(".")[0];
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
      setModalLabels({
        header: "Are you sure?",
        messages: [
          "Please confirm the deletion.",
          "Be aware that this action cannot be undone.",
        ],
      });
      setModalState("delete");
    } else if (option === 0) {
      setModalLabels({
        header: null,
        messages: [],
      });
      setModalState("download");
      downloadAnalyses();
    }

    setResetDropdown(false);
  };

  const handleDeletions = async () => {
    // const response = await fetch(url.slice(0, -1));
  };

  const handleModalClose = async (idx) => {
    if (idx === 1) {
      await handleDeletions();
    }
    setModalState(false);
    setResetDropdown(true);
    setCheckedUploads([]);
    setCheckedJobs([]);
  };

  const downloadAnalyses = async () => {
    try {
      const numberOfJobs = checkedJobs.length;
      //request only presigned urls for selected jobs
      const url = `https://curibio.com/jobs?`;
      checkedJobs.map((id) => (url += `job_ids=${id}&`));
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
        setModalState("success");
      } else {
        throw Error();
      }
    } catch (e) {
      console.log("ERROR fetching presigned url to download analysis");
      setModalLabels({
        header: "Error Occurred!",
        messages: [
          "An error occurred while attempting to download.",
          "Please try again.",
        ],
      });
      setModalState("fail");
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
              label={"Actions"}
              options={["Download", "Delete"]}
              disabled={checkedJobs.length === 0 && checkedUploads.length === 0}
              handleSelection={handleDropdownSelection}
              reset={resetDropdown}
            />
          </DropDownContainer>
          <Container>
            <TableContainer
              component={Paper}
              sx={{ backgroundColor: "var(--light-gray" }}
            >
              <Table aria-label="collapsible table">
                <TableHead
                  sx={{
                    backgroundColor: "var(--dark-blue)",
                  }}
                >
                  <TableRow>
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
                    />
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </Container>
        </PageContainer>
      )}
      <ModalWidget
        open={["success", "delete"].includes(modalState)}
        labels={modalLabels.messages}
        buttons={modalButtons}
        closeModal={handleModalClose}
        header={modalLabels.header}
      />
      <ModalWidget
        open={modalState === "download"}
        labels={[]}
        buttons={[]}
        header="Downloading in progress..."
      >
        <ModalSpinnerContainer>
          <CircularSpinner size={200} color={"secondary"} />
        </ModalSpinnerContainer>
      </ModalWidget>
    </>
  );
}

Uploads.getLayout = (page) => {
  return <DashboardLayout>{page}</DashboardLayout>;
};
