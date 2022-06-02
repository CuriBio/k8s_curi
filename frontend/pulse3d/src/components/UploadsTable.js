import styled from 'styled-components';
import { useWorker } from '@/components/hooks/useWorker';
import CircularSpinner from '@/components/CircularSpinner';
import { useEffect, useState } from 'react';
import {
  Paper,
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
  width: 80%;
  height: inherit;
  display: flex;
  justify-content: center;
  position: relative;
  padding-top: 5%;
`;
const SpinnerContainer = styled.div`
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100%;
`;

export default function UploadsTable() {
  const [isLoading, setIsLoading] = useState(true);
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);
  const [route, setRoute] = useState({});
  const [uploads, setUploads] = useState([]);
  const [jobs, setJobs] = useState([]);
  const [rows, setRows] = useState([]);
  const { response } = useWorker(route);

  useEffect(() => {
    if (response && response.status === 200) {
      if (response.type === 'jobStatus') setJobs(response.data.jobs);
      else if (response.type === 'downloadAnalysis') handleDownload(response);
      else setUploads(response.data);
    }
  }, [response]);

  useEffect(() => {
    setRoute({
      method: 'post',
      type: 'login',
      endpoint: 'login',
      body: {
        username: 'lucipak',
        customer_id: '60e88e2a-b101-49e2-9734-96f299fe8959',
        password: 'Test123Test123',
      },
    });
  }, []);

  useEffect(() => {
    if (uploads.length > 0)
      setRoute({
        method: 'get',
        type: 'jobStatus',
        endpoint: 'jobs',
      });
  }, [uploads]);

  useEffect(() => {
    formatUploads();
  }, [jobs]);

  useEffect(() => {
    //update UI once data is formatted
    setIsLoading(false);
  }, [rows]);

  const handleChangePage = (event, newPage) => {
    setPage(newPage);
  };

  const handleChangeRowsPerPage = (e) => {
    setRowsPerPage(+e.target.value);
    setPage(0);
  };

  const downloadAnalysis = ({ target }) => {
    const uploadId = target.id;
    // TOOO make in progress icon while downloading
    setRoute({
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

        return {
          uploadId: id,
          uploadedFile: filename,
          analyzedFile,
          datetime: formattedDate,
          download: job && job.status === 'finished' ? 'Download analysis' : '',
          status: job ? job.status : '',
          meta: job ? job.error_info : '',
        };
      }
    );
    setRows([...formattedRows]);
  };

  return (
    <Container>
      <Paper
        sx={{
          width: '80%',
          height: '85%',
          overflow: 'hidden',
          borderRadius: '2%',
          border: '1px solid var(--dark-gray)',
        }}
      >
        {isLoading ? (
          <SpinnerContainer>
            <CircularSpinner color={'rgb(167, 168, 169)'} size={125} />
          </SpinnerContainer>
        ) : (
          <>
            <TableContainer sx={{ height: '94%', minWidth: '100%' }}>
              <Table
                stickyHeader
                aria-label='sticky table'
                sx={{ height: '100%' }}
              >
                <TableHead>
                  <TableRow>
                    {columns.map((column) => (
                      <TableCell
                        key={column.id}
                        align={column.align}
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
                      <TableRow hover role='checkbox' tabIndex={-1} key={idx}>
                        {columns.map((column, idx) => {
                          let value = null;
                          if (rows[uploadIdx])
                            value = rows[uploadIdx][column.id];
                          return (
                            <TableCell
                              align='right'
                              key={column.id}
                              id={
                                rows[uploadIdx]
                                  ? rows[uploadIdx].uploadId
                                  : null
                              }
                              style={{
                                borderRight: '1px solid var(--dark-gray)',
                                overflowX: 'scroll',
                                whiteSpace: 'nowrap',
                                backgroundColor:
                                  idx % 2 === 0 ? 'var(--light-gray)' : 'white',
                              }}
                              onClick={
                                value === 'Download analysis'
                                  ? downloadAnalysis
                                  : null
                              }
                            >
                              {value}
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
              sx={{ backgroundColor: 'var(--dark-gray)' }}
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
      </Paper>
    </Container>
  );
}
