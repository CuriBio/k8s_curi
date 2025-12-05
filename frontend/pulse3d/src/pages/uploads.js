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
import { deepCopy, formatDateTime, removeFileExt } from "@/utils/generic";
import { getShortUUIDWithTooltip, NoMaxWidthTooltip } from "@/utils/jsx";
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

const TooltipText = styled.span`
  font-size: 15px;
`;

const modalObjs = {
  delete: {
    header: "Are you sure?",
    messages: ["Please confirm the deletion.", "Be aware that this action cannot be undone."],
  },
  downloadError: {
    header: "Error Occurred!",
    messages: ["An error occurred while attempting to download.", "Please try again later."],
  },
  empty: {
    header: null,
    messages: [],
  },
  failedDeletion: {
    header: "Error Occurred!",
    messages: ["There was an issue while deleting the files you selected.", "Please try again later."],
  },
};

const NO_SELECTION_MSG = "No recording uploads or analyses selected.";
const LIMIT_REACHED_MSG = "Disabled because analysis limit has been reached.";

const METADATA_KEYS_TO_DISPLAY = [
  "data_type",
  "file_format_version",
  "full_recording_length",
  "software_release_version",
  "total_well_count",
  "utc_beginning_recording",
];

const MA_METADATA_KEYS_TO_DISPLAY = [
  ...METADATA_KEYS_TO_DISPLAY,
  "channel_firmware_version",
  "computer_name_hash",
  "main_firmware_version",
  "instrument_serial_number",
  "platemap_name",
  "platemap_labels",
  "plate_barcode",
  "plate_barcode_entry_time",
  "plate_barcode_is_from_scanner",
  "post_stiffness_label",
  "stim_barcode",
  "stim_barcode_entry_time",
  "stim_barcode_is_from_scanner",
  "user_defined_metadata",
  "utc_beginning_calibration",
];

