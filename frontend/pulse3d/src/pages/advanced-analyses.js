import DashboardLayout from "@/components/layouts/DashboardLayout";
import styled from "styled-components";
import Table from "@/components/table/Table";
import { Box, IconButton } from "@mui/material";
import { useContext, useState, useEffect, useMemo } from "react";
import { AdvancedAnalysisContext } from "./_app";
import { formatDateTime } from "@/utils/generic";
import { getShortUUIDWithTooltip } from "@/utils/jsx";
import DropDownWidget from "@/components/basicWidgets/DropDownWidget";

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

const downloadJobs = async (jobIds) => {
  try {
    if (jobIds.length === 0) {
      return;
    }

    const url = `${process.env.NEXT_PUBLIC_ADVANCED_ANALYSIS_URL}/advanced-analyses/download`;
    const res = await fetch(url, {
      method: "POST",
      body: JSON.stringify({
        job_ids: jobIds,
        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
      }),
    });
    if (res?.status !== 200) {
      throw Error(`response status: ${res.status}`);
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
  }
};

export default function AdvancedAnalyses() {
  const { advancedAnalysisJobs, getAdvancedAnalysisJobs } = useContext(AdvancedAnalysisContext);

  const [isLoading, setIsLoading] = useState(true);
  const [displayRows, setDisplayRows] = useState([]);
  const [checkedRows, setCheckedRows] = useState({});
  const [tableState, setTableState] = useState({
    sorting: [{ id: "createdAt", desc: true }],
    columnFilters: [],
  });

  const checkedJobIds = Object.keys(checkedRows);

  useEffect(() => {
    if (advancedAnalysisJobs) {
      const formattedJobs = advancedAnalysisJobs.map(
        ({ id, name: filename, type: jobType, sources, created_at: createdAt, meta, status }) => {
          filename = filename || meta?.output_name || "None";
          return {
            id,
            filename,
            jobType,
            createdAt,
            sources,
            meta,
            status,
          };
        }
      );

      setDisplayRows([...formattedJobs]);
      setIsLoading(false);
    }
  }, [advancedAnalysisJobs]);

  const updateTableState = (newState) => {
    setTableState({ ...tableState, ...newState });
  };

  const columns = useMemo(
    () => [
      {
        accessorKey: "filename",
        id: "filename",
        header: "Analysis Name",
        filterVariant: "autocomplete",
        size: 200,
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
        size: 150,
        minSize: 150,
        // TODO figure out how to show metadata: Should it be in a dropdown? Should it be split into multiple cols?
        Cell: ({ cell }) => getShortUUIDWithTooltip(JSON.stringify(cell.getValue())),
      },
      {
        accessorKey: "sources",
        id: "sources",
        header: "Input IDs",
        filterVariant: "autocomplete",
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
        size: 200,
        Cell: ({ cell }) => <StatusText>{cell.getValue()}</StatusText>,
      },
    ],
    []
  );

  const handleActionSelection = async (optionIdx) => {
    try {
      if (optionIdx === 0 /* Download */) {
        await downloadJobs(checkedJobIds);
      } else if (optionIdx === 1 /* Delete */) {
        // TODO
      }
    } catch {
      return;
    }
    setCheckedRows({});
  };

  const actionsFn = (t) => {
    const checkedJobs = t.getSelectedRowModel().rows.map((row) => row.original);
    return (
      <Box sx={{ width: "100%", position: "relative", display: "flex", justifyContent: "end" }}>
        <DropDownContainer>
          <DropDownWidget
            label="Actions"
            options={["Download", "Delete"]}
            disableOptions={[
              checkedJobIds.length === 0 || checkedJobs.some((j) => j.status !== "finished"),
              true,
            ]}
            optionsTooltipText={["Must make a selection of only completed jobs.", "Coming soon."]}
            handleSelection={handleActionSelection}
            reset={checkedJobIds.length === 0}
          />
        </DropDownContainer>
      </Box>
    );
  };

  return (
    <TableContainer>
      <Table
        columns={columns}
        rowData={displayRows}
        rowSelection={checkedRows}
        setRowSelection={setCheckedRows}
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
          // TODO clear selection?
          let { columnFilters } = tableState;
          columnFilters = updateFn(columnFilters);
          updateTableState({ columnFilters });
        }}
        state={tableState}
      />
    </TableContainer>
  );
}

AdvancedAnalyses.getLayout = (page) => {
  return <DashboardLayout>{page}</DashboardLayout>;
};
