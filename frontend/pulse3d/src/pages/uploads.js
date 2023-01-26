import CircularSpinner from "@/components/basicWidgets/CircularSpinner";
import DropDownWidget from "@/components/basicWidgets/DropDownWidget";
import ModalWidget from "@/components/basicWidgets/ModalWidget";
import DashboardLayout, { UploadsContext } from "@/components/layouts/DashboardLayout";
import styled from "styled-components";
import { useContext, useState, useEffect } from "react";
import InteractiveAnalysisModal from "@/components/interactiveAnalysis/InteractiveAnalysisModal";
import { AuthContext } from "@/pages/_app";
import DataTable from "react-data-table-component";
import UploadsSubTable from "@/components/table/UploadsSubTable";
import Checkbox from "@mui/material/Checkbox";
import ResizableColumn from "@/components/table/ResizableColumn";
import ColumnHead from "@/components/table/ColumnHead";

// These can be overridden on a col-by-col basis by setting a value in an  obj in the columns array above
const columnProperties = {
  center: false,
  sortable: true,
};

const customStyles = {
  headRow: {
    style: {
      backgroundColor: "var(--dark-blue)",
      color: "white",
      fontSize: "1.2rem",
    },
  },
  subHeader: {
    style: {
      backgroundColor: "var(--dark-blue)",
    },
  },
  expanderCell: {
    style: { flex: "0" },
  },
  expanderButton: {},
  rows: {
    style: {
      height: "60px",
    },
  },
  cells: {
    style: { padding: "0 2rem 0 0" },
  },
};

const TableContainer = styled.div`
  margin: 3% 3% 3% 3%;
  overflow: auto;
  box-shadow: 0px 5px 5px -3px rgb(0 0 0 / 30%), 0px 8px 10px 1px rgb(0 0 0 / 20%),
    0px 3px 14px 2px rgb(0 0 0 / 12%);
`;
const SpinnerContainer = styled.div`
  margin: 50px;
`;

const InteractiveAnalysisContainer = styled.div`
  width: 78%;
  margin: 1%;
  background-color: white;
  height: 800px;
  border-radius: 5px;
  overflow: none;
`;

