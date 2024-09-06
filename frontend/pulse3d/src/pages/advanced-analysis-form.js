import { useState, useContext, useMemo } from "react";
import DashboardLayout from "@/components/layouts/DashboardLayout";
import InputDropdownWidget from "@/components/basicWidgets/InputDropdownWidget";
import styled from "styled-components";
import ButtonWidget from "@/components/basicWidgets/ButtonWidget";
import { AuthContext } from "@/pages/_app";
import Table from "@/components/table/Table";
import { Box, IconButton, Tooltip } from "@mui/material";
import { getShortUUIDWithTooltip } from "@/utils/jsx";
import { formatDateTime } from "@/utils/generic";
import DropDownWidget from "@/components/basicWidgets/DropDownWidget";

const OuterContainer = styled.div`
  justify-content: center;
  position: relative;
  padding: 3rem;
`;

const FormContainer = styled.div`
  width: 100%;
  min-width: 1200px;
  border: solid;
  border-color: var(--dark-gray);
  border-width: 2px;
  border-radius: 15px;
  background-color: white;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  align-items: center;
`;

const Header = styled.h2`
  position: relative;
  text-align: center;
  background-color: var(--dark-blue);
  color: var(--light-gray);
  margin: auto;
  width: 100%;
  height: 75px;
  line-height: 3;
`;

const InputSelectionContainer = styled.div`
  width: 50%;
  border: 2px solid var(--dark-gray);
  border-radius: 5px;
  margin-top: 2rem;
  background-color: var(--light-gray);
`;

const DropDownContainer = styled.div`
  width: 100%;
  display: flex;
  justify-content: center;
  position: relative;
  height: 17%;
  align-items: center;
  margin-top: 20px;
`;

const InputSelectionTableContainer = styled.div`
  width: 1150px;
`;

const ToolBarDropDownContainer = styled.div`
  width: 250px;
  background-color: white;
  border-radius: 8px;
  position: relative;
  margin: 15px 20px;
`;

const ButtonContainer = styled.div`
  display: flex;
  justify-content: flex-end;
  padding: 3rem 8rem;
  width: 100%;
`;

const SuccessText = styled.span`
  color: green;
  font-style: italic;
  font-size: 15px;
  padding-right: 10px;
  line-height: 3;
`;

const SmallerIconButton = styled(IconButton)`
  width: 24px;
  height: 24px;
`;

const FORM_STATES = {
  RESET: "idle",
  USER_EDITING: "user_editing",
  SUBMITTING: "submitting",
  SUBMISSION_SUCCESSFUL: "submission_successful",
  SUBMISSION_FAILED: "submission_failed",
  // TODO add other states for modals?
};

const pollP3dJobs = async (filenamePrefix, inputType) => {
  try {
    // TODO set a min and max version
    let url = `${process.env.NEXT_PUBLIC_PULSE3D_URL}/jobs?legacy=false&upload_type=${inputType}&status=finished&filename=${filenamePrefix}&sort_field=filename&sort_direction=ASC`;
    const response = await fetch(url);

    if (response && response.status === 200) {
      const jobs = await response.json();
      return jobs;
    }
    throw Error(`response: ${response.status}`);
  } catch (e) {
    console.log("ERROR getting p3d jobs for user", e);
    throw e;
  }
};

const getPlatemapInfoFromMetas = (jobMeta, uploadMeta) => {
  // check job meta
  jobMeta = JSON.parse(jobMeta);
  let wellGroups = jobMeta?.analysis_params?.well_groups;
  if (wellGroups) {
    return {
      platemapInfo: {
        name: "N/A",
        wellGroups,
      },
      platemapSource: "Pulse3D Override",
    };
  }
  // check upload meta
  uploadMeta = JSON.parse(uploadMeta);
  const platemapName = uploadMeta.platemap_name;
  if (platemapName) {
    return {
      platemapInfo: {
        name: platemapName,
        wellGroups: uploadMeta.platemap_labels,
      },
      platemapSource: "Recording Metadata",
    };
  }
  // return unassigned info
  return {
    platemapInfo: {
      name: "None",
      wellGroups: {},
    },
    platemapSource: "None",
  };
};

