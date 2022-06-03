import styled from 'styled-components';
import CircularSpinner from '@/components/CircularSpinner';
import { useEffect, useState } from 'react';
import {
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TablePagination,
  TableRow,
} from '@mui/material';

const columns = [
  { id: 'uploadId', label: 'Upload\u00a0ID' },
  { id: 'datetime', label: 'Datetime' },
  {
    id: 'uploadedFile',
    label: 'Uploaded\u00a0File',
  },
  {
    id: 'analyzedFile',
    label: 'Analyzed\u00a0File',
  },
  {
    id: 'status',
    label: 'Status',
  },
  {
    id: 'meta',
    label: 'Meta',
  },
  {
    id: 'download',
    label: 'Download',
  },
];

const Container = styled.div`
  display: flex;
  max-height: 85%;
  position: relative;
  justify-content: start;
  width: 100%;
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
  }
`;

export default function UploadsTable({ makeRequest, response }) {
  const [isLoading, setIsLoading] = useState(true);
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);
  const [uploads, setUploads] = useState([]);
  const [jobs, setJobs] = useState([]);
  const [rows, setRows] = useState([]);

  useEffect(() => {
    if (response && response.status === 200) {
      if (response.type === 'jobStatus') setJobs(response.data.jobs);
      else if (response.type === 'downloadAnalysis') handleDownload(response);
      else if (response.type === 'uploads') setUploads(response.data);
    }
  }, [response]);

  // TODO set on timer to constantly update status
  useEffect(() => {
    setIsLoading(true);

    makeRequest({
      method: 'get',
      type: 'uploads',
      endpoint: 'uploads',
    });
  }, []);

  useEffect(() => {
    if (uploads.length > 0)
      makeRequest({
        method: 'get',
        type: 'jobStatus',
        endpoint: 'jobs',
      });
  }, [uploads]);

  useEffect(() => {
    formatUploads();
  }, [jobs]);

  const handleChangePage = (e, newPage) => {
    setPage(newPage);
  };

  const handleChangeRowsPerPage = (e) => {
    setRowsPerPage(+e.target.value);
    setPage(0);
  };

  const downloadAnalysis = ({ target }) => {
    const uploadId = target.id;

    makeRequest({
      method: 'get',
      type: 'downloadAnalysis',
      endpoint: 'jobs',
      body: {
        job_ids: jobs.find((job) => job.upload_id === uploadId).id,
      },
    });
  };

  const handleDownload = async (res) => {
    const presignedUrl = res.data.jobs[0].url;
    const fileName = presignedUrl.split('/')[presignedUrl.length - 1];

    // setup temporary download link
    const link = document.createElement('a');
    link.href = presignedUrl; // assign link to hit presigned url
    link.download = fileName; // set new downloaded files name to analyzed file name

    document.body.appendChild(link);

    // click to download
    link.click();
    link.remove();
  };

  const formatUploads = () => {
    const formattedRows = uploads.map(
      ({ id, meta, created_at, object_key }) => {
        const { filename } = JSON.parse(meta);
        const job = jobs.find((job) => job.upload_id === id);

        const analyzedFile = object_key
          ? object_key.split('/')[object_key.split('/').length - 1]
          : '';

        const formattedDate = new Date(created_at).toLocaleDateString(
          undefined,
          {
            hour: 'numeric',
            minute: 'numeric',
          }
        );

        setIsLoading(false);

        return {
          uploadId: id,
          uploadedFile: filename,
          analyzedFile,
          datetime: formattedDate,
          download: job && job.status === 'finished' ? 'Download analysis' : '',
          status: job ? job.status : '',
        };
      }
    );
    setRows([...formattedRows]);
  };

  return (
    <Container>
      {isLoading ? (
        <SpinnerContainer id='spinnerContainer'>
          <CircularSpinner color={'secondary'} size={125} />
        </SpinnerContainer>
      ) : (
        <>
          <TableContainer
            sx={{
              width: '80%',
              maxHeight: '93%',
              marginLeft: '10%',
              borderLeft: '1px solid var(--dark-gray)',
              borderRight: '1px solid var(--dark-gray)',
            }}
          >
            <Table stickyHeader aria-label='sticky table'>
              <TableHead>
                <TableRow>
                  {columns.map((column) => (
                    <TableCell
                      id={column.id}
                      key={column.id}
                      align='center'
                      sx={{
                        backgroundColor: 'var(--dark-blue)',
                        color: 'var(--light-gray)',
                        textAlign: 'center',
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
                      role='checkbox'
                      tabIndex={-1}
                      key={idx}
                      sx={{ maxHeight: '50px' }}
                    >
                      {columns.map((column, idx) => {
                        let value = null;
                        if (rows[uploadIdx]) value = rows[uploadIdx][column.id];

                        return (
                          <TableCell
                            align='center'
                            key={column.id}
                            sx={{
                              maxWidth: '300px',
                              borderRight: '1px solid var(--dark-gray)',
                              overflowX: 'scroll',
                              whiteSpace: 'nowrap',
                              fontSize: '12px',
                              maxHeight: '50px',
                              backgroundColor:
                                idx % 2 === 0 ? 'var(--light-gray)' : 'white',
                            }}
                            onClick={
                              value === 'Download analysis'
                                ? downloadAnalysis
                                : null
                            }
                          >
                            <DownloadLink
                              id={
                                // used to download file. needs access to upload ID
                                rows[uploadIdx]
                                  ? rows[uploadIdx].uploadId
                                  : null
                              }
                            >
                              {value}
                            </DownloadLink>
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
              backgroundColor: 'var(--dark-gray)',
              width: '80%',
              marginLeft: '10%',
            }}
            rowsPerPageOptions={[10, 25, 50]}
            component='div'
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
