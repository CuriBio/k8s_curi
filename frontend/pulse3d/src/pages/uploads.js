import CircularSpinner from "@/components/basicWidgets/CircularSpinner";
import DropDownWidget from "@/components/basicWidgets/DropDownWidget";
import ModalWidget from "@/components/basicWidgets/ModalWidget";
import DashboardLayout, { UploadsContext } from "@/components/layouts/DashboardLayout";
import styled from "styled-components";
import { useContext, useState, useEffect } from "react";
import InteractiveAnalysisModal from "@/components/uploads/InteractiveAnalysisModal";
import { AuthContext } from "@/pages/_app";
import DataTable from "react-data-table-component";
import FilterHeader from "@/components/table/FilterHeader";
import UploadsSubTable from "@/components/table/UploadsSubTable";

const uploadTableColumns = [
  {
    name: "File Owner",
    admin: true,
    center: false,
    selector: (row) => row.username,
  },
  {
    name: "Recording Name",
    admin: false,
    center: false,
    selector: (row) => row.name || "none",
  },
  {
    name: "Upload ID",
    admin: false,
    center: false,
    selector: (row) => row.id,
  },
  {
    name: "Created Date",
    admin: false,
    center: false,
    selector: (row) => row.createdAt,
  },
  {
    name: "Last Analyzed",
    center: false,
    admin: false,
    selector: (row) => row.lastAnalyzed,
  },
];

// These can be overridden on a col-by-col basis by setting a value in an  obj in the columns array above
const columnProperties = {
  center: true,
  sortable: true,
};

const customStyles = {
  headRow: {
    style: {
      backgroundColor: "var(--dark-blue)",
      color: "white",
    },
  },
  subHeader: {
    style: {
      backgroundColor: "var(--dark-blue)",
    },
  },
  rows: {
    style: {
      backgroundColor: "var(--light-gray)",
      borderLeft: "2px solid var(--dark-gray)",
      borderRight: "2px solid var(--dark-gray)",
    },
  },
};

const Container = styled.div`
  display: flex;
  position: relative;
  justify-content: start;
  padding: 0% 3% 3% 3%;
  flex-direction: column;
`;
const SpinnerContainer = styled.div`
  margin: 50px;
`;

const InteractiveAnalysisContainer = styled.div`
  width: 78%;
  margin: 1%;
  background-color: white;
  height: 800px;
  border-radius: 5px;
  overflow: none;
`;

