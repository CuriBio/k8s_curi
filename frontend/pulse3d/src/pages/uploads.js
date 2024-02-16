import CircularSpinner from "@/components/basicWidgets/CircularSpinner";
import DropDownWidget from "@/components/basicWidgets/DropDownWidget";
import ModalWidget from "@/components/basicWidgets/ModalWidget";
import DashboardLayout, { UploadsContext } from "@/components/layouts/DashboardLayout";
import styled from "styled-components";
import { useContext, useState, useEffect, useMemo } from "react";
import InteractiveAnalysisModal from "@/components/interactiveAnalysis/InteractiveAnalysisModal";
import { AuthContext } from "@/pages/_app";
import { useRouter } from "next/router";
import JobPreviewModal from "@/components/interactiveAnalysis/JobPreviewModal";
import { formatDateTime } from "@/utils/generic";
import Table from "@/components/table/Table";
import { Box } from "@mui/material";
import Jobs from "@/components/table/Jobs";

const TableContainer = styled.div`
  margin: 3% 3% 3% 3%;
  overflow: auto;
  white-space: nowrap;
  box-shadow: 0px 5px 5px -3px rgb(0 0 0 / 30%), 0px 8px 10px 1px rgb(0 0 0 / 20%),
    0px 3px 14px 2px rgb(0 0 0 / 12%);
`;

const ModalSpinnerContainer = styled.div`
  position: relative;
  display: flex;
  justify-content: center;
  height: 315px;
  align-items: center;
`;

const DropDownContainer = styled.div`
  width: 250px;
  background-color: white;
  border-radius: 8px;
  position: relative;
  margin: 15px 20px;
`;

const LargeModalContainer = styled.div`
  width: 83%;
  min-width: 1000px;
  margin: 1%;
  top: 0px;
  position: absolute;
  background-color: white;
  border-radius: 5px;
  overflow: none;
  z-index: 5;
`;

