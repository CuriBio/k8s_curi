import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableContainer from "@mui/material/TableContainer";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import Paper from "@mui/material/Paper";
import CircularSpinner from "@/components/basicWidgets/CircularSpinner";
import DropDownWidget from "@/components/basicWidgets/DropDownWidget";
import DashboardLayout, {
  UploadsContext,
} from "@/components/layouts/DashboardLayout";
import styled from "styled-components";
import { useContext, useState, useEffect } from "react";
import Row from "@/components/uploads/TableRow"

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
  left: 70%;
  position: relative;
  margin: 3% 1% 1% 1%;
`;


export default function Uploads() {
  const { uploads } = useContext(UploadsContext);
  const [jobs, setJobs] = useState();
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [checkedJobs, setCheckedJobs] = useState([]);
  const [checkedUploads, setCheckedUploads] = useState([]);
  
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
    const uploadsInterval = setInterval(() => getAllJobs(), [1e4]);
    // clear interval when switching pages
    return () => clearInterval(uploadsInterval);
  }, [uploads]);


  useEffect(() => {
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
    if (jobs) setLoading(false);
  }, [jobs]);

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
              disabled={checkedJobs === [] && checkedUploads === []}
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
    </>
  );
}

Uploads.getLayout = (page) => {
  return <DashboardLayout>{page}</DashboardLayout>;
};
