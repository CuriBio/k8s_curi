import DashboardLayout from "@/components/layouts/DashboardLayout";
import styled from "styled-components";
import Table from "@/components/table/Table";
import { Box, IconButton } from "@mui/material";
import { useContext, useState, useEffect, useMemo } from "react";
import { AdvancedAnalysisContext } from "./_app";
import { formatDateTime } from "@/utils/generic";
import { getShortUUIDWithTooltip } from "@/utils/jsx";
import DropDownWidget from "@/components/basicWidgets/DropDownWidget";
import ModalWidget from "@/components/basicWidgets/ModalWidget";

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

const StatusText = styled.div`
  text-wrap: wrap;
`;

const DropDownContainer = styled.div`
  width: 250px;
  background-color: white;
  border-radius: 8px;
  position: relative;
  margin: 15px 20px;
`;

const downloadJobs = async (selectedJobs, onError) => {
  try {
    if (selectedJobs.length === 0) {
      return;
    }
    const jobIds = selectedJobs.map(({ id }) => id);

    const url = `${process.env.NEXT_PUBLIC_ADVANCED_ANALYSIS_URL}/advanced-analyses/download`;
    const res = await fetch(url, {
      method: "POST",
      body: JSON.stringify({
        job_ids: jobIds,
        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
      }),
    });
    if (res?.status !== 200) {
      throw Error(`response status: ${res?.status}`);
    }

    let downloadUrl, downloadName;
    if (jobIds.length === 1) {
      // will be downloading from a presigned URL in this case
      const downloadInfo = await res.json();
      downloadUrl = downloadInfo.url;
      downloadName = "download"; // name does not actually matter in this case, the filename will be whatever it is set to in S3
    } else {
      // will receive a stream of the zipped files in this case
      downloadName = `advanced_analyses__${formatDateTime()}__${jobIds.length}.zip`;
      const file = await res.blob();
      downloadUrl = window.URL.createObjectURL(file);
    }
    const a = document.createElement("a");
    document.body.appendChild(a);
    a.setAttribute("href", downloadUrl);
    a.setAttribute("download", downloadName);
    a.click();
    a.remove();
  } catch (e) {
    console.log("ERROR downloading jobs:", e);
    onError();
  }
};

const deleteJobs = async (selectedJobs, onError) => {
  try {
    if (selectedJobs.length === 0) {
      return;
    }
    const query = selectedJobs.map(({ id }) => `job_ids=${id}`).join("&");

    const url = `${process.env.NEXT_PUBLIC_ADVANCED_ANALYSIS_URL}/advanced-analyses?${query}`;
    const res = await fetch(url, {
      method: "DELETE",
    });
    if (res?.status !== 204) {
      throw Error(`response status: ${res?.status}`);
    }
  } catch (e) {
    console.log("ERROR deleting jobs:", e);
    onError();
  }
};

const getSortFilterName = (sortColId) => {
  if (sortColId === "filename") {
    return "name";
  } else if (sortColId === "createdAt") {
    return "created_at";
  } else {
    return sortColId;
  }
};

const MODAL_TYPES = {
  NONE: "none",
  DOWNLOAD_ERROR: "download_error",
  DELETE_PROMPT: "delete_prompt",
  DELETE_ERROR: "delete_error",
};

const getModalState = (modalType) => {
  const modalInfo = { type: modalType };
  if (modalType === MODAL_TYPES.DOWNLOAD_ERROR) {
    modalInfo.header = "Error Occurred!";
    modalInfo.labels = ["An error occurred while attempting to download.", "Please try again later."];
    modalInfo.buttons = ["Close"];
  } else if (modalType === MODAL_TYPES.DELETE_PROMPT) {
    modalInfo.header = "Are you sure?";
    modalInfo.labels = ["Please confirm the deletion.", "Be aware that this action cannot be undone."];
    modalInfo.buttons = ["Cancel", "Confirm"];
  } else if (modalType === MODAL_TYPES.DELETE_ERROR) {
    modalInfo.header = "Error Occurred!";
    modalInfo.labels = ["An error occurred while attempting to delete.", "Please try again later."];
    modalInfo.buttons = ["Close"];
  } else {
    modalInfo.type = MODAL_TYPES.NONE;
    modalInfo.header = "";
    modalInfo.labels = [];
    modalInfo.buttons = [];
  }
  return modalInfo;
};

