import CircularSpinner from "@/components/basicWidgets/CircularSpinner";
import DropDownWidget from "@/components/basicWidgets/DropDownWidget";
import ModalWidget from "@/components/basicWidgets/ModalWidget";
import DashboardLayout from "@/components/layouts/DashboardLayout";
import styled from "styled-components";
import { useContext, useState, useEffect, useMemo } from "react";
import InteractiveAnalysisModal from "@/components/interactiveAnalysis/InteractiveAnalysisModal";
import { AuthContext, UploadsContext } from "@/pages/_app";
import { useRouter } from "next/router";
import JobPreviewModal from "@/components/interactiveAnalysis/JobPreviewModal";
import { deepCopy, formatDateTime } from "@/utils/generic";
import { getShortUUIDWithTooltip } from "@/utils/jsx";
import Table from "@/components/table/Table";
import { Box, IconButton } from "@mui/material";
import Jobs from "@/components/table/Jobs";

const TableContainer = styled.div`
  margin: 3% 3% 3% 3%;
  overflow: auto;
  white-space: nowrap;
  box-shadow: 0px 5px 5px -3px rgb(0 0 0 / 30%), 0px 8px 10px 1px rgb(0 0 0 / 20%),
    0px 3px 14px 2px rgb(0 0 0 / 12%);
`;