const NA_METADATA_KEYS_TO_DISPLAY = [...METADATA_KEYS_TO_DISPLAY, "tissue_sampling_period"];

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
  const { uploads, setDefaultUploadForReanalysis, jobs, getUploadsAndJobs } = useContext(UploadsContext);

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

    let downloadTooltip = { msg: "", disable: false };
    if (selectedUploadCount === 0 && selectedJobCount === 0) {
      downloadTooltip = { msg: NO_SELECTION_MSG, disable: true };
    }

    let deleteTooltip = { msg: "", disable: false };
    if (selectedUploadCount === 0 && selectedJobCount === 0) {
      deleteTooltip = { msg: NO_SELECTION_MSG, disable: true };
    } else if (
      selectedUploadsInfo.some((u) => accountId !== u.user_id.replace(/-/g, "")) ||
      selectedJobsInfo.some((j) => !j.owner)
    ) {
      deleteTooltip = { msg: "Selection includes items owned by another user.", disable: true };
    } else if (selectedJobsInfo.some((j) => ["pending", "running"].includes(j.status))) {
      deleteTooltip = {
        msg: "Selection includes analyses that are still pending or running.",
        disable: true,
      };
    }

    let iaTooltip = { msg: "", disable: false };
    if (usageQuota?.jobs_reached) {
      iaTooltip = { msg: LIMIT_REACHED_MSG, disable: true };
    } else if (selectedJobCount !== 1) {
      iaTooltip = { msg: "Must select exactly one analysis.", disable: true };
    } else if (selectedJobsInfo[0].status !== "finished") {
      iaTooltip = { msg: "Selected analysis must have completed successfully.", disable: true };
    }

    let reanalyzeTooltip = { msg: "", disable: false };
    if (usageQuota?.jobs_reached) {
      reanalyzeTooltip = { msg: LIMIT_REACHED_MSG, disable: true };
    } else if (selectedUploadCount === 0) {
      reanalyzeTooltip = { msg: "No recording uploads selected.", disable: true };
    }

    return [downloadTooltip, deleteTooltip, iaTooltip, reanalyzeTooltip];
  })();

  const dropdownsubOptionDisabledTooltips = (() => {
    const { selectedUploadsInfo, selectedJobsInfo } = getInfoOfSelections(selectionInfo);
    const selectedUploadCount = selectedUploadsInfo.length;
    const successfullyCompletedJobCount = selectedJobsInfo.filter((j) => j.status === "finished").length;

    let downloadUploadsTooltip = { msg: "", disable: false };
    if (selectedUploadCount === 0) {
      downloadUploadsTooltip = { msg: "No recording uploads selected.", disable: true };
    }

    let downloadAnalysesTooltip = { msg: "", disable: false };
    if (successfullyCompletedJobCount === 0) {
      downloadAnalysesTooltip = {
        msg: "No analyses selected that have successfully completed.",
        disable: true,
      };
    } else if (selectedJobsInfo.some((j) => j.status !== "finished")) {
      downloadAnalysesTooltip = {
        msg:
          "Selection includes analyses that have not completed successfully which will be omitted from the download.",
        disable: false,
      };
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
      const formattedUploads = uploads.map(
        ({ username, id, filename, created_at, auto_upload, user_id, meta }) => {
          const recName = removeFileExt(filename) || null;
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
            meta,
          };
        }
      );

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
        enableColumnActions: false,
        size: 200,
        minSize: 130,
      },
      {
        accessorKey: "name",
        id: "name",
        header: "Recording Name",
        filterVariant: "autocomplete",
        enableColumnActions: false,
        size: 320,
        minSize: 130,
      },
      {
        accessorKey: "id", //accessorKey used to define `data` column. `id` gets set to accessorKey automatically
        filterVariant: "autocomplete",
        id: "id",
        header: "Upload ID",
        enableColumnActions: false,
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
        enableColumnActions: false,
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
        enableColumnActions: false,
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
        enableColumnActions: false,
        size: 180,
        Cell: ({ cell }) =>
          cell.getValue() !== null && <div>{cell.getValue() ? "Auto Upload" : "Manual Upload"}</div>,
      },
      {
        accessorKey: "meta",
        header: "Metadata",
        id: "metadata",
        enableColumnActions: false,
        enableColumnFilter: false,
        enableResizing: false,
        enableSorting: false,
        size: 120,
        minSize: 40,
        Cell: ({ cell }) => {
          const meta = cell.getValue();
          if (meta == null) {
            return "";
          } else {
            let parsedMeta;
            try {
              parsedMeta = JSON.parse(meta);
            } catch {
              return "";
            }
            if (Object.keys(parsedMeta).length === 0) {
              return "";
            }

            const metadata_keys_to_display =
              productPage === "nautilai" ? NA_METADATA_KEYS_TO_DISPLAY : MA_METADATA_KEYS_TO_DISPLAY;

            const title = (
              <TooltipText>
                <ul>
                  {Object.keys(parsedMeta)
                    .filter((k) => metadata_keys_to_display.includes(k))
                    .sort()
                    .map((k) => {
                      return (
                        <li key={k}>
                          {k}: {JSON.stringify(parsedMeta[k])}
                        </li>
                      );
                    })}
                </ul>
              </TooltipText>
            );
            return <NoMaxWidthTooltip title={title}>View</NoMaxWidthTooltip>;
          }
        },
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
      }

      let failedDeletingJobs = false;
      // only proceed if no issues deleting uploads
      if (!failedDeletingUploads && selectedJobsInfo.length > 0) {
        // soft delete all jobs
        const jobIdsToDelete = selectedJobsInfo.map(({ jobId }) => jobId);

        const jobsURL = `${process.env.NEXT_PUBLIC_PULSE3D_URL}/jobs?`;
        jobIdsToDelete.map((jobId) => (jobsURL += `job_ids=${jobId}&`));

        const jobsResponse = await fetch(jobsURL.slice(0, -1), {
          method: "DELETE",
        });

        failedDeletingJobs = jobsResponse.status !== 200;
      }

      const failed = failedDeletingUploads || failedDeletingJobs;

      if (failed) {
        setModalButtons(["Close"]);
        setModalLabels(modalObjs.failedDeletion);
        setModalState("generic");
      }

      return failed;
    } catch (e) {
      console.log("ERROR attempting to soft delete selected jobs and uploads:", e);
      return true;
    }
  };

  const handleModalClose = async (idx) => {
    let failed = false;
    // TODO there is probably a better way to handle this since different actions could use the same words
    if (modalButtons[idx] === "Confirm") {
      // set in progress
      setModalLabels(modalObjs.empty);
      setModalState("deleting");

      failed = await handleDeletions();
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
      console.log("ERROR downloading analyses:", e);
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
      console.log("ERROR during multi file download:", e);
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
          setModalButtons(["Cancel", "Confirm"]);
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
        }
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
            const { selectedUploadsInfo } = getInfoOfSelections(selectionInfo);
            const uploadIds = selectedUploadsInfo.map(({ id }) => id);
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
            console.log("ERROR downloading recording files:", e);
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
            disableOptions={dropdownDisabledTooltips.map(({ disable }) => disable)}
            optionsTooltipText={dropdownDisabledTooltips.map(({ msg }) => msg)}
            handleSelection={handleDropdownSelection}
            handleSubSelection={handleDownloadSubSelection}
            reset={resetDropdown}
            disableSubOptions={{
              Download: dropdownsubOptionDisabledTooltips.Download.map(({ disable }) => disable),
            }}
            subOptionsTooltipText={(() => {
              const toolTips = {};
              Object.entries(dropdownsubOptionDisabledTooltips).map(([btnName, subOptions]) => {
                toolTips[btnName] = subOptions.map(({ msg }) => msg);
              });
              return toolTips;
            })()}
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
