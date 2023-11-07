import styled from "styled-components";
import { formatDateTime } from "@/utils/generic";
import { useState, useMemo, useEffect } from "react";
import Table from "./Table";
import { select } from "d3";

const Container = styled.div`
  padding: 0 3.5rem;
`;

const PreviewText = styled.div`
  font-style: italic;

  &:hover {
    color: var(--teal-green);
    text-decoration: underline;
    cursor: pointer;
  }
`;

export default function Jobs({
  row,
  openJobPreview,
  selectedUploads,
  setSelectedUploads,
  setSelectedJobs,
  selectedJobs,
}) {
  const [rowSelection, setRowSelection] = useState({});
  const [jobs, setJobs] = useState([]);
  const [uploadId, setUploadId] = useState();

  const localSelectedJobs = Object.keys(rowSelection).filter((x) => rowSelection[x]);

  useEffect(() => {
    if (row && "original" in row) {
      setJobs(row.original.jobs);
      setUploadId(row.original.id);
    }
  }, [row]);

  useEffect(() => {
    checkInitialSelectedJobs();
  }, [selectedJobs, uploadId]);

  const checkInitialSelectedJobs = () => {
    if (uploadId in selectedJobs) {
      const initialJobs = {};

      for (const id of selectedJobs[uploadId]) {
        initialJobs[id] = true;
      }

      setRowSelection(initialJobs);
    }
  };

  const handleSelectedJobsDiff = () => {
    if (jobs.length > 0) {
      if (
        !(
          uploadId in selectedJobs &&
          selectedJobs[uploadId].length === localSelectedJobs.length &&
          selectedJobs[uploadId].every((val) => localSelectedJobs.includes(val))
        )
      )
        // set state in parent component to hold all selected jobs
        setSelectedJobs({ ...selectedJobs, [uploadId]: localSelectedJobs });
    }
  };

  useEffect(() => {
    handleSelectedJobsDiff();
  }, [rowSelection]);

  const getAnalysisParamsStr = (params) => {
    return (
      <div>
        {Object.keys(params).map((param) => {
          let paramVal;

          if (params[param] !== null) {
            if (param === "well_groups") {
              const wellGroups = params[param];
              return (
                <div key={param}>
                  well groups:
                  {Object.keys(wellGroups).map((label) => (
                    <ul key={label} style={{ margin: "3px" }}>
                      {label}: {wellGroups[label].join(", ")}
                    </ul>
                  ))}
                </div>
              );
            } else {
              paramVal = param === "peaks_valleys" ? "user set" : params[param];

              if (param == "inverted_post_magnet_wells") {
                param = "wells with flipped waveforms";
              }

              return <div key={param}>{`${param.replaceAll("_", " ")}: ${paramVal}`}</div>;
            }
          }
        })}
      </div>
    );
  };

  const columns = useMemo(
    () => [
      {
        accessorFn: (row) => (row.analyzedFile ? row.analyzedFile : "None"),
        id: "analyzedFile",
        header: "Analyzed Filename",
        filterVariant: "autocomplete",
        size: 300,
      },
      {
        accessorFn: (row) => new Date(row.createdAt),
        header: "Date Created",
        id: "createdAt",
        filterVariant: "date",
        sortingFn: "datetime",
        size: 200,
        Cell: ({ cell }) => formatDateTime(cell.getValue()),
      },
      {
        // TODO fix filtering, doesn't grab correct values
        accessorKey: "analysisParams", //accessorKey used to define `data` column. `id` gets set to accessorKey automatically
        filterVariant: "autocomplete",
        id: "analysisParams",
        header: "Analysis Parameters",
        size: 300,
        Cell: ({ cell }) => getAnalysisParamsStr(cell.getValue()),
      },
      {
        accessorFn: (row) =>
          row.status == "finished" ? "Completed" : row.status[0].toUpperCase() + row.status.slice(1),
        id: "status",
        filterVariant: "autocomplete",
        header: "Status",
        size: 200,
      },
      {
        accessorKey: "status",
        id: "snapshot",
        enableColumnFilter: false,
        enableSorting: false,
        filterVariant: "autocomplete",
        header: "",
        size: 250,
        // TODO handle snapshot preview functionality
        Cell: ({ cell }) => {
          return (
            cell.getValue() == "finished" && (
              <PreviewText onClick={() => openJobPreview(cell.row.original)}>
                Waveform Snapshot Preview
              </PreviewText>
            )
          );
        },
      },
    ],
    []
  );

  return (
    <Container>
      <Table
        columns={columns}
        rowData={jobs}
        defaultSortColumn={"createdAt"}
        rowSelection={rowSelection}
        setRowSelection={setRowSelection}
        enablePagination={false}
        enableTopToolbar={false}
        enableSelectAll={false}
        enableStickyHeader={false}
        getRowId={(row) => row.jobId}
        enableRowSelection={(row) => !["pending", "running"].includes(row.status)}
        showColumnFilters={false}
      />
    </Container>
  );
}