export default function AdvancedAnalysisForm() {
  const { accountScope } = useContext(AuthContext);

  const [formState, setFormState] = useState(FORM_STATES.RESET);
  const [inputType, setInputType] = useState();
  const [loadingAvailableP3dJobs, setLoadingAvailableP3dJobs] = useState(false);
  const [availableP3dJobs, setAvailableP3dJobs] = useState([]);
  const [pollAvailableP3dJobsTimeout, setPollAvailableP3dJobsTimeout] = useState();
  const [selectedP3dJobs, setSelectedP3dJobs] = useState([]);

  const formattedJobSelection = selectedP3dJobs.map(
    ({ filename, id, created_at: createdAt, job_meta: jobMeta, upload_meta: uploadMeta }) => {
      const { platemapInfo, platemapSource } = getPlatemapInfoFromMetas(jobMeta, uploadMeta);

      return {
        filename,
        id,
        createdAt,
        platemapInfo,
        platemapSource,
      };
    }
  );

  // TODO probably makes sense to make available products a field in AuthContext
  const availableInputTypes = ["mantarray", "nautilai"].filter((p) =>
    (accountScope || []).some((scope) => scope.includes(p))
  );

  const enableSubmitBtn =
    formState === FORM_STATES.USER_EDITING &&
    inputType != null &&
    selectedP3dJobs.length >= 2 &&
    formattedJobSelection.every((job) => job.platemapSource !== "None");

  const handleInputTypeDropDownSelect = (idx) => {
    setFormState(FORM_STATES.USER_EDITING);
    setInputType(availableInputTypes[idx]);
    // also clear selected and available jobs
    setSelectedP3dJobs([]);
    setAvailableP3dJobs([]);
  };

  const isJobAlreadySelected = (testJob) => {
    return selectedP3dJobs.some((selectedJob) => selectedJob.id === testJob.id);
  };

  const handleInputDropDownSelect = (idx) => {
    if (idx === -1) {
      return;
    }
    setFormState(FORM_STATES.USER_EDITING);

    const newJob = availableP3dJobs[idx];
    if (!isJobAlreadySelected(newJob)) {
      setSelectedP3dJobs([...selectedP3dJobs, newJob]);
    }
  };

  const resetState = () => {
    setFormState(FORM_STATES.RESET);
    setSelectedP3dJobs([]);
    setInputType();
  };

  const handleSubmission = () => {
    if (!enableSubmitBtn) {
      return;
    }
    setFormState(FORM_STATES.SUBMITTING);
    // TODO
  };

  const onSelectInputChange = (e, value) => {
    if (e == null || e.type !== "change" || value == null || value === "") {
      return;
    }
    setLoadingAvailableP3dJobs(true);
    clearTimeout(pollAvailableP3dJobsTimeout);
    const newPollAvailableInputsTimeout = setTimeout(async () => {
      try {
        const newAvailableP3dJobs = (await pollP3dJobs(value, inputType)).filter((retrievedJob) => {
          return !isJobAlreadySelected(retrievedJob);
        });
        setAvailableP3dJobs(newAvailableP3dJobs);
      } catch {}
      setLoadingAvailableP3dJobs(false);
    }, 200);
    setPollAvailableP3dJobsTimeout(newPollAvailableInputsTimeout);
  };

  const removeInputsFromSelection = (jobIdsToRemove) => {
    const newSelectedP3dJobs = selectedP3dJobs.filter((job) => !jobIdsToRemove.includes(job.id));
    setSelectedP3dJobs([...newSelectedP3dJobs]);
  };

  return (
    <OuterContainer>
      <FormContainer>
        <Header>Run Advanced Analysis</Header>
        <InputSelectionContainer>
          <DropDownContainer>
            <div style={{ backgroundColor: "white", marginBottom: "30px" }}>
              <InputDropdownWidget
                label="Select Input Type"
                options={availableInputTypes}
                handleSelection={handleInputTypeDropDownSelect}
                reset={formState === FORM_STATES.RESET}
                width={500}
                disabled={formState === FORM_STATES.SUBMITTING}
              />
            </div>
          </DropDownContainer>
        </InputSelectionContainer>
        <InputSelectionContainer>
          <DropDownContainer>
            <div style={{ backgroundColor: "white", marginBottom: "30px" }}>
              <InputDropdownWidget
                label="Select Inputs"
                options={availableP3dJobs.map((j) => `${j.filename} (${formatDateTime(j.created_at)})`)}
                handleSelection={handleInputDropDownSelect}
                reset={formState === FORM_STATES.RESET || availableP3dJobs.length === 0}
                width={500}
                disabled={formState === FORM_STATES.SUBMITTING || inputType == null}
                onInputChange={onSelectInputChange}
                loading={loadingAvailableP3dJobs}
              />
            </div>
          </DropDownContainer>
        </InputSelectionContainer>
        <div style={{ textAlign: "center", marginTop: "10px", marginBottom: "10px", fontSize: "18px" }}>
          <b>Selected Inputs:</b>
        </div>
        <InputSelectionTableContainer>
          <InputSelectionTable
            formattedJobSelection={formattedJobSelection}
            removeInputsFromSelection={removeInputsFromSelection}
          />
        </InputSelectionTableContainer>
        <ButtonContainer>
          {formState === FORM_STATES.SUBMISSION_SUCCESSFUL && (
            <SuccessText>Submission Successful!</SuccessText>
          )}
          <ButtonWidget
            width="200px"
            height="50px"
            position="relative"
            borderRadius="3px"
            label="Reset"
            clickFn={resetState}
          />
          <ButtonWidget
            width="200px"
            height="50px"
            position="relative"
            borderRadius="3px"
            left="10px"
            backgroundColor={enableSubmitBtn ? "var(--dark-blue)" : "var(--dark-gray)"}
            disabled={!enableSubmitBtn}
            inProgress={formState === FORM_STATES.SUBMITTING}
            label="Submit"
            clickFn={handleSubmission}
          />
        </ButtonContainer>
      </FormContainer>
      {/* TODO
      <ModalWidget
        open={modalState}
        labels={failedUploadsMsg}
        buttons={modalButtons}
        closeModal={handleClose}
        header="Error Occurred"
      />
      <ModalWidget
        open={usageModalState}
        labels={usageModalLabels.messages}
        closeModal={() => {
          setUsageModalState(false);
          router.replace("/uploads", undefined, { shallow: true });
        }}
        header={usageModalLabels.header}
      />
      <ModalWidget
        open={creditUsageAlert}
        labels={["This re-analysis will consume 1 analysis credit."]}
        closeModal={() => {
          setCreditUsageAlert(false);
          setAlertShowed(true);
        }}
        header={"Attention!"}
      />
      */}
    </OuterContainer>
  );
}