const ModalBackdrop = styled.div`
  height: auto;
  top: 0;
  position: absolute;
  background: black;
  opacity: 0.2;
  width: 100%;
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

const getJobsList = (j) => {
  return Object.values(j).flat(2);
};

const getSelectedUploads = (u) => {
  return Object.keys(u).filter((x) => u[x]);
};

export default function Uploads() {
  const router = useRouter();
  const { accountType, usageQuota, accountScope, productPage } = useContext(AuthContext);
  const { uploads, setFetchUploads, pulse3dVersions, setDefaultUploadForReanalysis } = useContext(
    UploadsContext
  );

  const [jobs, setJobs] = useState([]);
  const [displayRows, setDisplayRows] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedUploads, setSelectedUploads] = useState({});
  const [selectedJobs, setSelectedJobs] = useState({});
  const [resetDropdown, setResetDropdown] = useState(false);
  const [modalState, setModalState] = useState(false);
  const [modalLabels, setModalLabels] = useState({ header: "", messages: [] });
  const [modalButtons, setModalButtons] = useState([]);
  const [openInteractiveAnalysis, setOpenInteractiveAnalysis] = useState(false);
  const [openJobPreview, setOpenJobPreview] = useState(false);
  const [selectedAnalysis, setSelectedAnalysis] = useState();
  const [jobsInSelectedUpload, setJobsInSelectedUpload] = useState(0);

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
    if (!openInteractiveAnalysis) {
      // reset when interactive analysis modal closes
      resetTable();
    }
  }, [openInteractiveAnalysis]);

  useEffect(() => {
    if (uploads) {
      const formattedUploads = uploads.map(({ username, id, filename, created_at, owner, auto_upload }) => {
        // const formattedTime = formatDateTime(created_at);
        const recName = filename ? filename.split(".").slice(0, -1).join(".") : null;
        const uploadJobs = jobs
          .filter(({ uploadId }) => uploadId === id)
          .sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt));

        const lastAnalyzed = uploadJobs[0] ? uploadJobs[0].createdAt : created_at;

        return {
          username,
          name: recName,
          id,
          jobs: uploadJobs,
          createdAt: created_at,
          lastAnalyzed,
          owner,
          autoUpload: auto_upload,
        };
      });

      setDisplayRows([...formattedUploads]);
      setIsLoading(false);
    }
  }, [jobs]);

  useEffect(() => {
    handleSelectedJobs();
  }, [selectedJobs]);

  useEffect(() => {
    handleSelectedUploads();
  }, [selectedUploads]);

  const columns = useMemo(
    () => [
      {
        accessorKey: "username",
        id: "username",
        header: "Owner",
        filterVariant: "autocomplete",
        size: 200,
        minSize: 130,
      },
      {
        accessorKey: "name",
        id: "name",
        header: "Recording Name",
        filterVariant: "autocomplete",
        size: 320,
        minSize: 130,
      },
      {
        accessorKey: "id", //accessorKey used to define `data` column. `id` gets set to accessorKey automatically
        filterVariant: "autocomplete",
        id: "id",
        header: "Upload ID",
        size: 320,
        minSize: 130,
      },
      {
        accessorFn: (row) => new Date(row.createdAt),
        header: "Date Created",
        id: "createdAt",
        filterVariant: "date-range",
        sortingFn: "datetime",
        size: 275,
        minSize: 275,
        Cell: ({ cell }) => formatDateTime(cell.getValue()),
      },
      {
        accessorFn: (row) => new Date(row.lastAnalyzed),
        header: "Last Analyzed",
        id: "lastAnalyzed",
        filterVariant: "date-range",
        sortingFn: "datetime",
        size: 275,
        minSize: 275,
        Cell: ({ cell }) => formatDateTime(cell.getValue()),
      },
      {
        accessorKey: "autoUpload",
        id: "autoUpload",
        filterVariant: "autocomplete",
        header: "Upload Origin",
        enableColumnFilter: false,
        enableResizing: false,
        size: 180,
        Cell: ({ cell }) =>
          cell.getValue() !== null && <div>{cell.getValue() ? `Auto Upload` : "Manual Upload"}</div>,
      },
    ],
    []
  );

  const handleSelectedJobs = () => {
    for (const uploadId in selectedJobs) {
      const uploadJobs = displayRows.find((x) => x.id === uploadId).jobs;
      const selected = selectedJobs[uploadId];
      const uploadIsSelected = uploadId in selectedUploads && selectedUploads[uploadId];

      if (uploadJobs.length === selected.length && uploadJobs.length !== 0 && !uploadIsSelected) {
        // if all jobs are selected and the parent upload isn't, then auto selected the upload
        selectedUploads[uploadId] = true;
        setSelectedUploads({ ...selectedUploads });
      } else if (uploadJobs.length > selected.length && uploadIsSelected) {
        // else if the parent upload is selected, but a user unchecks a job, then auto uncheck the parent upload
        selectedUploads[uploadId] = false;
        setSelectedUploads({ ...selectedUploads });
      }
    }
  };

  const handleSelectedUploads = () => {
    const selectedJobsCopy = JSON.parse(JSON.stringify(selectedJobs));

    for (const uploadId in selectedUploads) {
      const uploadJobs = displayRows.find((x) => x.id === uploadId).jobs;
      const uploadIsSelected = selectedUploads[uploadId];

      if (uploadIsSelected) {
        // if parent upload is selected and all the jobs aren't selected, then auto select all the jobs
        const allSelectedJobs = uploadJobs.map(({ jobId }) => jobId);
        selectedJobsCopy[uploadId] = allSelectedJobs;
        setSelectedJobs({ ...selectedJobsCopy });
      }
    }

    for (const uploadId in selectedJobsCopy) {
      if (!Object.keys(selectedUploads).includes(uploadId)) {
        selectedJobsCopy[uploadId] = [];
        setSelectedJobs({ ...selectedJobsCopy });
      }
    }
  };

  const resetTable = async () => {
    setResetDropdown(true);
    setSelectedUploads({});
    setSelectedJobs({});
    setFetchUploads(true);
    await getAllJobs();
  };

  const getAllJobs = async () => {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_PULSE3D_URL}/jobs?download=False`);
      if (response && response.status === 200) {
        const { jobs } = await response.json();

        const newJobs = jobs.map(({ id, upload_id, created_at, object_key, status, meta, owner }) => {
          const analyzedFile = object_key ? object_key.split("/")[object_key.split("/").length - 1] : "";
          const isChecked = Object.keys(selectedJobs).includes(id);
          const parsedMeta = JSON.parse(meta);
          const analysisParams = parsedMeta.analysis_params;
          // add pulse3d version used on job to be displayed with other analysis params
          analysisParams.pulse3d_version = parsedMeta.version;
          const metaParams = { analysisParams };

          if ("name_override" in parsedMeta) metaParams.nameOverride = parsedMeta.name_override;
          // handle specific errors to let users know
          if ("error" in parsedMeta) {
            if (parsedMeta.error.includes("Invalid file format")) {
              status += ": Invalid file format";
            } else if (parsedMeta.error.includes("Unable to converge")) {
              status += `: ${parsedMeta.error}`;
            }
          }

          return {
            jobId: id,
            uploadId: upload_id,
            analyzedFile,
            createdAt: created_at,
            status,
            version: pulse3dVersions[0], // tag with latest version for now
            checked: isChecked,
            owner,
            ...metaParams,
          };
        });

        setJobs([...newJobs]);
      }
    } catch (e) {
      console.log("ERROR fetching jobs in /uploads");
    }
  };

  const removeDeletedUploads = (deletedUploads) => {
    const deletedIds = deletedUploads.map(({ id }) => id);
    const filteredRows = displayRows.filter(({ id }) => !deletedIds.includes(id));
    setDisplayRows([...filteredRows]);
  };

  const handleDeletions = async () => {
    // NOTE the query that soft deletes the files will also fail even if non-owner files get sent since the user_ids will not match to what's in the database
    //remove all pending from list
    const jobsList = getJobsList(selectedJobs);
    const jobsToDelete = jobs.filter(
      ({ jobId, status, owner }) =>
        jobsList.includes(jobId) &&
        !["pending", "running"].includes(status) &&
        (owner || accountType === "admin")
    );
    // get upload meta data
    // check if upload is selected, check that upload has no actively running jobs, and check user is deleting own upload or it's an admin account
    const uploadsToDelete = displayRows.filter(
      ({ id, jobs, owner }) =>
        getSelectedUploads(selectedUploads).includes(id) &&
        !jobs.find(
          ({ status, jobId }) => !jobsList.includes(jobId) || ["pending", "running"].includes(status)
        ) &&
        (owner || accountType === "admin")
    );

    try {
      let failedDeletion = false;
      //soft delete uploads
      if (uploadsToDelete) {
        const finalUploadIds = uploadsToDelete.map(({ id }) => id);
        // filter for uploads where there are no pending jobs to prevent deleting uploads for pending jobs
        if (finalUploadIds && finalUploadIds.length > 0) {
          const uploadsURL = `${process.env.NEXT_PUBLIC_PULSE3D_URL}/uploads?`;
          finalUploadIds.map((id) => (uploadsURL += `upload_ids=${id}&`));

          const uploadsResponse = await fetch(uploadsURL.slice(0, -1), {
            method: "DELETE",
          });

          failedDeletion ||= uploadsResponse.status !== 200;
        }
      }

      // only proceed if upload successfully deleted
      if (!failedDeletion) {
        // remove uploads from list to show auto deletion, waiting for get uploads request is too slow
        // will self-correct if anything is different when actual get uploads request renders
        removeDeletedUploads(uploadsToDelete);
        // soft delete all jobs
        if (jobsToDelete.length > 0) {
          const jobsURL = `${process.env.NEXT_PUBLIC_PULSE3D_URL}/jobs?`;
          jobsToDelete.map(({ jobId }) => (jobsURL += `job_ids=${jobId}&`));

          const jobsResponse = await fetch(jobsURL.slice(0, -1), {
            method: "DELETE",
          });

          failedDeletion ||= jobsResponse.status !== 200;
        }
      }

      if (failedDeletion) {
        setModalButtons(["Close"]);
        setModalLabels(modalObjs.failedDeletion);
        setModalState("generic");
      }

      return failedDeletion;
    } catch (e) {
      console.log(e);
      console.log("ERROR attempting to soft delete selected jobs and uploads");
    }
  };

  const checkOwnerOfFiles = async () => {
    const ownerOfUploads =
      displayRows.filter(({ id, owner }) => id in selectedUploads && selectedUploads[id] && owner).length ==
      getSelectedUploads(selectedUploads).length;

    const alljobs = getJobsList(selectedJobs);
    const ownerOfJobs =
      jobs.filter(({ jobId, owner }) => alljobs.includes(jobId) && owner).length == alljobs.length;

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
    const jobsList = getJobsList(selectedJobs);
    const finishedJobs = jobs.filter(
      ({ jobId, status }) => jobsList.includes(jobId) && status === "finished"
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
      let url = null,
        zipFilename = null,
        body = null;

      const now = formatDateTime();

      // TODO use product name here instead of "MA"
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
        // TODO look at if streaming is necessary or not
        const file = await response.blob();
        const url = window.URL.createObjectURL(file);

        const a = document.createElement("a");
        document.body.appendChild(a);
        a.setAttribute("href", url);
        a.setAttribute("download", zipFilename);
        a.click();
        a.remove();
      } else {
        throw Error();
      }
    } catch (e) {
      console.log(`ERROR during multi file download: ${e}`);
      throw Error();
    }
  };

  const handleJobPreviewClick = (j) => {
    setSelectedAnalysis(j);
    setOpenJobPreview(true);
  };

  const disableOptions = () => {
    const jobsList = getJobsList(selectedJobs);
    const multiTargetOptions = Array(2).fill(
      jobsList.length === 0 && getSelectedUploads(selectedUploads).length === 0
    );

    return [...multiTargetOptions, isSingleTargetSelected(jobsList), isSingleUploadSelected()];
  };

  const isSingleTargetSelected = (jobsList) => {
    const selectedJobsList = jobs.filter((job) => job.jobId === jobsList[0]);

    return (
      jobsList.length !== 1 ||
      (selectedJobsList.length > 0 && selectedJobsList[0].status !== "finished") ||
      (usageQuota && usageQuota.jobs_reached)
    );
  };

  const isSingleUploadSelected = () => {
    if (uploads) {
      return getSelectedUploads(selectedUploads).length != 1 || (usageQuota && usageQuota.jobs_reached);
    }
  };

  const actionsFn = (t) => {
    const dropdownOptions =
      accountType === "admin"
        ? ["Download", "Delete"]
        : ["Download", "Delete", "Interactive Analysis", "Re-Analyze"];

    const checkedRows = t.getSelectedRowModel().rows;

    const handleDropdownSelection = (option) => {
      if (option === 1) {
        setModalButtons(["Close", "Confirm"]);
        setModalLabels(modalObjs.delete);
        setModalState("generic");
      } else if (option === 0) {
        // if download, check that no job contains an error status
        const jobsList = getJobsList(selectedJobs);
        const failedJobs = jobs.filter(({ jobId, status }) => jobsList.includes(jobId) && status === "error");

        if (failedJobs.length === 0) {
          downloadAnalyses();
        } else {
          setModalButtons(["Close", "Continue"]);
          setModalLabels(modalObjs.containsFailedJob);
          setModalState("generic");
        }
      } else if (option === 2) {
        const jobsList = getJobsList(selectedJobs);
        const jobDetails = jobs.find(({ jobId }) => jobId == jobsList[0]);
        setSelectedAnalysis(jobDetails);

        const jobUpload = displayRows.find(({ id }) => id === jobDetails.uploadId);
        setJobsInSelectedUpload(jobUpload.jobs.length); // used to show credit usage if necessary

        setOpenInteractiveAnalysis(true);
      } else if (option === 3) {
        // Open Re-analyze tab with name of file pre-selected
        const selectedUpload = uploads.find((upload) => upload.id == checkedRows[0].id);
        setDefaultUploadForReanalysis(selectedUpload);
        router.push("/upload-form?id=re-analyze+existing+upload");
      }
    };

    const handleDownloadSubSelection = async ({ Download }) => {
      if (Download === 1) {
        try {
          const uploadIds = getSelectedUploads(selectedUploads);
          if (uploadIds.length === 1) {
            await downloadSingleFile({ uploadId: uploadIds[0] });
            resetTable();
          } else if (uploadIds.length > 1) {
            // show active downloading modal only for multifile downloads
            setModalLabels(modalObjs.empty);
            setModalState("downloading");

            await downloadMultiFiles(uploadIds, true);

            // show successful download modal only for multifile downloads
            setModalLabels({
              header: "Success!",
              messages: [
                `The following number of recording files have been successfully downloaded: ${
                  getSelectedUploads(selectedUploads).length
                }`,
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

    return (
      <Box sx={{ width: "100%", position: "relative", display: "flex", justifyContent: "end" }}>
        <DropDownContainer>
          <DropDownWidget
            label="Actions"
            options={dropdownOptions}
            subOptions={{
              Download: ["Download Analyses", "Download Raw Data"],
            }}
            disableOptions={disableOptions()}
            optionsTooltipText={[
              ...Array(2).fill("Must make a selection below before actions become available."),
              usageQuota && usageQuota.jobs_reached
                ? "Interactive analysis is disabled because customer limit has been reached."
                : "You must select one successful job to enable interactive analysis.",
              usageQuota && usageQuota.jobs_reached
                ? "Re-analysis is disabled because customer limit has been reached."
                : "You must select one upload to enable re-analysis.",
            ]}
            handleSelection={handleDropdownSelection}
            handleSubSelection={handleDownloadSubSelection}
            reset={resetDropdown}
            disableSubOptions={{
              Download: [
                getJobsList(selectedJobs).length === 0,
                getSelectedUploads(selectedUploads).length === 0,
              ],
            }}
            subOptionsTooltipText={[
              "Must make a job selection before becoming available.",
              "Must make an upload selection before becoming available.",
            ]}
            setReset={setResetDropdown}
          />
        </DropDownContainer>
      </Box>
    );
  };

  return (
    <>
      {!openInteractiveAnalysis && (
        <TableContainer>
          <Table
            columns={columns}
            rowData={displayRows}
            defaultSortColumn={"lastAnalyzed"}
            rowSelection={selectedUploads}
            setRowSelection={setSelectedUploads}
            toolbarFn={actionsFn}
            columnVisibility={{
              username: accountType !== "user" || accountScope.includes(`${productPage}:rw_all_data`),
            }}
            subTableFn={(row) => (
              <Jobs
                row={row}
                openJobPreview={handleJobPreviewClick}
                selectedUploads={selectedUploads}
                setSelectedUploads={setSelectedUploads}
                setSelectedJobs={setSelectedJobs}
                selectedJobs={selectedJobs}
              />
            )}
            enableExpanding={true}
            isLoading={isLoading}
          />
        </TableContainer>
      )}
      {openJobPreview && (
        <>
          <ModalBackdrop />
          <LargeModalContainer>
            <JobPreviewModal setOpenJobPreview={setOpenJobPreview} selectedAnalysis={selectedAnalysis} />
          </LargeModalContainer>
        </>
      )}
      {openInteractiveAnalysis && (
        <LargeModalContainer>
          <InteractiveAnalysisModal
            selectedJob={selectedAnalysis}
            setOpenInteractiveAnalysis={setOpenInteractiveAnalysis}
            numberOfJobsInUpload={jobsInSelectedUpload}
          />
        </LargeModalContainer>
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