const PageContainer = styled.div`
  width: 85%;
`;
const DropDownContainer = styled.div`
  width: 200px;
  background-color: white;
  border-radius: 5px;
  height: 40px;
  margin: 10px 0px;
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
    messages: ["Please confirm the deletion.", "Be aware that this action cannot be undone."],
  },
  downloadError: {
    header: "Error Occurred!",
    messages: ["An error occurred while attempting to download.", "Please try again."],
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
    messages: ["There was an issue while deleting the files you selected.", "Please try again later."],
  },
  nothingToDownload: {
    header: "Oops..",
    messages: [
      "There is nothing to download.",
      "Please make sure you are attempting to download finished analyses.",
    ],
  },
  unauthorizedDelete: {
    header: "Warning!",
    messages: [
      "You are not allowed to delete any files under a different user's account.",
      "Would you like to proceed with only those listed under your own?",
    ],
  },
};
export default function Uploads() {
  const { accountType, usageQuota } = useContext(AuthContext);
  const { uploads, setFetchUploads, pulse3dVersions } = useContext(UploadsContext);
  const [jobs, setJobs] = useState([]);
  const [rows, setRows] = useState([]);
  const [displayRows, setDisplayRows] = useState([]);
  const [checkedJobs, setCheckedJobs] = useState([]);
  const [checkedUploads, setCheckedUploads] = useState([]);
  const [resetDropdown, setResetDropdown] = useState(false);
  const [modalState, setModalState] = useState(false);
  const [modalLabels, setModalLabels] = useState({ header: "", messages: [] });
  const [modalButtons, setModalButtons] = useState([]);
  const [openInteractiveAnalysis, setOpenInteractiveAnalysis] = useState(false);
  const [selectedAnalysis, setSelectedAnalysis] = useState();
  const [pending, setPending] = useState(true);
  const [filterString, setFilterString] = useState("");
  const [filterColumn, setFilterColumn] = useState("");
  const [ownerWidth, setOwnerWidth] = useState("10%");
  const [recordingWidth, setRecordingWidth] = useState("30%");
  const [uploadWidth, setUploadWidth] = useState("25%");
  const [createdWidth, setCreatedWidth] = useState("19%");
  const [analyzedWidth, setAnalyzedWidth] = useState("19%");
  const [sortColumn, setSortColumn] = useState("");
  const [uploadTableColumns, setUploadTableColumns] = useState([]);
  const [jobsInSelectedUpload, setJobsInSelectedUpload] = useState(0);

  useEffect(() => {
    // removing loading spinner once jobs have been recieved or if 0 jobs were receieved because there were zero uploads for new users
    if (jobs.length > 0 || (jobs.length === 0 && uploads)) {
      setPending(false);
    }
  }, [displayRows]);

  useEffect(() => {
    const displayOwner = displayRows.filter(({ username }) => username).length == displayRows.length;

    setUploadTableColumns([
      {
        width: "3%",
        display: true,
        cell: (row) => (
          <Checkbox id={row.id} checked={checkedUploads.includes(row.id)} onChange={handleCheckedUploads} />
        ),
      },
      {
        name: (
          <ColumnHead
            title="Owner"
            setFilterString={setFilterString}
            columnName="username"
            setFilterColumn={setFilterColumn}
            width={ownerWidth.replace("%", "")}
            filterColumn={filterColumn}
            setSelfWidth={setOwnerWidth}
            setRightNeighbor={setRecordingWidth}
            rightWidth={recordingWidth.replace("%", "")}
            setSortColumns={setSortColumn}
            sortColumn={sortColumn}
          />
        ),
        width: ownerWidth,
        display: displayOwner,
        sortFunction: (rowA, rowB) => rowA.username.localeCompare(rowB.username),
        cell: (row) => <ResizableColumn content={row.username} />,
      },
      {
        name: (
          <ColumnHead
            title="Recording Name"
            setFilterString={setFilterString}
            columnName="name"
            setFilterColumn={setFilterColumn}
            width={recordingWidth.replace("%", "")}
            filterColumn={filterColumn}
            setSelfWidth={setRecordingWidth}
            setRightNeighbor={setUploadWidth}
            rightWidth={uploadWidth.replace("%", "")}
            setSortColumns={setSortColumn}
            sortColumn={sortColumn}
          />
        ),
        width: recordingWidth,
        display: true,
        sortFunction: (rowA, rowB) => rowA.name.localeCompare(rowB.name),
        cell: (row) => <ResizableColumn content={row.name} />,
      },
      {
        name: (
          <ColumnHead
            title="Upload ID"
            setFilterString={setFilterString}
            columnName="id"
            setFilterColumn={setFilterColumn}
            width={uploadWidth.replace("%", "")}
            filterColumn={filterColumn}
            setSelfWidth={setUploadWidth}
            setRightNeighbor={setCreatedWidth}
            rightWidth={createdWidth.replace("%", "")}
            setSortColumns={setSortColumn}
            sortColumn={sortColumn}
          />
        ),
        width: uploadWidth,
        display: true,
        sortFunction: (rowA, rowB) => rowA.id.localeCompare(rowB.id),
        cell: (row) => <ResizableColumn content={row.id} />,
      },
      {
        name: (
          <ColumnHead
            title="Date Created"
            setFilterString={setFilterString}
            columnName="createdAt"
            setFilterColumn={setFilterColumn}
            width={createdWidth.replace("%", "")}
            filterColumn={filterColumn}
            setSelfWidth={setCreatedWidth}
            setRightNeighbor={setAnalyzedWidth}
            rightWidth={analyzedWidth.replace("%", "")}
            setSortColumns={setSortColumn}
            sortColumn={sortColumn}
          />
        ),
        width: createdWidth,
        display: true,
        sortFunction: (rowA, rowB) => new Date(rowB.createdAt) - new Date(rowA.createdAt),
        cell: (row) => <ResizableColumn content={row.createdAt} />,
      },
      {
        name: (
          <ColumnHead
            title="Last Analyzed"
            setFilterString={setFilterString}
            columnName="lastAnalyzed"
            setFilterColumn={setFilterColumn}
            width={analyzedWidth.replace("%", "")}
            filterColumn={filterColumn}
            setSelfWidth={setAnalyzedWidth}
            setRightNeighbor={() => {}}
            setSortColumns={setSortColumn}
            sortColumn={sortColumn}
            last={true}
          />
        ),
        width: analyzedWidth,
        id: "lastAnalyzed",
        display: true,
        sortFunction: (rowA, rowB) => new Date(rowB.lastAnalyzed) - new Date(rowA.lastAnalyzed),
        cell: (row) => {
          //make sure to use the correct last analyzed date
          const latestDate = row.jobs.map((job) => job.datetime).sort((a, b) => new Date(b) - new Date(a))[0];
          return <ResizableColumn last={true} content={latestDate} />;
        },
      },
    ]);

    if (displayOwner) {
      // admin accounts have an extra Owners column so the widths should be different
      setCreatedWidth("13%");
      setAnalyzedWidth("13%");
    }
  }, [displayRows, checkedUploads]);

  const filterColumns = () => {
    return rows.filter((row) => {
      return row[filterColumn].toLocaleLowerCase().includes(filterString.toLocaleLowerCase());
    });
  };
  //when filter string changes, refilter results
  useEffect(() => {
    if (filterColumn) {
      const newList = filterColumns();
      if (newList.length > 0) {
        setDisplayRows(newList);
      }
    }
  }, [filterString]);

  useEffect(() => {
    if (!openInteractiveAnalysis) {
      // reset when interactive analysis modal closes
      resetTable();
    }
  }, [openInteractiveAnalysis]);

  const resetTable = () => {
    setResetDropdown(true);
    setCheckedUploads([]);
    setCheckedJobs([]);
    getAllJobs();
  };

  const getAllJobs = async () => {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_PULSE3D_URL}/jobs?download=False`);
      if (response && response.status === 200) {
        const { jobs } = await response.json();

        const newJobs = jobs.map(({ id, upload_id, created_at, object_key, status, meta, owner }) => {
          const analyzedFile = object_key ? object_key.split("/")[object_key.split("/").length - 1] : "";
          const formattedTime = formatDateTime(created_at);
          const parsedMeta = JSON.parse(meta);
          const analysisParams = parsedMeta.analysis_params;
          // add pulse3d version used on job to be displayed with other analysis params
          analysisParams.pulse3d_version = parsedMeta.version;
          const isChecked = checkedJobs.includes(id);
          return {
            jobId: id,
            uploadId: upload_id,
            analyzedFile,
            datetime: formattedTime,
            status,
            analysisParams,
            version: pulse3dVersions[0], // tag with latest version for now, can't be before v0.25.1
            checked: isChecked,
            owner,
          };
        });
        setJobs(newJobs);
      }
    } catch (e) {
      console.log("ERROR fetching jobs in /uploads");
    }
  };

  const formatDateTime = (datetime) => {
    if (datetime)
      return new Date(datetime + "Z").toLocaleDateString(undefined, {
        hour: "numeric",
        minute: "numeric",
      });
    else {
      const now = new Date();
      const datetime =
        now.getFullYear() +
        "-" +
        (now.getMonth() + 1) +
        "-" +
        now.getDate() +
        "-" +
        now.getHours() +
        now.getMinutes() +
        now.getSeconds();
      return datetime;
    }
  };

  useEffect(() => {
    if (uploads) {
      getAllJobs();

      if (uploads.length > 0) {
        const statusUpdateInterval = setInterval(async () => {
          if (!["downloading", "deleting"].includes(modalState) && !openInteractiveAnalysis) {
            await getAllJobs();
          }
        }, [1e4]);

        return () => clearInterval(statusUpdateInterval);
      }
    }
  }, [uploads]);

  useEffect(() => {
    // reset to false everytime it gets triggered
    if (resetDropdown) setResetDropdown(false);
  }, [resetDropdown]);

  useEffect(() => {
    if (uploads) {
      const formattedUploads = uploads.map(({ username, id, filename, created_at, owner }) => {
        const formattedTime = formatDateTime(created_at);
        const recName = filename ? filename.split(".")[0] : null;
        const uploadJobs = jobs
          .filter(({ uploadId }) => uploadId === id)
          .sort((a, b) => new Date(b.datetime) - new Date(a.datetime));
        const lastAnalyzed = uploadJobs[0] ? uploadJobs[0].datetime : formattedTime;
        return {
          username,
          name: recName,
          id,
          createdAt: formattedTime,
          lastAnalyzed,
          jobs: uploadJobs,
          owner,
        };
      });
      formattedUploads.sort((a, b) => new Date(b.lastAnalyzed) - new Date(a.lastAnalyzed));
      setRows([...formattedUploads]);
      setDisplayRows([...formattedUploads]);

      if (filterColumn) {
        const newList = filterColumns();
        if (newList.length > 0) {
          setDisplayRows(newList);
        }
      }
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
        downloadAnalyses();
      } else {
        setModalButtons(["Close", "Continue"]);
        setModalLabels(modalObjs.containsFailedJob);
        setModalState("generic");
      }
    } else if (option === 2) {
      const jobDetails = jobs.filter(({ jobId }) => jobId == checkedJobs[0]);
      setSelectedAnalysis(jobDetails[0]);
      const uploadId = jobDetails[0].uploadId;
      for (let uploadIdx in displayRows) {
        if (displayRows[uploadIdx].id === uploadId) {
          setJobsInSelectedUpload(displayRows[uploadIdx].jobs.length);
        }
      }
      setOpenInteractiveAnalysis(true);
    }
  };

  const handleDownloadSubSelection = async ({ Download }) => {
    if (Download === 1) {
      try {
        if (checkedUploads.length === 1) {
          await downloadSingleFile({ uploadId: checkedUploads[0] });
          resetTable();
        } else if (checkedUploads.length > 1) {
          // show active downloading modal only for multifile downloads
          setModalLabels(modalObjs.empty);
          setModalState("downloading");

          await downloadMultiFiles(checkedUploads, true);

          // show successful download modal only for multifile downloads
          setModalLabels({
            header: "Success!",
            messages: [
              `The following number of recording files have been successfully downloaded: ${checkedUploads.length}`,
              "They can be found in your local downloads folder.",
            ],
          });
          setModalButtons(["Close"]);
          setModalState("generic");
        }
      } catch (e) {
        console.log(`ERROR fetching presigned url to download recording files: ${e}`);
        setModalLabels(modalObjs.downloadError);
        setModalButtons(["Close"]);
        setModalState("generic");
      }
    } else {
      handleDropdownSelection(Download);
    }
  };

  const handleDeletions = async () => {
    // NOTE the query that soft deletes the files will also fail even if non-owner files get sent since the user_ids will not match to what's in the database
    //remove all pending from list
    const jobsToDelete = jobs.filter(
      ({ jobId, status, owner }) => checkedJobs.includes(jobId) && status !== "pending" && owner
    );
    // get upload meta data
    const uploadsToDelete = displayRows.filter(
      ({ id, jobs, owner }) =>
        checkedUploads.includes(id) && jobs.filter((job) => job.status === "pending").length == 0 && owner
    );

    try {
      let failedDeletion = false;
      //soft delete uploads
      if (uploadsToDelete) {
        // filter for uploads where there are no pending jobs to prevent deleting uploads for pending jobs
        const finalUploadIds = uploadsToDelete.map(({ id }) => id);

        if (finalUploadIds && finalUploadIds.length > 0) {
          const uploadsURL = `${process.env.NEXT_PUBLIC_PULSE3D_URL}/uploads?`;
          finalUploadIds.map((id) => (uploadsURL += `upload_ids=${id}&`));

          const uploadsResponse = await fetch(uploadsURL.slice(0, -1), {
            method: "DELETE",
          });

          failedDeletion ||= uploadsResponse.status !== 200;
        }
      }

      // soft delete all jobs
      if (jobsToDelete.length > 0) {
        const jobsURL = `${process.env.NEXT_PUBLIC_PULSE3D_URL}/jobs?`;
        jobsToDelete.map(({ jobId }) => (jobsURL += `job_ids=${jobId}&`));
        const jobsResponse = await fetch(jobsURL.slice(0, -1), {
          method: "DELETE",
        });

        failedDeletion ||= jobsResponse.status !== 200;
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
      console.log("ERROR attempting to soft delete selected jobs and uploadfs");
    }
  };

  const checkOwnerOfFiles = async () => {
    const ownerOfUploads =
      displayRows.filter(({ id, owner }) => checkedUploads.includes(id) && owner).length ==
      checkedUploads.length;

    const ownerOfJobs =
      jobs.filter(({ jobId, owner }) => checkedJobs.includes(jobId) && owner).length == checkedJobs.length;

    return ownerOfJobs && ownerOfUploads;
  };

  const handleModalClose = async (idx) => {
    if (modalButtons[idx] === "Continue") {
      // this block gets hit when user chooses to continue without 'error' status analyses
      downloadAnalyses();
    } else if (modalButtons[idx] === "Confirm") {
      const ownerCheck = await checkOwnerOfFiles();
      if (!ownerCheck && accountType !== "admin") {
        // set in progress
        setModalLabels(modalObjs.unauthorizedDelete);
        setModalButtons(["Close", "Proceed"]);
        setModalState("generic");
      } else {
        await startDeleting();
      }
    } else if (modalButtons[idx] === "Proceed") {
      await startDeleting();
    } else {
      // close in progress modal
      // also resets for any 'Close' modal button events
      // index 0 in buttons
      setModalState(false);
      resetTable();
    }
  };

  const startDeleting = async () => {
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
      resetTable();
    }
  };

  const downloadAnalyses = async () => {
    // removes any jobs with error + pending statuses
    const finishedJobs = jobs.filter(
      ({ jobId, status }) => checkedJobs.includes(jobId) && status === "finished"
    );
    const numberOfJobs = finishedJobs.length;

    if (numberOfJobs > 0) {
      setModalButtons(["Close"]);

      /*
          Download correct number of files,
          else throw error to prompt error modal
        */
      try {
        if (numberOfJobs === 1) {
          await downloadSingleFile(finishedJobs[0]);
          // table only resets on download success modal close, so this needs to be handled here
          resetTable();
        } else if (numberOfJobs > 1) {
          // show active downloading modal only for multifile downloads
          setModalLabels(modalObjs.empty);
          setModalState("downloading");

          await downloadMultiFiles(finishedJobs);

          // show successful download modal only for multifile downloads
          setModalLabels({
            header: "Success!",
            messages: [
              `The following number of analyses have been successfully downloaded: ${numberOfJobs}`,
              "They can be found in your local downloads folder.",
            ],
          });

          setModalState("generic");
        }
      } catch (e) {
        console.log(`ERROR fetching presigned url to download analysis: ${e}`);
        setModalLabels(modalObjs.downloadError);
        setModalState("generic");
      }
    } else {
      // let user know in the off chance that the only files they selected are not finished analyzing or failed
      setModalLabels(modalObjs.nothingToDownload);
      setModalButtons(["Close"]);
      setModalState("generic");
    }
  };

  const downloadSingleFile = async ({ jobId, uploadId }) => {
    // request only presigned urls for selected job/upload
    try {
      let response = null,
        presignedUrl = null,
        name = null;
      if (jobId) {
        const url = `${process.env.NEXT_PUBLIC_PULSE3D_URL}/jobs?job_ids=${jobId}`;
        response = await fetch(url);

        if (response.status === 200) {
          const { jobs } = await response.json();
          presignedUrl = jobs[0].url;
          name = jobs[0].id;
        }
      } else {
        const url = `${process.env.NEXT_PUBLIC_PULSE3D_URL}/uploads/download`;
        response = await fetch(url, {
          method: "POST",
          body: JSON.stringify({ upload_ids: [uploadId] }),
        });

        if (response.status === 200) {
          const { filename, url } = await response.json();
          presignedUrl = url;
          name = filename;
        }
      }

      if (presignedUrl) {
        const a = document.createElement("a");
        document.body.appendChild(a);
        a.setAttribute("href", presignedUrl);
        a.setAttribute("download", name);
        a.click();
        a.remove();
      } else {
        throw Error();
      }
    } catch (e) {
      throw Error();
    }
  };

  const downloadMultiFiles = async (data, uploads = false) => {
    try {
      //streamsaver has to be required here otherwise you get build errors with "document is not defined"
      const { createWriteStream } = require("streamsaver");
      let url = null,
        zipFilename = null,
        body = null;
      const now = formatDateTime();

      if (uploads) {
        url = `${process.env.NEXT_PUBLIC_PULSE3D_URL}/uploads/download`;
        zipFilename = `MA-recordings__${now}__${data.length}.zip`;
        body = { upload_ids: data };
      } else {
        const jobIds = data.map(({ jobId }) => jobId);
        url = `${process.env.NEXT_PUBLIC_PULSE3D_URL}/jobs/download`;
        zipFilename = `MA-analyses__${now}__${data.length}.zip`;
        body = { job_ids: jobIds };
      }

      const response = await fetch(url, {
        method: "POST",
        body: JSON.stringify(body),
      });

      if (response.status === 200) {
        // only stream to file if not firefox. Once the underlying issue with streaming on
        // firefox is fixed, should remove this
        if (navigator.userAgent.indexOf("Firefox") != -1) {
          const file = await response.blob();
          const url = window.URL.createObjectURL(file);

          const a = document.createElement("a");
          document.body.appendChild(a);
          a.setAttribute("href", url);
          a.setAttribute("download", zipFilename);
          a.click();
          a.remove();
        } else {
          const fileStream = createWriteStream(zipFilename);
          const writer = fileStream.getWriter();

          if (response.body.pipeTo) {
            writer.releaseLock();
            return response.body.pipeTo(fileStream);
          }

          const reader = response.body.getReader();

          () =>
            reader
              .read()
              .then(({ value, done }) => (done ? writer.close() : writer.write(value).then(pump)))();
        }
      } else {
        throw Error();
      }
    } catch (e) {
      console.log(`ERROR during multi file download: ${e}`);
      throw Error();
    }
  };

  const ExpandedComponent = ({ data }) => {
    return (
      <UploadsSubTable jobs={data.jobs} checkedJobs={checkedJobs} handleCheckedJobs={handleCheckedJobs} />
    );
  };

  const handleCheckedUploads = (e) => {
    // first check if change is adding or removing an upload
    if (!checkedUploads.includes(e.target.id)) {
      // if adding, push to state
      checkedUploads.push(e.target.id);
    } else {
      // if removing, splice to state
      const idxToSplice = checkedUploads.indexOf(e.target.id);
      checkedUploads.splice(idxToSplice, 1);
    }
    // set state
    setCheckedUploads([...checkedUploads]);

    const newCheckedJobs = [];

    // every checked upload should have all of it's jobs checked
    // so it's resetting checkedJobs to empty array, then concat all relevant jobs
    checkedUploads.map((upload) => {
      const idx = rows.map((row) => row.id).indexOf(upload);
      const jobIds = rows[idx].jobs.map(({ jobId, status }) => {
        // only add jobs to checked array if not pending
        if (status !== "pending") newCheckedJobs.push(jobId);
      });
      newCheckedJobs.concat(jobIds);
    });

    // set jobs in state
    setCheckedJobs([...newCheckedJobs]);
  };

  const handleCheckedJobs = (e) => {
    // check if action is unchecking a job
    if (checkedJobs.includes(e.target.id)) {
      // remove from job state
      const idxToSplice = checkedJobs.indexOf(e.target.id);
      checkedJobs.splice(idxToSplice, 1);

      // remove corresponding upload as checked because a checked upload cannot have any unchecked jobs
      checkedUploads.map((upload, uploadIdx) => {
        const idx = rows.map((row) => row.id).indexOf(upload);
        const jobIds = rows[idx].jobs.map(({ jobId }) => jobId);
        const missingJobs = jobIds.filter((id) => !checkedJobs.includes(id));
        if (missingJobs.length > 0) checkedUploads.splice(uploadIdx, 1);
      });

      // set checked uploads
      setCheckedUploads([...checkedUploads]);
    } else checkedJobs.push(e.target.id); // else if action is checking a job, then push job id to state

    // set checked jobs either way
    setCheckedJobs([...checkedJobs]);
  };
  const disableOptions = () => {
    const multiTargetOptions = Array(2).fill(checkedJobs.length === 0 && checkedUploads.length === 0);
    const selectedJobsList = jobs.filter((job) => job.jobId === checkedJobs[0]);
    const singleTargetOptions =
      checkedJobs.length !== 1 ||
      (selectedJobsList.length > 0 && selectedJobsList[0].status !== "finished") ||
      (usageQuota && usageQuota.jobs_reached);
    return [...multiTargetOptions, singleTargetOptions];
  };
  return (
    <>
      {!openInteractiveAnalysis && (
        <PageContainer>
          <TableContainer>
            <DataTable
              data={displayRows}
              compact={true}
              columns={uploadTableColumns
                .filter(
                  // if admin user then show all columns, else just show non-admin columns
                  (e) => e.display
                )
                .map((e) => {
                  return {
                    ...columnProperties,
                    ...e,
                  };
                })}
              pagination
              expandableRows
              expandableRowsComponent={ExpandedComponent}
              customStyles={customStyles}
              progressPending={pending}
              defaultSortFieldId="lastAnalyzed"
              progressComponent={
                <SpinnerContainer>
                  <CircularSpinner size={200} color={"secondary"} />
                </SpinnerContainer>
              }
              sortIcon={<></>}
              subHeader={true}
              subHeaderComponent={
                <DropDownContainer>
                  <DropDownWidget
                    label="Actions"
                    options={
                      accountType === "admin"
                        ? ["Download", "Delete"]
                        : ["Download", "Delete", "Interactive Analysis"]
                    }
                    subOptions={{
                      Download: ["Download Analyses", "Download Raw Data"],
                    }}
                    disableOptions={disableOptions()}
                    optionsTooltipText={[
                      ...Array(2).fill("Must make a selection below before actions become available."),
                      usageQuota && usageQuota.jobs_reached
                        ? "Interactive analysis is disabled because customer limit has been reached."
                        : "You must select one successful job to enable interactive analysis.",
                    ]}
                    handleSelection={handleDropdownSelection}
                    handleSubSelection={handleDownloadSubSelection}
                    reset={resetDropdown}
                    disableSubOptions={{
                      Download: [checkedJobs.length === 0, checkedUploads.length === 0],
                    }}
                    subOptionsTooltipText={[
                      "Must make a job selection before becoming available.",
                      "Must make an upload selection before becoming available.",
                    ]}
                    setReset={setResetDropdown}
                  />
                </DropDownContainer>
              }
            />
          </TableContainer>
        </PageContainer>
      )}
      {openInteractiveAnalysis && (
        <InteractiveAnalysisContainer>
          <InteractiveAnalysisModal
            selectedJob={selectedAnalysis}
            setOpenInteractiveAnalysis={setOpenInteractiveAnalysis}
            numberOfJobsInUpload={jobsInSelectedUpload}
          />
        </InteractiveAnalysisContainer>
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
        header={modalState === "downloading" ? "Downloading in progress..." : "Deleting in progress..."}
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