const PageContainer = styled.div`
  width: 80%;
`;
const DropDownContainer = styled.div`
  width: 250px;
  background-color: white;
  border-radius: 5px;
  left: 70%;
  position: relative;
  margin: 3% 1% 1% 1%;
`;
const ModalSpinnerContainer = styled.div`
  position: relative;
  display: flex;
  justify-content: center;
  height: 315px;
  align-items: center;
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
};

export default function Uploads() {
  const { accountType } = useContext(AuthContext);
  const { uploads, setFetchUploads } = useContext(UploadsContext);
  const [jobs, setJobs] = useState([]);
  const [rows, setRows] = useState([]);
  const [displayRows, setDisplayRows] = useState([]);
  const [checkedJobs, setCheckedJobs] = useState([]);
  const [checkedUploads, setCheckedUploads] = useState([]);
  const [resetDropdown, setResetDropdown] = useState(false);
  const [modalState, setModalState] = useState(false);
  const [modalLabels, setModalLabels] = useState({ header: "", messages: [] });
  const [modalButtons, setModalButtons] = useState([]);
  const [openInteractiveAnalysis, setOpenInteractiveAnalysis] = useState(false);
  const [selectedAnalysis, setSelectedAnalysis] = useState();
  const [pending, setPending] = useState(true);
  const [filterString, setFilterString] = useState("");
  const [filtercolumn, setFilterColumn] = useState("");
  const [updateData, toggleUpdateData] = useState(false);
  const [selectedUploads, setSelectedUploads] = useState([]);

  useEffect(() => {
    setTimeout(async () => {
      // don't call get jobs if downloading or deleting in progress because it backs up server
      if (!["downloading", "deleting"].includes(modalState) && updateData) {
        await getAllJobs();
        toggleUpdateData(!updateData);
      }
    }, [1e4]);
  }, [updateData]);

  useEffect(() => {
    if (jobs.length > 0) {
      setPending(false);
    }
  }, [displayRows]);
  const toFilterField =
    accountType === "admin"
      ? {
          Owner: "username",
          Recording: "name",
          ID: "id",
          "Date Created": "createdAt",
          "Last Analyzed": "lastAnalyzed",
        }
      : {
          Recording: "name",
          ID: "id",
          "Date Created": "createdAt",
          "Last Analyzed": "lastAnalyzed",
        };

  //when filter string changes, refilter results

  useEffect(() => {
    const newList = rows.filter((row) => {
      //if the column being filtered is a date
      if (toFilterField[filtercolumn] === "createdAt" || toFilterField[filtercolumn] === "lastAnalyzed") {
        return row[toFilterField[filtercolumn]]
          .toLocaleLowerCase()
          .includes(filterString.toLocaleLowerCase());
      } else if (row[toFilterField[filtercolumn]]) {
        return row[toFilterField[filtercolumn]].includes(filterString);
      }
    });
    setDisplayRows(newList);
  }, [filterString]);

  useEffect(() => {
    if (!openInteractiveAnalysis) {
      // reset when interactive analysis modal closes
      resetTable();
    }
  }, [openInteractiveAnalysis]);

  const resetTable = () => {
    setResetDropdown(true);
    setCheckedUploads([]);
    setCheckedJobs([]);
    getAllJobs();
  };

  const getAllJobs = async () => {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_PULSE3D_URL}/jobs?download=False`);
      if (response && response.status === 200) {
        const { jobs } = await response.json();
        const newJobs = jobs.map(({ id, upload_id, created_at, object_key, status, meta }) => {
          const analyzedFile = object_key ? object_key.split("/")[object_key.split("/").length - 1] : "";
          const formattedTime = formatDateTime(created_at);
          const parsedMeta = JSON.parse(meta);
          const analysisParams = parsedMeta.analysis_params;
          const isChecked = checkedJobs.includes(id);
          return {
            jobId: id,
            uploadId: upload_id,
            analyzedFile,
            datetime: formattedTime,
            status,
            analysisParams,
            // version: pulse3dVersions[0], // tag with latest version for now, can't be before v0.25.1
            version: "0.25.2",
            checked: isChecked,
          };
        });
        setJobs(newJobs);
      }
    } catch (e) {
      console.log("ERROR fetching jobs in /uploads");
    }
  };

  const formatDateTime = (datetime) => {
    if (datetime)
      return new Date(datetime + "Z").toLocaleDateString(undefined, {
        hour: "numeric",
        minute: "numeric",
      });
    else {
      const now = new Date();
      const datetime =
        now.getFullYear() +
        "-" +
        (now.getMonth() + 1) +
        "-" +
        now.getDate() +
        "-" +
        now.getHours() +
        now.getMinutes() +
        now.getSeconds();
      return datetime;
    }
  };

  useEffect(() => {
    getAllJobs();
    // start 10 second interval
    // don't call get jobs if downloading or deleting in progress because it backs up server
    if (!["downloading", "deleting"].includes(modalState)) {
      toggleUpdateData(!updateData);
    }
  }, [uploads]);

  useEffect(() => {
    const formattedUploads = uploads.map(({ username, id, filename, created_at }) => {
      const formattedTime = formatDateTime(created_at);
      const recName = filename ? filename.split(".")[0] : null;
      const uploadJobs = jobs
        .filter(({ uploadId }) => uploadId === id)
        .sort((a, b) => new Date(b.datetime) - new Date(a.datetime));
      const isChecked = selectedUploads.includes(id);
      const lastAnalyzed = uploadJobs[0] ? uploadJobs[0].datetime : formattedTime;
      return {
        username,
        name: recName,
        id,
        createdAt: formattedTime,
        lastAnalyzed,
        jobs: uploadJobs,
        checked: isChecked,
      };
    });

    setRows([...formattedUploads]);
    setDisplayRows([...formattedUploads]);
  }, [jobs]);

  const handleDropdownSelection = (option) => {
    if (option === 1) {
      setModalButtons(["Close", "Confirm"]);
      setModalLabels(modalObjs.delete);
      setModalState("generic");
    } else if (option === 0) {
      // if download, check that no job contains an error status
      const failedJobs = jobs.filter(
        ({ jobId, status }) => checkedJobs.includes(jobId) && status === "error"
      );

      if (failedJobs.length === 0) {
        downloadAnalyses();
      } else {
        setModalButtons(["Close", "Continue"]);
        setModalLabels(modalObjs.containsFailedJob);
        setModalState("generic");
      }
    } else if (option === 2) {
      const jobDetails = jobs.filter(({ jobId }) => jobId == checkedJobs[0]);
      setSelectedAnalysis(jobDetails[0]);
      setOpenInteractiveAnalysis(true);
    }

    setResetDropdown(false);
  };

  const handleDeletions = async () => {
    try {
      let failedDeletion = false;
      // soft delete uploads
      if (checkedUploads.length > 0) {
        const uploadsURL = `${process.env.NEXT_PUBLIC_PULSE3D_URL}/uploads?`;
        checkedUploads.map((id) => (uploadsURL += `upload_ids=${id}&`));
        const uploadsResponse = await fetch(uploadsURL.slice(0, -1), {
          method: "DELETE",
        });

        failedDeletion ||= uploadsResponse.status !== 200;
      }

      // soft delete all jobs
      if (checkedJobs.length > 0) {
        const jobsURL = `${process.env.NEXT_PUBLIC_PULSE3D_URL}/jobs?`;
        checkedJobs.map((id) => (jobsURL += `job_ids=${id}&`));
        const jobsResponse = await fetch(jobsURL.slice(0, -1), {
          method: "DELETE",
        });

        failedDeletion ||= jobsResponse.status !== 200;
      }
      if (failedDeletion) {
        setModalButtons(["Close"]);
        setModalLabels(modalObjs.failedDeletion);
        setModalState("generic");
      }
      // rerender table with updated deletions
      await setFetchUploads();
      return failedDeletion;
    } catch (e) {
      console.log("ERROR attempting to soft delete selected jobs and uploads");
    }
  };

  const handleModalClose = async (idx) => {
    if (modalButtons[idx] === "Continue") {
      // this block gets hit when user chooses to continue without 'error' status analyses
      downloadAnalyses();
    } else if (modalButtons[idx] === "Confirm") {
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
    } else {
      // close in progress modal
      // also resets for any 'Close' modal button events
      // index 0 in buttons
      setModalState(false);
      resetTable();
    }
  };

  const downloadAnalyses = async () => {
    try {
      // removes any jobs with error + pending statuses
      const finishedJobs = jobs.filter(
        ({ jobId, status }) => checkedJobs.includes(jobId) && status === "finished"
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
          throw Error(e);
        }
      } else {
        // let user know in the off chance that the only files they selected are not finished analyzing or failed
        setModalLabels(modalObjs.nothingToDownload);
        setModalButtons(["Close"]);
        setModalState("generic");
      }
    } catch (e) {
      console.log(`ERROR fetching presigned url to download analysis: ${e}`);
      setModalLabels(modalObjs.downloadError);
      setModalState("generic");
    }
  };

  const downloadSingleFile = async ({ jobId }) => {
    // request only presigned urls for selected job
    const url = `${process.env.NEXT_PUBLIC_PULSE3D_URL}/jobs?job_ids=${jobId}`;
    const response = await fetch(url);

    if (response.status === 200) {
      const { jobs } = await response.json();
      const presignedUrl = jobs[0].url;

      if (presignedUrl) {
        const a = document.createElement("a");
        document.body.appendChild(a);
        a.setAttribute("href", presignedUrl);
        a.setAttribute("download", jobs[0].id);
        a.click();
        a.remove();
      }
    } else {
      throw Error();
    }
  };

  const downloadMultiFiles = async (jobs) => {
    try {
      //streamsaver has to be required here otherwise you get build errors with "document is not defined"
      const { createWriteStream } = require("streamsaver");
      const url = `${process.env.NEXT_PUBLIC_PULSE3D_URL}/jobs/download`;
      const jobIds = jobs.map(({ jobId }) => jobId);

      const response = await fetch(url, {
        method: "POST",
        body: JSON.stringify({ job_ids: jobIds }),
      });

      if (response.status === 200) {
        const now = formatDateTime();
        const zipFilename = `MA-analyses__${now}__${jobs.length}.zip`;

        // only stream to file if not firefox. Once the underlying issue with streaming on
        // firefox is fixed, should remove this
        if (navigator.userAgent.indexOf("Firefox") != -1) {
          const file = await response.blob();
          const url = window.URL.createObjectURL(file);

          const a = document.createElement("a");
          document.body.appendChild(a);
          a.setAttribute("href", url);
          a.setAttribute("download", zipFilename);
          a.click();
          a.remove();
        } else {
          const fileStream = createWriteStream(zipFilename);
          const writer = fileStream.getWriter();

          if (response.body.pipeTo) {
            writer.releaseLock();
            return response.body.pipeTo(fileStream);
          }

          const reader = response.body.getReader();

          () =>
            reader
              .read()
              .then(({ value, done }) => (done ? writer.close() : writer.write(value).then(pump)))();
        }
      } else {
        throw Error();
      }
    } catch (e) {
      console.log(`ERROR during multi file download: ${e}`);
      throw Error();
    }
  };
  const ExpandedComponent = ({ data }) => {
    const [jobToEdit, setJobToEdit] = useState();

    const [checkArray, setCheckArray] = useState(data.jobs.map((job) => job.checked));

    //takes care of adding the state of checked jobs
    useEffect(() => {
      if (jobToEdit) {
        if (jobToEdit.action === "add") {
          for (let i = 0; i < jobs.length; i++) {
            if (jobs[i].jobId === jobToEdit.id) {
              jobs[i].checked = true;
              setCheckedJobs([...checkedJobs, jobs[i].jobId]);
            }
          }
        } else if (jobToEdit.action === "remove") {
          for (let i = 0; i < jobs.length; i++) {
            if (jobs[i].jobId === jobToEdit.id) {
              for (let j = 0; j < displayRows.length; j++) {
                if (displayRows[j].id === jobs[i].uploadId) {
                  displayRows[j].checked = false;
                  let temp = selectedUploads;
                  setSelectedUploads(temp.filter((row) => row !== displayRows[j].id));
                }
              }
              jobs[i].checked = false;
              if (checkedJobs.length === 1) {
                setCheckedJobs([]);
              } else {
                let temp = checkedJobs;
                const location = temp.indexOf(jobToEdit.id);
                temp.splice(location, 1);
                setCheckedJobs(temp);
              }
            }
          }
        }
        let temp = [];
        data.jobs.forEach((job) => {
          if (checkedJobs.includes(job.jobId)) {
            temp.push(job.checked);
          }
        });
        if (temp.length === checkArray.length) {
          setCheckArray(temp);
        }
      }
    }, [jobToEdit]);
    return (
      <UploadsSubTable
        jobs={data.jobs}
        checkedArray={checkArray}
        setJobToEdit={(e) => {
          setJobToEdit(e);
        }}
      />
    );
  };
  return (
    <>
      {!openInteractiveAnalysis ? (
        <PageContainer>
          <DropDownContainer>
            <DropDownWidget
              label="Actions"
              options={["Download", "Delete", "Interactive Analysis"]}
              disableOptions={[
                ...Array(2).fill(checkedJobs.length === 0 && checkedUploads.length === 0),
                checkedJobs.length !== 1 ||
                  jobs.filter((job) => job.jobId === checkedJobs[0])[0].status !== "finished",
              ]}
              optionsTooltipText={[
                ...Array(2).fill("Must make a selection below before actions become available."),
                "You must select one successful job to enable interactive analysis.",
              ]}
              handleSelection={handleDropdownSelection}
              reset={resetDropdown}
            />
          </DropDownContainer>
          <Container>
            <DataTable
              data={displayRows}
              columns={uploadTableColumns
                .filter(
                  // if admin user then show all columns, else just show non-admin columns
                  (e) => accountType === "admin" || !e.admin
                )
                .map((e) => {
                  return {
                    ...columnProperties,
                    ...e,
                  };
                })}
              pagination
              expandableRows
              expandableRowsComponent={ExpandedComponent}
              customStyles={customStyles}
              progressPending={pending}
              progressComponent={
                <SpinnerContainer>
                  <CircularSpinner size={200} color={"secondary"} />
                </SpinnerContainer>
              }
              subHeader
              subHeaderAlign="left"
              subHeaderComponent={
                <FilterHeader
                  columns={
                    accountType === "admin"
                      ? ["", "Owner", "Recording", "ID", "Date Created", "Last Analyzed"]
                      : ["", "Recording", "ID", "Date Created", "Last Analyzed"]
                  }
                  setFilterString={setFilterString}
                  setFilterColumn={setFilterColumn}
                  loading={pending}
                />
              }
              selectableRowsNoSelectAll
              selectableRows
              selectableRowSelected={(row) => row.checked}
              onSelectedRowsChange={({ selectedRows }) => {
                for (let i = 0; i < displayRows.length; i++) {
                  if (selectedRows.includes(displayRows[i])) {
                    displayRows[i].checked = true;
                  } else {
                    displayRows[i].checked = false;
                  }
                }
                setDisplayRows(displayRows);
              }}
            />
          </Container>
        </PageContainer>
      ) : (
        <InteractiveAnalysisContainer>
          <InteractiveAnalysisModal
            selectedJob={selectedAnalysis}
            setOpenInteractiveAnalysis={setOpenInteractiveAnalysis}
          />
        </InteractiveAnalysisContainer>
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
