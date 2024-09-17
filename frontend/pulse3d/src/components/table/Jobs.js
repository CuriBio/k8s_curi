import styled from "styled-components";
import { formatDateTime } from "@/utils/generic";
import { getShortUUIDWithTooltip } from "@/utils/jsx";
import { useState, useMemo, useEffect } from "react";
import Table from "./Table";

const Container = styled.div`
  margin: 0 3.5rem;
`;

const PreviewText = styled.div`
  font-style: italic;

  &:hover {
    color: var(--teal-green);
    text-decoration: underline;
    cursor: pointer;
  }
`;

const ErrorText = styled.div`
  text-wrap: wrap;
`;

const getAnalysisParamsStr = (params) => {
  return (
    <div>
      {Object.entries(params).map(([paramName, paramVal]) => {
        if (paramVal === null) {
          return;
        }
        if (paramName === "well_groups") {
          const wellGroups = paramVal;
          return (
            <div key={paramName}>
              well groups:
              {Object.keys(wellGroups).map((label) => (
                <ul key={label} style={{ margin: "3px" }}>
                  {label}: {wellGroups[label].join(", ")}
                </ul>
              ))}
            </div>
          );
        } else {
          if (paramName === "peaks_valleys") {
            paramVal = "user set";
          } else if (paramName == "inverted_post_magnet_wells") {
            paramName = "wells with flipped waveforms";
          }

          return <div key={paramName}>{`${paramName.replaceAll("_", " ")}: ${paramVal}`}</div>;
        }
      })}
    </div>
  );
};

export default function Jobs({ uploadRow, openJobPreview, setSelectedJobs, selectedJobs }) {
  const jobs = uploadRow?.original?.jobs || [];

  const columns = useMemo(
    () => [
      {
        accessorFn: (row) => row.analyzedFile || "None",
        id: "analyzedFile",
        header: "Analyzed Filename",
        size: 300,
      },
      {
        accessorKey: "jobId",
        id: "jobId",
        header: "Job ID",
        size: 130,
        Cell: ({ cell }) => getShortUUIDWithTooltip(cell.getValue(), 4),
      },
      {
        accessorFn: (row) => new Date(row.createdAt),
        header: "Date Created",
        id: "createdAt",
        sortingFn: "datetime",
        size: 200,
        Cell: ({ cell }) => formatDateTime(cell.getValue(), true),
      },
      {
        accessorKey: "analysisParams", //accessorKey used to define `data` column. `id` gets set to accessorKey automatically
        id: "analysisParams",
        header: "Analysis Parameters",
        size: 260,
        Cell: ({ cell }) => getAnalysisParamsStr(cell.getValue()),
      },
      {
        accessorFn: (row) =>
          row.status == "finished" ? "Completed" : row.status[0].toUpperCase() + row.status.slice(1),
        id: "status",
        header: "Status",
        size: 200,
        Cell: ({ cell }) => <ErrorText>{cell.getValue()}</ErrorText>,
      },
      {
        accessorKey: "status",
        id: "snapshot",
        enableColumnFilter: false,
        enableColumnResizing: false,
        enableSorting: false,
        header: "",
        size: 250,
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
        rowSelection={selectedJobs}
        setRowSelection={setSelectedJobs}
        enablePagination={false}
        enableTopToolbar={false}
        enableSelectAll={false}
        enableStickyHeader={false}
        getRowId={(row) => row.jobId}
        enableRowSelection={(row) => !["pending", "running"].includes(row.original.status)}
        showColumnFilters={false}
      />
    </Container>
  );
}
