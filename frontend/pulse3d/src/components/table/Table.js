import DashboardLayout from "@/components/layouts/DashboardLayout";
import { MaterialReactTable, useMaterialReactTable } from "material-react-table";
//Date Picker Imports - these should just be in your Context Provider
import { AdapterDayjs } from "@mui/x-date-pickers/AdapterDayjs";
import { LocalizationProvider } from "@mui/x-date-pickers/LocalizationProvider";

const getHeaderSx = (showColumnFilters) => {
  const commonStyle = { borderBottom: "1px solid var(--dark-gray)", padding: "1rem" };
  const commonSvgRoot = { paddingBottom: "3px", fontSize: 24 };
  const commonSortLabel = { fontSize: 24, paddingTop: "3px" };

  return showColumnFilters
    ? {
        ...commonStyle,
        background: "white",
        color: "black",
        "& .MuiSvgIcon-root": commonSvgRoot,
        "& .MuiTableSortLabel-icon": commonSortLabel,
        "& .MuiFormControl-root": { minWidth: "80px" },
      }
    : {
        ...commonStyle,
        background: "var(--dark-blue)",
        color: "white",
        "& .MuiSvgIcon-root": { ...commonSvgRoot, fill: "white" },
        "& .MuiTableSortLabel-icon": { ...commonSortLabel, fill: "white" },
        "& .MuiDivider-root": { borderColor: "white", borderWidth: "1px" },
      };
};

export default function Table({
  columns = [],
  rowData = [],
  defaultSortColumn,
  defaultSortDesc = true,
  rowSelection,
  setRowSelection,
  subTableFn = null,
  toolbarFn = null,
  rowClickFn = null,
  enablePagination = true,
  enableTopToolbar = true,
  enableExpanding = false,
  enableSelectAll = true,
  enableStickyHeader = true,
  enableColumnResizing = true,
  getRowId = (row) => row.id,
  isLoading = false,
  enableRowSelection = true,
  showColumnFilters = true,
  columnVisibility = {},
  state = {},
  manualSorting = false,
  onSortingChange = null,
  manualFiltering = false,
  onColumnFiltersChange = null,
}) {
  let opts = {
    columns,
    data: rowData,
    initialState: {
      sorting: [
        {
          id: defaultSortColumn,
          desc: defaultSortDesc,
        },
      ],
    },
    enableColumnFilterModes: false,
    enableColumnResizing,
    enableRowSelection,
    enableStickyHeader,
    enableTopToolbar,
    enablePagination,
    enableSelectAll,
    selectAllMode: "all",
    muiTableProps: {
      sx: {
        cursor: "default",
        "& .Mui-TableBodyCell-DetailPanel": {
          maxWidth: 1500,
        },
      },
    },
    muiTableBodyRowProps: ({ row }) => ({ onClick: rowClickFn ? () => rowClickFn(row) : null }),
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
      sx: getHeaderSx(showColumnFilters),
    },
    muiTableBodyCellProps: {
      sx: { whiteSpace: "nowrap" },
    },
    muiPaginationProps: {
      color: "secondary",
      rowsPerPageOptions: [10, 30, 50, 100],
      variant: "outlined",
    },
    autoResetPageIndex: false,
    onRowSelectionChange: setRowSelection, // returns {[id]: true, [id2]: true, ...}
    renderDetailPanel: subTableFn ? ({ row }) => subTableFn(row) : null,
    renderTopToolbar: toolbarFn ? ({ table }) => toolbarFn(table) : null,
    state: {
      rowSelection,
      isLoading,
      density: "compact",
      columnVisibility,
      showColumnFilters,
      ...state,
    }, // rowSelection can be {[id]: true, [id2]: false, [id3]: true, ... }
    enableExpanding,
    muiCircularProgressProps: { size: 100 },
    getRowId: getRowId,
  };

  if (manualSorting) {
    opts = {
      ...opts,
      manualSorting,
      onSortingChange,
    };
  }
  if (manualFiltering) {
    opts = { ...opts, manualFiltering, onColumnFiltersChange };
  }

  const table = useMaterialReactTable(opts);

  return (
    <LocalizationProvider dateAdapter={AdapterDayjs}>
      <MaterialReactTable table={table} />
    </LocalizationProvider>
  );
}

Table.getLayout = (page) => {
  return <DashboardLayout>{page}</DashboardLayout>;
};