AdvancedAnalysisForm.getLayout = (page) => {
  return <DashboardLayout>{page}</DashboardLayout>;
};

function InputSelectionTable({ formattedJobSelection, removeInputsFromSelection }) {
  const [checkedRows, setCheckedRows] = useState({});

  const checkedJobIds = Object.keys(checkedRows);

  const columns = useMemo(
    () => [
      {
        accessorKey: "filename",
        id: "filename",
        header: "Analysis Name",
        filterVariant: "autocomplete",
        size: 300,
        minSize: 200,
      },
      {
        accessorKey: "id",
        filterVariant: "autocomplete",
        id: "id",
        header: "Job ID",
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
        size: 200,
        minSize: 175,
        muiFilterDatePickerProps: {
          slots: { clearButton: SmallerIconButton, openPickerButton: SmallerIconButton },
        },
        Cell: ({ cell }) => formatDateTime(cell.getValue()),
      },
      {
        accessorKey: "platemapInfo",
        id: "platemapInfo",
        header: "PlateMap",
        filterVariant: "autocomplete",
        size: 200,
        minSize: 130,
        // TODO move this function to utils/jsx.js?
        Cell: ({ cell }) => {
          const { name, wellGroups } = cell.getValue();
          const wellGroupsEntries = Object.entries(wellGroups || {});
          const tooltipText =
            wellGroupsEntries.length === 0
              ? "No Groups"
              : wellGroupsEntries.map(([label, wells], idx) => {
                  return (
                    <div key={`well-group-${idx}`}>
                      {label}: {wells.sort().join(", ")}
                    </div>
                  );
                });
          return (
            <Tooltip title={<span style={{ fontSize: "15px" }}>{tooltipText}</span>}>
              <div>{name}</div>
            </Tooltip>
          );
        },
      },
      {
        accessorKey: "platemapSource",
        id: "platemapSource",
        header: "PlateMap Source",
        filterVariant: "autocomplete",
        size: 200,
        minSize: 130,
      },
    ],
    []
  );

  const handleActionSelection = (optionIdx) => {
    if (optionIdx === 0 /* Remove */) {
      removeInputsFromSelection(checkedJobIds);
    } else if (optionIdx === 1 /* Assign/Override Platemap */) {
      // TODO
    }
    setCheckedRows({});
  };

  const actionsFn = (t) => {
    return (
      <Box sx={{ width: "100%", position: "relative", display: "flex", justifyContent: "end" }}>
        <ToolBarDropDownContainer>
          <DropDownWidget
            label="Actions"
            options={["Remove", "Assign/Override Platemap"]}
            disableOptions={[checkedJobIds.length === 0, true]}
            optionsTooltipText={[
              "Must make a selection below before actions become available.",
              "Coming Soon.",
            ]}
            handleSelection={handleActionSelection}
            reset={checkedJobIds.length === 0}
          />
        </ToolBarDropDownContainer>
      </Box>
    );
  };

  return (
    <Table
      columns={columns}
      rowData={formattedJobSelection}
      defaultSortColumn={"filename"}
      rowSelection={checkedRows}
      setRowSelection={setCheckedRows}
      toolbarFn={actionsFn}
      enablePagination={false}
      showColumnFilters={false}
    />
  );
}

function LongitudinalAnalysisParams() {
  // TODO
}
