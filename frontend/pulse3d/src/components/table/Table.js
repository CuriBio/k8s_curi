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
  const table = useMaterialReactTable({
    columns,
    data: rowData,
    enableColumnFilterModes: false,
    enableColumnResizing: true,
    enableRowSelection: enableRowSelection,
    enableStickyHeader: enableStickyHeader,
    enableTopToolbar: enableTopToolbar,
    enablePagination: enablePagination,
    enableSelectAll: enableSelectAll,
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
      sx: { cursor: "default" },
    },
    muiTablePaperProps: {
      sx: { background: "var(--dark-blue)" },
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
      sx: {
        borderBottom: "1px solid var(--dark-gray)",
        background: showColumnFilters ? "white" : "var(--dark-blue)",
        color: showColumnFilters ? "black" : "white",
      },
    },
    muiTableBodyCellProps: {
      sx: { whiteSpace: "nowrap" },
    },
    muiPaginationProps: {
      color: "secondary",
      rowsPerPageOptions: [10, 30, 50, 100],
      shape: "rounded",
      variant: "outlined",
    },
    onRowSelectionChange: setRowSelection, // returns {[id]: true, [id2]: true, ...}
    renderDetailPanel: subTableFn ? ({ row }) => subTableFn(row) : null,
    renderTopToolbar: toolbarFn ? ({ table }) => toolbarFn(table) : null,
    state: { rowSelection, isLoading, density: "compact", columnVisibility }, // rowSelection can be {[id]: true, [id2]: false, [id3]: true, ... }
    enableExpanding: enableExpanding,
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