export default function AdvancedAnalyses() {
  const { advancedAnalysisJobs, getAdvancedAnalysisJobs } = useContext(AdvancedAnalysisContext);

  const reGetAdvancedAnalysisJobs = (tableState) => {
    if (advancedAnalysisJobs == null) {
      return;
    }

    const { sorting, columnFilters } = tableState;

    // TODO consider pulling this into a function and sharing with uploads table
    let sortField, sortDirection;
    if (sorting.length > 0) {
      const sortInfo = sorting[0];
      sortField = getSortFilterName(sortInfo.id);
      sortDirection = sortInfo.desc ? "DESC" : "ASC";
    }

    const filters = {};
    for (const filt of columnFilters) {
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

    getAdvancedAnalysisJobs(filters, sortField, sortDirection);
  };

  const [isLoading, setIsLoading] = useState(true);
  const [displayRows, setDisplayRows] = useState([]);
  const [selectedJobs, setSelectedJobs] = useState([]);
  const [tableState, setTableState] = useState({
    sorting: [{ id: "createdAt", desc: true }],
    columnFilters: [],
  });
  const [modalState, setModalState] = useState(getModalState(MODAL_TYPES.NONE));

  const jobSelectionState = {};
  for (const job of selectedJobs) {
    jobSelectionState[job.id] = true;
  }

  useEffect(() => {
    if (advancedAnalysisJobs != null) {
      setDisplayRows([...advancedAnalysisJobs]);
      setIsLoading(false);
    }
  }, [advancedAnalysisJobs]);

  const columns = useMemo(
    () => [
      {
        accessorKey: "filename",
        id: "filename",
        header: "Analyzed Filename",
        filterVariant: "autocomplete",
        size: 240,
        minSize: 130,
      },
      {
        accessorKey: "id", //accessorKey used to define `data` column. `id` gets set to accessorKey automatically
        id: "id",
        header: "Analysis ID",
        filterVariant: "autocomplete",
        size: 190,
        minSize: 130,
        Cell: ({ cell }) => getShortUUIDWithTooltip(cell.getValue()),
      },
      {
        accessorFn: (row) => new Date(row.createdAt),
        id: "createdAt",
        header: "Date Created",
        filterVariant: "date-range",
        sortingFn: "datetime",
        size: 310,
        minSize: 200,
        muiFilterDatePickerProps: {
          slots: { clearButton: SmallerIconButton, openPickerButton: SmallerIconButton },
        },
        Cell: ({ cell }) => formatDateTime(cell.getValue()),
      },
      {
        accessorKey: "meta",
        id: "meta",
        header: "Metadata",
        enableColumnFilter: false,
        enableSorting: false,
        size: 150,
        minSize: 150,
        // TODO figure out how to show metadata: Should it be in a dropdown? Should it be split into multiple cols?
        Cell: ({ cell }) => getShortUUIDWithTooltip(JSON.stringify(cell.getValue())),
      },
      {
        accessorKey: "sources",
        id: "sources",
        header: "Input IDs",
        enableColumnFilter: false,
        enableSorting: false,
        size: 230,
        minSize: 130,
        Cell: ({ cell }) => (
          <ul>
            {cell.getValue().map((e) => (
              <li key={e}>{getShortUUIDWithTooltip(e)}</li>
            ))}
          </ul>
        ),
      },
      {
        accessorFn: (row) =>
          row.status == "finished" ? "Completed" : row.status[0].toUpperCase() + row.status.slice(1),
        id: "status",
        header: "Status",
        filterVariant: "autocomplete",
        size: 200,
        Cell: ({ cell }) => <StatusText>{cell.getValue()}</StatusText>,
      },
    ],
    []
  );

  const updateModalType = (modalType) => {
    setModalState(getModalState(modalType));
  };

  const updateTableState = (newState) => {
    const updatedState = { ...tableState, ...newState };
    setTableState(updatedState);
    reGetAdvancedAnalysisJobs(updatedState);
  };

  const updateSelectedJobs = (newJobSelectionState) => {
    // filter out jobs that are no longer selected
    const newSelectedJobs = selectedJobs.filter((j) => j.id in newJobSelectionState);
    // add jobs that are now selected
    Object.keys(newJobSelectionState).map((newJobId) => {
      if (newSelectedJobs.some((j) => j.id === newJobId)) {
        return;
      }
      const jobInfo = (advancedAnalysisJobs || []).find((j) => j.id === newJobId);
      if (!jobInfo) {
        return;
      }
      newSelectedJobs.push(jobInfo);
    });

    setSelectedJobs(newSelectedJobs);
  };

  const handleActionSelection = async (optionIdx) => {
    let clearSelection = true;
    try {
      if (optionIdx === 0 /* Download */) {
        await downloadJobs(selectedJobs, () => updateModalType(MODAL_TYPES.DOWNLOAD_ERROR));
      } else if (optionIdx === 1 /* Delete */) {
        clearSelection = false;
        updateModalType(MODAL_TYPES.DELETE_PROMPT);
      }
    } catch {}
    if (clearSelection) {
      setSelectedJobs([]);
    }
  };

  const actionsFn = (t) => {
    return (
      <Box sx={{ width: "100%", position: "relative", display: "flex", justifyContent: "end" }}>
        <DropDownContainer>
          <DropDownWidget
            label="Actions"
            options={["Download", "Delete"]}
            disableOptions={[
              selectedJobs.length === 0 || selectedJobs.some((j) => j.status !== "finished"),
              selectedJobs.length === 0 ||
                selectedJobs.some((j) => ["pending", "running"].includes(j.status)),
            ]}
            optionsTooltipText={[
              "Must make a selection of only successfully completed jobs.",
              "Must make a selection of only completed jobs.",
            ]}
            handleSelection={handleActionSelection}
            reset={selectedJobs.length === 0}
          />
        </DropDownContainer>
      </Box>
    );
  };

  const handleModalClose = async (idx) => {
    let nextModalType = MODAL_TYPES.NONE;

    if (modalState.type === MODAL_TYPES.DELETE_PROMPT) {
      if (modalState.buttons[idx] === "Confirm") {
        await deleteJobs(selectedJobs, () => {
          nextModalType = MODAL_TYPES.DELETE_ERROR;
        });
        setSelectedJobs([]);
      }
    }

    updateModalType(nextModalType);
  };

  return (
    <>
      <TableContainer>
        <Table
          columns={columns}
          rowData={displayRows}
          rowSelection={jobSelectionState}
          setRowSelection={(newJobSelectionFn) => {
            updateSelectedJobs(newJobSelectionFn(jobSelectionState));
          }}
          toolbarFn={actionsFn}
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
      <ModalWidget
        open={modalState.type !== MODAL_TYPES.NONE}
        header={modalState.header}
        labels={modalState.labels}
        buttons={modalState.buttons}
        closeModal={handleModalClose}
      >
        {/* TODO try just using one modal like this and conditionally showing the spinner once the spinner is required
          <ModalSpinnerContainer>
            <CircularSpinner size={200} color={"secondary"} />
          </ModalSpinnerContainer>
          */}
      </ModalWidget>
    </>
  );
}

AdvancedAnalyses.getLayout = (page) => {
  return <DashboardLayout>{page}</DashboardLayout>;
};