const SmallerIconButton = styled(IconButton)`
  width: 24px;
  height: 24px;
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

const NO_MULTI_SELECTION_MSG = "No recording uploads or analyses selected.";
const LIMIT_REACHED_MSG = "Disabled because analysis limit has been reached.";

const getInfoOfSelections = (selectionInfo) => {
  const selectedUploadsInfo = [];
  const selectedJobsInfo = [];
  Object.values(selectionInfo).map((uploadDetails) => {
    if (uploadDetails.selected) {
      selectedUploadsInfo.push(uploadDetails.info);
    }
    Object.values(uploadDetails.jobs).map((jobDetails) => {
      if (jobDetails.selected) {
        selectedJobsInfo.push(jobDetails.info);
      }
    });
  });
  return { selectedUploadsInfo, selectedJobsInfo };
};

const getSortFilterName = (sortColId) => {
  if (sortColId === "username") {
    return "username";
  } else if (sortColId === "name") {
    return "filename";
  } else if (sortColId === "id") {
    return "id";
  } else if (sortColId === "createdAt") {
    return "created_at";
  } else if (sortColId === "autoUpload") {
    return "auto_upload";
  } else {
    return "last_analyzed";
  }
};

export default function Uploads() {
  const router = useRouter();
  const { accountType, usageQuota, accountScope, productPage, accountId } = useContext(AuthContext);
  const { uploads, setUploads, setDefaultUploadForReanalysis, jobs, setJobs, getUploadsAndJobs } = useContext(
    UploadsContext
  );

  const [displayRows, setDisplayRows] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [selectionInfo, setSelectionInfo] = useState({
    /* Tanner (9/13/24): keeping the structure of this object here for future reference. Can be removed if necessary
    uploadId: {
      info: { ... },
      selected: true/false,
      jobs: {
        jobId: {
          info: { ... },
          selected: true/false
        }
        ...
      }
    }
    ...
    */
  });
  const [resetDropdown, setResetDropdown] = useState(false);
  const [modalState, setModalState] = useState(false);
  const [modalLabels, setModalLabels] = useState({ header: "", messages: [] });
  const [modalButtons, setModalButtons] = useState([]);
  const [openInteractiveAnalysis, setOpenInteractiveAnalysis] = useState(false);
  const [openJobPreview, setOpenJobPreview] = useState(false);
  const [selectedAnalysis, setSelectedAnalysis] = useState();
  const [jobsInSelectedUpload, setJobsInSelectedUpload] = useState(0);
  const [tableState, setTableState] = useState({
    sorting: [{ id: "lastAnalyzed", desc: true }],
    columnFilters: [],
  });

  // TODO consider moving this into a function and calling both of those functions only from the update fns.
  // Will also need to put these values in useState
  const uploadSelectionState = {};
  const jobSelectionState = {};
  for (const [uploadId, uploadDetails] of Object.entries(selectionInfo)) {
    if (uploadDetails.selected) {
      uploadSelectionState[uploadId] = true;
    }
    for (const [jobId, jobDetails] of Object.entries(uploadDetails.jobs)) {
      if (jobDetails.selected) {
        jobSelectionState[jobId] = true;
      }
    }
  }

  const dropdownDisabledTooltips = (() => {
    const { selectedUploadsInfo, selectedJobsInfo } = getInfoOfSelections(selectionInfo);
    const selectedUploadCount = selectedUploadsInfo.length;
    const selectedJobCount = selectedJobsInfo.length;

    let downloadTooltip = "";
    if (selectedUploadCount === 0 && selectedJobCount === 0) {
      downloadTooltip = NO_MULTI_SELECTION_MSG;
    }

    let deleteTooltip = "";
    if (selectedUploadCount === 0 && selectedJobCount === 0) {
      deleteTooltip = NO_MULTI_SELECTION_MSG;
    } else if (
      selectedUploadsInfo.some((u) => accountId !== u.user_id.replace(/-/g, "")) ||
      selectedJobsInfo.some((j) => !j.owner)
    ) {
      deleteTooltip = "Selection includes items owned by another user.";
    } else if (selectedJobsInfo.some((j) => ["pending", "running"].includes(j.status))) {
      deleteTooltip = "Selection includes analyses that are still pending or running.";
    }

    let iaTooltip = "";
    if (usageQuota?.jobs_reached) {
      iaTooltip = LIMIT_REACHED_MSG;
    } else if (selectedJobCount !== 1) {
      iaTooltip = "Must select exactly one analysis.";
    } else if (selectedJobsInfo[0].status !== "finished") {
      iaTooltip = "Selected analysis must have completed successfully.";
    }

    let reanalyzeTooltip = "";
    if (usageQuota?.jobs_reached) {
      reanalyzeTooltip = LIMIT_REACHED_MSG;
    } else if (selectedUploadCount === 0) {
      reanalyzeTooltip = "No recording uploads selected.";
    }

    return [downloadTooltip, deleteTooltip, iaTooltip, reanalyzeTooltip];
  })();

  const dropdownsubOptionDisabledTooltips = (() => {
    const { selectedUploadsInfo, selectedJobsInfo } = getInfoOfSelections(selectionInfo);
    const selectedUploadCount = selectedUploadsInfo.length;
    const selectedJobCount = selectedJobsInfo.length;

    let downloadUploadsTooltip = "";
    if (selectedUploadCount === 0) {
      downloadUploadsTooltip = "No recording uploads selected.";
    }

    let downloadAnalysesTooltip = "";
    if (selectedJobCount === 0) {
      downloadAnalysesTooltip = "No analyses selected.";
    } else if (selectedJobsInfo.some((j) => j.status !== "finished")) {
      downloadAnalysesTooltip = "Selection includes analyses that have not completed successfully.";
    }

    return { Download: [downloadAnalysesTooltip, downloadUploadsTooltip] };
  })();

  useEffect(() => {
    // reset to false everytime it gets triggered
    if (resetDropdown) {
      setResetDropdown(false);
    }
  }, [resetDropdown]);

  useEffect(() => {
    if (!openInteractiveAnalysis) {
      // reset when interactive analysis modal closes
      resetTable();
    }
  }, [openInteractiveAnalysis]);

  useEffect(() => {
    if (uploads) {
      const formattedUploads = uploads.map(({ username, id, filename, created_at, auto_upload, user_id }) => {
        const recName = filename ? filename.split(".").slice(0, -1).join(".") : null;
        const uploadJobs = jobs
          .filter(({ uploadId }) => uploadId === id)
          .sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt));

        const lastAnalyzed = uploadJobs[0] ? uploadJobs[0].createdAt : created_at;

        const owner = accountId === user_id.replace(/-/g, "");

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
  }, [uploads, jobs]);

  useEffect(() => {
    if (!uploads) {
      return;
    }
    let sortField, sortDirection;
    if (tableState.sorting.length > 0) {
      const sortInfo = tableState.sorting[0];
      sortField = getSortFilterName(sortInfo.id);
      sortDirection = sortInfo.desc ? "DESC" : "ASC";
    }
    const filters = {};
    for (const filt of tableState.columnFilters) {
      const filterName = getSortFilterName(filt.id);
      const filterValue = filt.value;
      // assuming that an array indicates the filter type is a datetime
      if (filterValue instanceof Array) {
        const formatDate = (date, max = false) => {
          if (!date?.toISOString) {
            return null;
          }
          try {
            date = new Date(date);
            if (max) {
              date.setDate(date.getDate() + 1);
              date.setMilliseconds(date.getMilliseconds() - 1);
            }
            return date.toISOString();
          } catch {
            return null;
          }
        };

        const min = filterValue[0];
        const formattedMin = formatDate(min);
        if (formattedMin) {
          filters[filterName + "_min"] = formattedMin;
        }
        const max = filterValue[1];
        const formattedMax = formatDate(max, true);
        if (formattedMax) {
          filters[filterName + "_max"] = formattedMax;
        }
      } else {
        filters[filterName] = filt.value;
      }
    }
    getUploadsAndJobs(productPage, filters, sortField, sortDirection);
  }, [tableState]);

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
        size: 190,
        minSize: 130,
        Cell: ({ cell }) => getShortUUIDWithTooltip(cell.getValue()),
      },
      {
        accessorFn: (row) => new Date(row.createdAt),
        header: "Date Created",
        id: "createdAt",
        filterVariant: "date-range",
        sortingFn: "datetime",
        size: 340,
        minSize: 275,
        muiFilterDatePickerProps: {
          slots: { clearButton: SmallerIconButton, openPickerButton: SmallerIconButton },
        },
        Cell: ({ cell }) => formatDateTime(cell.getValue()),
      },
      {
        accessorFn: (row) => new Date(row.lastAnalyzed),
        header: "Last Analyzed",
        id: "lastAnalyzed",
        filterVariant: "date-range",
        sortingFn: "datetime",
        size: 340,
        minSize: 275,
        muiFilterDatePickerProps: {
          slots: { clearButton: SmallerIconButton, openPickerButton: SmallerIconButton },
        },
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
          cell.getValue() !== null && <div>{cell.getValue() ? "Auto Upload" : "Manual Upload"}</div>,
      },
    ],
    []
  );

  const updateUploadSelectionInfo = (newUploadSelection) => {
    try {
      const newSelectionInfo = { ...selectionInfo };

      const newUploadSelectionSet = new Set(Object.keys(newUploadSelection));
      const uploadSelectionStateSet = new Set(Object.keys(uploadSelectionState));

      const uploadsAdded = newUploadSelectionSet.difference(uploadSelectionStateSet);
      for (const uploadIdAdded of uploadsAdded) {
        if (!(uploadIdAdded in newSelectionInfo)) {
          const uploadInfo = uploads.find((u) => u.id === uploadIdAdded);
          if (!uploadInfo) {
            continue;
          }
          newSelectionInfo[uploadIdAdded] = {
            info: deepCopy(uploadInfo),
          };
        }
        newSelectionInfo[uploadIdAdded].selected = true;
        const jobSelectionInfo = {};
        jobs.map((j) => {
          if (j.uploadId === uploadIdAdded) {
            jobSelectionInfo[j.jobId] = {
              info: deepCopy(j),
              selected: true,
            };
          }
        });
        newSelectionInfo[uploadIdAdded].jobs = jobSelectionInfo;
      }

      const uploadsRemoved = uploadSelectionStateSet.difference(newUploadSelectionSet);
      for (const uploadIdRemoved of uploadsRemoved) {
        delete newSelectionInfo[uploadIdRemoved];
      }

      setSelectionInfo(newSelectionInfo);
    } catch (e) {
      console.log("ERROR updating upload selection:", e);
    }
  };

  const updateJobSelectionInfo = (newJobSelection) => {
    try {
      const newSelectionInfo = { ...selectionInfo };

      const newJobSelectionSet = new Set(Object.keys(newJobSelection));
      const jobSelectionStateSet = new Set(Object.keys(jobSelectionState));

      const jobsAdded = newJobSelectionSet.difference(jobSelectionStateSet);
      for (const jobIdAdded of jobsAdded) {
        const jobInfo = jobs.find((j) => j.jobId === jobIdAdded);
        if (!jobInfo) {
          continue;
        }
        const uploadSelectionInfo = newSelectionInfo[jobInfo.uploadId];
        if (uploadSelectionInfo) {
          const jobSelectionInfo = uploadSelectionInfo.jobs[jobIdAdded];
          if (!jobSelectionInfo) {
            continue;
          }
          jobSelectionInfo.selected = true;
          uploadSelectionInfo.selected = Object.values(uploadSelectionInfo.jobs).every((j) => j.selected);
        } else {
          const uploadInfo = uploads.find((u) => u.id === jobInfo.uploadId);
          if (!uploadInfo) {
            continue;
          }
          const jobSelectionInfo = {};
          jobs.map((j) => {
            if (j.uploadId === jobInfo.uploadId) {
              jobSelectionInfo[j.jobId] = {
                info: deepCopy(j),
                selected: j.jobId === jobIdAdded,
              };
            }
          });
          newSelectionInfo[jobInfo.uploadId] = {
            info: deepCopy(uploadInfo),
            selected: Object.keys(jobSelectionInfo).length === 1,
            jobs: jobSelectionInfo,
          };
        }
      }

      const jobsRemoved = jobSelectionStateSet.difference(newJobSelectionSet);
      for (const jobIdRemoved of jobsRemoved) {
        const jobInfo = jobs.find((j) => j.jobId === jobIdRemoved);
        if (!jobInfo) {
          continue;
        }
        const uploadSelectionInfo = newSelectionInfo[jobInfo.uploadId];
        if (!uploadSelectionInfo) {
          continue;
        }
        const jobSelectionInfo = uploadSelectionInfo.jobs[jobIdRemoved];
        if (!jobSelectionInfo) {
          continue;
        }
        jobSelectionInfo.selected = false;

        uploadSelectionInfo.selected = false;
        if (Object.values(uploadSelectionInfo.jobs).every((j) => !j.selected)) {
          delete newSelectionInfo[jobInfo.uploadId];
        }
      }

      setSelectionInfo(newSelectionInfo);
    } catch (e) {
      console.log("ERROR updating job selection:", e);
    }
  };

  const updateTableState = (newState) => {
    setTableState({ ...tableState, ...newState });
  };

  const resetTable = async () => {
    setResetDropdown(true);
    setSelectionInfo({});
  };

  const handleDeletions = async () => {
    const { selectedUploadsInfo, selectedJobsInfo } = getInfoOfSelections(selectionInfo);

    try {
      let failedDeletingUploads = false;
      //soft delete uploads
      if (selectedUploadsInfo.length > 0) {
        const uploadIdsToDelete = selectedUploadsInfo.map(({ id }) => id);

        const uploadsURL = `${process.env.NEXT_PUBLIC_PULSE3D_URL}/uploads?`;
        uploadIdsToDelete.map((id) => (uploadsURL += `upload_ids=${id}&`));
        const uploadsResponse = await fetch(uploadsURL.slice(0, -1), {
          method: "DELETE",
        });
        failedDeletingUploads = uploadsResponse.status !== 200;

        if (!failedDeletingUploads) {
          // remove uploads from list to show auto deletion, waiting for get uploads request is too slow
          // will self-correct if anything is different when actual get uploads request renders
          const filteredUploads = uploads.filter(({ id }) => !uploadIdsToDelete.includes(id));
          setUploads([...filteredUploads]);
        }
      }

      let failedDeletingJobs = false;
      // only proceed if no issues deleting uploads
      if (!failedDeletingUploads && selectedJobsInfo.length > 0) {
        // soft delete all jobs
        const jobIdsToDelete = selectedJobsInfo.map(({ jobId }) => jobId);

        const jobsURL = `${process.env.NEXT_PUBLIC_PULSE3D_URL}/jobs?`;
        jobIdsToDelete.map(({ jobId }) => (jobsURL += `job_ids=${jobId}&`));

        const jobsResponse = await fetch(jobsURL.slice(0, -1), {
          method: "DELETE",
        });

        failedDeletingJobs = jobsResponse.status !== 200;

        if (failedDeletingJobs) {
          setModalButtons(["Close"]);
          setModalLabels(modalObjs.failedDeletion);
          setModalState("generic");
        } else {
          const filteredJobs = jobs.filter(({ jobId }) => !jobIdsToDelete.includes(jobId));
          setJobs([...filteredJobs]);
        }
      }

      return failedDeletingUploads || failedDeletingJobs;
    } catch (e) {
      console.log("ERROR attempting to soft delete selected jobs and uploads:", e);
      return true;
    }
  };

  const handleModalClose = async (idx) => {
    let failed = false;
    // TODO there is probably a better way to handle this since different actions could use the same words
    if (modalButtons[idx] === "Continue") {
      // set in progress
      setModalLabels(modalObjs.empty);
      setModalState("deleting");

      failed = await handleDeletions();
      // TODO there is probably a better way to do whatever this sleep is trying to do
      // wait a second to remove deleted files
      // really helps with flow of when in progress modal closes
      await new Promise((r) => setTimeout(r, 1000));
    }
    if (!failed) {
      setModalState(false);
      resetTable();
    }
  };

  const downloadAnalyses = async () => {
    try {
      const { selectedJobsInfo } = getInfoOfSelections(selectionInfo);
      // remove any jobs that aren't finished just to be safe
      const finishedJobs = selectedJobsInfo.filter(({ status }) => status === "finished");
      const numberOfJobs = finishedJobs.length;

      setModalButtons(["Close"]);

      // Download correct number of files, else throw error to prompt error modal
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
      console.log(`ERROR downloading analyses: ${e}`);
      setModalLabels(modalObjs.downloadError);
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
        const url = `${process.env.NEXT_PUBLIC_PULSE3D_URL}/jobs/download`;
        response = await fetch(url, {
          method: "POST",
          body: JSON.stringify({
            job_ids: [jobId],
            upload_type: productPage,
            timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
          }),
        });

        if (response.status === 200) {
          const job = await response.json();
          presignedUrl = job.url;
          name = job.id;
        }
      } else {
        const url = `${process.env.NEXT_PUBLIC_PULSE3D_URL}/uploads/download`;
        response = await fetch(url, {
          method: "POST",
          body: JSON.stringify({ upload_ids: [uploadId], upload_type: productPage }),
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
        a.setAttribute("download", "download");
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
      let url, downloadType, body;
      if (uploads) {
        url = `${process.env.NEXT_PUBLIC_PULSE3D_URL}/uploads/download`;
        downloadType = "recordings";
        body = { upload_ids: data, upload_type: productPage };
      } else {
        const jobIds = data.map(({ jobId }) => jobId);
        url = `${process.env.NEXT_PUBLIC_PULSE3D_URL}/jobs/download`;
        downloadType = "analyses";
        body = {
          job_ids: jobIds,
          upload_type: productPage,
          timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
        };
      }
      let zipFilename = `${downloadType}__${formatDateTime()}__${data.length}.zip`;
      if (productPage) {
        zipFilename = `${productPage}-${zipFilename}`;
      }

      const response = await fetch(url, {
        method: "POST",
        body: JSON.stringify(body),
      });

      if (response.status === 200) {
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

  const actionsFn = (t) => {
    const dropdownOptions =
      accountType === "admin" ? ["Download"] : ["Download", "Delete", "Interactive Analysis", "Re-Analyze"];

    const handleDropdownSelection = (optionIdx) => {
      try {
        if (dropdownOptions[optionIdx] === "Delete") {
          setModalButtons(["Close", "Confirm"]);
          setModalLabels(modalObjs.delete);
          setModalState("generic");
        } else if (dropdownOptions[optionIdx] === "Interactive Analysis") {
          const { selectedJobsInfo } = getInfoOfSelections(selectionInfo);
          const selectedJobInfo = selectedJobsInfo[0];
          setSelectedAnalysis(selectedJobInfo);
          const uploadInfo = selectionInfo[selectedJobInfo.uploadId];
          setJobsInSelectedUpload(Object.values(uploadInfo.jobs).length); // used to show credit usage if necessary
          setOpenInteractiveAnalysis(true);
        } else if (dropdownOptions[optionIdx] === "Re-Analyze") {
          // Open Re-analyze tab with name of the selected files
          const { selectedUploadsInfo } = getInfoOfSelections(selectionInfo);
          setDefaultUploadForReanalysis(selectedUploadsInfo);
          router.push("/upload-form?id=re-analyze+existing+upload");
        } else {
          return;
        }

        resetTable();
      } catch (e) {
        console.log(`ERROR handling drop down selection (${dropdownOptions[optionIdx]}):`, e);
      }
    };

    const handleDownloadSubSelection = async ({ optionName, subOptionIdx }) => {
      if (optionName === "Download") {
        if (subOptionIdx === 0 /* Analyses */) {
          downloadAnalyses();
        } else if (subOptionIdx === 1 /* Recordings */) {
          try {
            const { selectedUploadInfo } = getInfoOfSelections(selectionInfo);
            const uploadIds = selectedUploadInfo.map(({ id }) => id);
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
                  `The following number of recording files have been successfully downloaded: ${uploadIds.length}`,
                  "They can be found in your local downloads folder.",
                ],
              });
              setModalButtons(["Close"]);
              setModalState("generic");
            }
          } catch (e) {
            console.log(`ERROR downloading recording files: ${e}`);
            setModalLabels(modalObjs.downloadError);
            setModalButtons(["Close"]);
            setModalState("generic");
          }
        }
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
            disableOptions={dropdownDisabledTooltips.map((msg) => msg !== "")}
            optionsTooltipText={dropdownDisabledTooltips}
            handleSelection={handleDropdownSelection}
            handleSubSelection={handleDownloadSubSelection}
            reset={resetDropdown}
            disableSubOptions={{
              Download: dropdownsubOptionDisabledTooltips.Download.map((msg) => msg !== ""),
            }}
            subOptionsTooltipText={dropdownsubOptionDisabledTooltips}
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
            rowSelection={uploadSelectionState}
            setRowSelection={(newUploadSelectionFn) =>
              updateUploadSelectionInfo(newUploadSelectionFn(uploadSelectionState))
            }
            toolbarFn={actionsFn}
            columnVisibility={{
              username: accountType !== "user" || accountScope.includes(`${productPage}:rw_all_data`),
            }}
            subTableFn={(row) => (
              <Jobs
                uploadRow={row}
                openJobPreview={handleJobPreviewClick}
                setSelectedJobs={(newJobSelectionFn) =>
                  updateJobSelectionInfo(newJobSelectionFn(jobSelectionState))
                }
                selectedJobs={jobSelectionState}
              />
            )}
            enableExpanding={true}
            isLoading={isLoading}
            manualSorting={true}
            onSortingChange={(newSorting) => {
              if (isLoading) {
                return;
              }
              const sorting = newSorting();
              // Tanner (5/28/24): have to do this manually since the MRT component doesn't seem to handle this correctly
              if (sorting[0].id === tableState.sorting[0]?.id) {
                sorting[0].desc = !tableState.sorting[0].desc;
              }
              updateTableState({ sorting });
            }}
            manualFiltering={true}
            onColumnFiltersChange={(updateFn) => {
              if (isLoading) {
                return;
              }
              let { columnFilters } = tableState;
              columnFilters = updateFn(columnFilters);
              updateTableState({ columnFilters });
            }}
            state={tableState}
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
