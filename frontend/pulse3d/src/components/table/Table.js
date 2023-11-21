import DashboardLayout from "@/components/layouts/DashboardLayout";
import { MaterialReactTable, useMaterialReactTable } from "material-react-table";
//Date Picker Imports - these should just be in your Context Provider
import { AdapterDayjs } from "@mui/x-date-pickers/AdapterDayjs";
import { LocalizationProvider } from "@mui/x-date-pickers/LocalizationProvider";

export default function Table({
  columns = [],
  rowData = [],
  defaultSortColumn,
  rowSelection,
  setRowSelection,
  subTableFn = null,
  toolbarFn = null,
  enablePagination = true,
  enableTopToolbar = true,
  enableExpanding = false,
  enableSelectAll = true,
  enableStickyHeader = true,
  getRowId = (row) => row.id,
  isLoading = false,
  enableRowSelection = true,
  showColumnFilters = true,
  columnVisibility = {},
}) {
  const getHeaderSx = () => {
    return showColumnFilters
      ? {
          borderBottom: "1px solid var(--dark-gray)",
          background: "white",
          color: "black",
          padding: "1rem",
          "& .MuiSvgIcon-root": {
            paddingBottom: "3px",
            fontSize: 24,
          },
          "& .MuiTableSortLabel-icon": {
            paddingTop: "3px",
            fontSize: 24,
          },
          "& .MuiFormControl-root": {
            minWidth: "80px",
          },
        }
      : {
          borderBottom: "1px solid var(--dark-gray)",
          background: "var(--dark-blue)",
          color: "white",
          padding: "1rem",
          "& .MuiSvgIcon-root": {
            color: "white",
            paddingBottom: "3px",
            fontSize: 24,
          },
          "& .MuiTableSortLabel-icon": {
            fill: "white",
            paddingTop: "3px",
            fontSize: 24,
          },
          "& .MuiDivider-root": { borderColor: "white", borderWidth: "1px" },
        };
  };

  const table = useMaterialReactTable({
    columns,
    data: rowData,
    enableColumnFilterModes: false,
    enableColumnResizing: true,
    enableRowSelection,
    enableStickyHeader,
    enableTopToolbar,
    enablePagination,
    enableSelectAll,
    selectAllMode: "all",
    initialState: {
      showColumnFilters: showColumnFilters,
      sorting: [
        {
          id: defaultSortColumn,
          desc: true,
        },
      ],
    },
    muiTableProps: {
      sx: {
        cursor: "default",
      },
    },
    muiTablePaperProps: {
      sx: {
        background: "var(--dark-blue)",
        // don't set it at all if pagination because it will mess up for all box css components that have varying heights
        "& .MuiBox-root": !enablePagination && {
          minHeight: 0,
        },
      },
    },
    muiTableContainerProps: {
      sx: { background: "var(--med-gray)" },
    },
    paginationDisplayMode: "pages",
    muiFilterTextFieldProps: {
      size: "small",
      variant: "outlined",
      color: "secondary",
      inputProps: {
        sx: { fontSize: "12px" },
      },
    },
    muiTableHeadCellProps: {
      sx: getHeaderSx(),
    },
    muiTableBodyCellProps: {
      sx: { whiteSpace: "nowrap" },
    },
    muiPaginationProps: {
      color: "secondary",
      rowsPerPageOptions: [10, 30, 50, 100],
      variant: "outlined",
    },
    onRowSelectionChange: setRowSelection, // returns {[id]: true, [id2]: true, ...}
    renderDetailPanel: subTableFn ? ({ row }) => subTableFn(row) : null,
    renderTopToolbar: toolbarFn ? ({ table }) => toolbarFn(table) : null,
    state: { rowSelection, isLoading, density: "compact", columnVisibility }, // rowSelection can be {[id]: true, [id2]: false, [id3]: true, ... }
    enableExpanding,
    muiCircularProgressProps: { size: 100 },
    getRowId: getRowId,
  });

  return (
    <LocalizationProvider dateAdapter={AdapterDayjs}>
      <MaterialReactTable table={table} />
    </LocalizationProvider>
  );
}

Table.getLayout = (page) => {
  return <DashboardLayout>{page}</DashboardLayout>;
};
