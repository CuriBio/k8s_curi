import DashboardLayout, {
  UploadsContext,
} from "@/components/layouts/DashboardLayout";
import styled from "styled-components";
import CircularSpinner from "@/components/basicWidgets/CircularSpinner";
import { useEffect, useState, useCallback, useContext, useRef } from "react";
import {
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TablePagination,
  TableRow,
} from "@mui/material";
import { useRouter } from "next/router";

const Container = styled.div`
  display: flex;
  max-height: 85%;
  position: relative;
  justify-content: start;
  width: 80%;
  padding-top: 5%;
  flex-direction: column;
`;

const SpinnerContainer = styled.div`
  display: flex;
  justify-content: center;
  align-items: center;
  width: 80%;
  height: 100%;
  margin-left: 10%;
`;

const DownloadLink = styled.span`
  &:hover {
    color: var(--teal-green);
    cursor: pointer;
    text-decoration: underline;
  }
`;

const columns = [
  { id: "uploadId", label: "Upload\u00a0ID" },
  { id: "datetime", label: "Datetime" },
  {
    id: "uploadedFile",
    label: "Uploaded\u00a0File",
  },
  {
    id: "analyzedFile",
    label: "Analyzed\u00a0File",
  },
  {
    id: "status",
    label: "Status",
  },
  {
    id: "meta",
    label: "Meta",
  },
  {
    id: "download",
    label: "Download",
  },
];
export default function Uploads() {
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);
  const [jobs, setJobs] = useState();
  const [rows, setRows] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const { uploads } = useContext(UploadsContext);
  const router = useRouter();

  const getJobs = async () => {
    const response = await fetch("http://localhost/jobs");

    if (response && response.status === 200) {
      const { jobs } = await response.json();
      setJobs(jobs);
    } else if (response && [403, 401].includes(response.status)) {
      router.replace("/login", null, { shallow: true });
    }
  };

  useEffect(() => {
    if (uploads.length > 0) getJobs();
  }, [uploads]);

  const handleChangePage = (e, newPage) => {
    setPage(newPage);
  };

  const handleChangeRowsPerPage = (e) => {
    setRowsPerPage(+e.target.value);
    setPage(0);
  };

  // add param to GET /jobs to return only one presigned URL
  const downloadAnalysis = async ({ target }) => {
    await getJobs();
    const selectedJob = jobs.find((job) => job.upload_id === target.id);

    const presignedUrl = selectedJob.url;
    const fileName = presignedUrl.split("/")[presignedUrl.length - 1];

    // setup temporary download link
    const link = document.createElement("a");
    link.href = presignedUrl; // assign link to hit presigned url
    link.download = fileName; // set new downloaded files name to analyzed file name

    document.body.appendChild(link);

    // click to download
    link.click();
    link.remove();
  };

  const formatUploads = useCallback(() => {
    setIsLoading(true);
    if (jobs) {
      const formattedRows = jobs.map(
        ({ upload_id, created_at, object_key, status }) => {
          const uploadedFilename = uploads.find(
            (el) => el.id === upload_id
          ).filename;

          const analyzedFile = object_key
            ? object_key.split("/")[object_key.split("/").length - 1]
            : "";

          const formattedDate = new Date(created_at).toLocaleDateString(
            undefined,
            {
              hour: "numeric",
              minute: "numeric",
            }
          );

          return {
            uploadId: upload_id,
            uploadedFile: uploadedFilename,
            analyzedFile,
            datetime: formattedDate,
            download: status === "finished" ? "Download analysis" : "",
            status,
          };
        }
      );
      setIsLoading(false);
      setRows([...formattedRows]);
    }
  }, [jobs]);

  useEffect(() => {
    formatUploads();
  }, [formatUploads]);

  return (
    <Container>
      {isLoading ? (
        <SpinnerContainer id="spinnerContainer">
          <CircularSpinner color={"secondary"} size={125} />
        </SpinnerContainer>
      ) : (
        <>
          <TableContainer
            sx={{
              width: "80%",
              maxHeight: "93%",
              marginLeft: "10%",
              borderLeft: "1px solid var(--dark-gray)",
              borderRight: "1px solid var(--dark-gray)",
            }}
          >
            <Table stickyHeader aria-label="sticky table">
              <TableHead>
                <TableRow>
                  {columns.map((column) => (
                    <TableCell
                      id={column.id}
                      key={column.id}
                      align="center"
                      sx={{
                        backgroundColor: "var(--dark-blue)",
                        color: "var(--light-gray)",
                        textAlign: "center",
                        borderRight: "none",
                      }}
                    >
                      {column.label}
                    </TableCell>
                  ))}
                </TableRow>
              </TableHead>
              <TableBody>
                {new Array(rowsPerPage).fill().map((row, idx) => {
                  const uploadIdx = idx + page * rowsPerPage;

                  return (
                    <TableRow
                      hover
                      role="checkbox"
                      tabIndex={-1}
                      key={idx}
                      sx={{ maxHeight: "50px" }}
                    >
                      {columns.map((column, idx) => {
                        let value = null;
                        if (rows[uploadIdx]) value = rows[uploadIdx][column.id];
                        // used to download file. needs access to upload ID

                        const id = rows[uploadIdx]
                          ? rows[uploadIdx].uploadId
                          : null;
                        return (
                          <TableCell
                            align="center"
                            key={column.id}
                            id={id}
                            sx={{
                              maxWidth: "300px",
                              borderRight: "1px solid var(--dark-gray)",
                              overflowX: "scroll",
                              whiteSpace: "nowrap",
                              fontSize: "12px",
                              maxHeight: "50px",
                              backgroundColor:
                                idx % 2 === 0 ? "var(--light-gray)" : "white",
                            }}
                            onClick={
                              value === "Download analysis"
                                ? downloadAnalysis
                                : null
                            }
                          >
                            {value === "Download analysis" ? (
                              <DownloadLink id={id}>{value}</DownloadLink>
                            ) : (
                              value
                            )}
                          </TableCell>
                        );
                      })}
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </TableContainer>
          <TablePagination
            sx={{
              backgroundColor: "var(--dark-gray)",
              width: "80%",
              marginLeft: "10%",
            }}
            rowsPerPageOptions={[10, 25, 50]}
            component="div"
            count={rows.length}
            rowsPerPage={rowsPerPage}
            page={page}
            onPageChange={handleChangePage}
            onRowsPerPageChange={handleChangeRowsPerPage}
          />
        </>
      )}
    </Container>
  );
}

Uploads.getLayout = (page) => {
  return <DashboardLayout>{page}</DashboardLayout>;
};
