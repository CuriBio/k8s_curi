import { useState, useContext, useMemo } from "react";
import DashboardLayout from "@/components/layouts/DashboardLayout";
import InputDropdownWidget from "@/components/basicWidgets/InputDropdownWidget";
import styled from "styled-components";
import ButtonWidget from "@/components/basicWidgets/ButtonWidget";
import { AuthContext } from "@/pages/_app";
import Table from "@/components/table/Table";
import { Box, IconButton, Tooltip } from "@mui/material";
import { getShortUUIDWithTooltip } from "@/utils/jsx";
import { formatDateTime, getLocalTzOffsetHours, getSortedWellListStr } from "@/utils/generic";
import DropDownWidget from "@/components/basicWidgets/DropDownWidget";
import AnalysisParamContainer from "@/components/uploadForm/AnalysisParamContainer";

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

const SectionHeader = styled.div`
  text-align: center;
  margin-top: 10px;
  margin-bottom: 10px;
  font-size: 18px;
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

const LongitudinalAnalysisParamsContainer = styled.div`
  padding: 1rem;
  top: 12%;
  width: 1150px;
  position: relative;
  display: grid;
  border: solid;
  justify-content: center;
  border-color: var(--dark-gray);
  border-width: 2px;
  border-radius: 7px;
  background-color: var(--light-gray);
  grid-template-columns: 45% 55%;
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

const ErrorText = styled.span`
  color: red;
  font-style: italic;
  font-size: 15px;
  padding-right: 10px;
  line-height: 3;
`;

const SmallerIconButton = styled(IconButton)`
  width: 24px;
  height: 24px;
`;

const MAX_NUM_INPUTS = 75;

const FORM_STATES = {
  RESET: "idle",
  USER_EDITING: "user_editing",
  SUBMITTING: "submitting",
  SUBMISSION_SUCCESSFUL: "submission_successful",
  SUBMISSION_FAILED: "submission_failed",
};

const pollP3dJobs = async (filenamePrefix, inputType, versionMajMin) => {
  try {
    const query = [
      "legacy=false",
      `upload_type=${inputType}`,
      "status=finished",
      `filename=${filenamePrefix}`,
      "sort_field=filename",
      "sort_direction=ASC",
      "include_prerelease_versions=false",
      `version_min=${versionMajMin || "1.0"}.0`,
    ];
    if (versionMajMin) {
      query.push(`version_max=${versionMajMin}.999`);
    }
    const url = `${process.env.NEXT_PUBLIC_PULSE3D_URL}/jobs?${query.join("&")}`;
    const response = await fetch(url);

    if (response && response.status === 200) {
      const jobs = await response.json();
      return jobs;
    }
    throw Error(`response status: ${response.status}`);
  } catch (e) {
    console.log("ERROR getting p3d jobs for user:", e);
    throw e;
  }
};

const submitAdvAnalysisJob = async (inputType, analysisParams, selectedP3dJobs) => {
  let requestBody;
  try {
    requestBody = JSON.stringify({
      version: "0.1.0",
      output_name: analysisParams.analysisTitle,
      sources: selectedP3dJobs.map((job) => job.id),
      platemap_overrides: { platemaps: [], assignments: {} },
      experiment_start_time_utc: processExperimentStartDate(analysisParams.experimentStartDate)
        .toISOString()
        .replace("T", " ")
        .split(".")[0],
      local_tz_offset_hours: analysisParams.localTzOffsetHours,
      input_type: inputType,
      job_type: "longitudinal",
    });
  } catch (e) {
    console.log("ERROR formatting requestBody for advanced analysis job submission:", e);
    throw e;
  }

  try {
    const url = `${process.env.NEXT_PUBLIC_ADVANCED_ANALYSIS_URL}/advanced-analyses`;
    const res = await fetch(url, { method: "POST", body: requestBody });
    if (res?.status !== 201) {
      throw Error(`response status: ${res?.status}`);
    }
  } catch (e) {
    console.log("ERROR submitting advanced analysis job:", e);
    throw e;
  }
};

const extractFromMetas = (jobMeta, uploadMeta) => {
  // check job meta
  jobMeta = JSON.parse(jobMeta);
  const version = jobMeta?.version;
  let wellGroups = jobMeta?.analysis_params?.well_groups;
  if (wellGroups) {
    return {
      platemapInfo: {
        name: "N/A",
        wellGroups,
      },
      platemapSource: "Pulse3D Override",
      version,
    };
  }
  // check upload meta
  uploadMeta = JSON.parse(uploadMeta);
  const platemapName = uploadMeta?.platemap_name;
  const platemapLabels = uploadMeta?.platemap_labels;
  if (platemapName && platemapLabels) {
    return {
      platemapInfo: {
        name: platemapName,
        wellGroups: platemapLabels,
      },
      platemapSource: "Recording Metadata",
      version,
    };
  }
  // return unassigned info
  return {
    platemapInfo: {
      name: "None",
      wellGroups: {},
    },
    platemapSource: "None",
    version,
  };
};

const processExperimentStartDate = (d) => {
  return new Date(`${d.replace("_", " ")}:00:00`);
};

const getMajMinFromVersion = (v) => {
  if (v == null) {
    return null;
  }
  try {
    return v.split(".").slice(0, -1).join(".");
  } catch {
    console.log(`ERROR invalid job version: ${v}`);
    return null;
  }
};

const getDefaultAnalysisParams = () => {
  return {
    analysisTitle: "",
    experimentStartDate: "",
    localTzOffsetHours: getLocalTzOffsetHours(),
  };
};

const getUpdatedAnalysisParamErrors = (newParams, paramErrors) => {
  const updatedParamErrors = { ...paramErrors };

  if ("analysisTitle" in newParams) {
    const testVal = newParams.analysisTitle;
    let errMsg = "";
    if (testVal == null || testVal.length === 0) {
      errMsg = "Required";
    } else if (testVal.length > 300) {
      // Tanner (9/5/24): picking an arbitrary max length since it seems appropriate to have one. Not sure what this max should actually be
      errMsg = "Must be <= 300 characters";
    }
    updatedParamErrors.analysisTitle = errMsg;
  }

  if ("experimentStartDate" in newParams) {
    const testVal = newParams.experimentStartDate;
    let errMsg = "";
    if (testVal == null || testVal.length === 0) {
      errMsg = "Required";
    } else if (testVal.length !== 13 || isNaN(processExperimentStartDate(testVal))) {
      errMsg = "Invalid value/format, must be 'YYYY-MM-DD_HH'";
    }
    updatedParamErrors.experimentStartDate = errMsg;
  }

  return updatedParamErrors;
};

export default function AdvancedAnalysisForm() {
  const { accountScope } = useContext(AuthContext);

  const [formState, setFormState] = useState(FORM_STATES.RESET);
  const [inputType, setInputType] = useState();
  const [loadingAvailableP3dJobs, setLoadingAvailableP3dJobs] = useState(false);
  const [availableP3dJobs, setAvailableP3dJobs] = useState([]);
  const [pollAvailableP3dJobsTimeout, setPollAvailableP3dJobsTimeout] = useState();
  const [selectedP3dJobs, setSelectedP3dJobs] = useState([]);

  const [analysisParams, setAnalysisParams] = useState(getDefaultAnalysisParams());
  const [analysisParamErrors, setAnalysisParamErrors] = useState(
    getUpdatedAnalysisParamErrors(getDefaultAnalysisParams(), {})
  );

  const formattedJobSelection = selectedP3dJobs.map(
    ({ filename, id, created_at: createdAt, job_meta: jobMeta, upload_meta: uploadMeta, meta }) => {
      const { platemapInfo, platemapSource, version } = extractFromMetas(jobMeta, uploadMeta);

      return {
        filename,
        id,
        createdAt,
        platemapInfo,
        platemapSource,
        version,
      };
    }
  );

  // TODO probably makes sense to make available products a field in AuthContext
  const availableInputTypes = ["mantarray", "nautilai"].filter((p) =>
    (accountScope || []).some((scope) => scope.includes(p))
  );

  const versionMajMin = getMajMinFromVersion(formattedJobSelection[0]?.version);
  const inputLimitReached = selectedP3dJobs.length >= MAX_NUM_INPUTS;
  const enableSubmitBtn =
    formState === FORM_STATES.USER_EDITING &&
    inputType != null &&
    selectedP3dJobs.length >= 2 &&
    selectedP3dJobs.length <= MAX_NUM_INPUTS &&
    formattedJobSelection.every((job) => job.platemapSource !== "None") &&
    Object.values(analysisParamErrors).every((msg) => msg === "");

  const updateAnalysisParams = (newParams) => {
    setFormState(FORM_STATES.USER_EDITING);
    const updatedParams = { ...analysisParams, ...newParams };
    const updatedParamErrors = getUpdatedAnalysisParamErrors(newParams, analysisParamErrors);
    setAnalysisParams(updatedParams);
    setAnalysisParamErrors(updatedParamErrors);
  };

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
    if (versionMajMin === null) {
      try {
        const newMajMinVersion = getMajMinFromVersion(JSON.parse(newJob.job_meta).version);
        if (newMajMinVersion === null) {
          return;
        }
        // now that a version has been set, need to filter out all jobs with a different version here since the list
        // of available jobs won't be updated until the user starts typing into the input box again, which is not required before choosing
        // another option from the list
        setAvailableP3dJobs(
          availableP3dJobs.filter((j) => {
            try {
              const jobVersion = JSON.parse(j.job_meta).version;
              return getMajMinFromVersion(jobVersion) === newMajMinVersion;
            } catch {
              return false;
            }
          })
        );
      } catch {}
    }
  };

  const resetState = () => {
    setSelectedP3dJobs([]);
    setInputType();
    updateAnalysisParams(getDefaultAnalysisParams());
    setFormState(FORM_STATES.RESET);
  };

  const handleSubmission = async () => {
    if (!enableSubmitBtn) {
      return;
    }
    setFormState(FORM_STATES.SUBMITTING);

    try {
      await submitAdvAnalysisJob(inputType, analysisParams, selectedP3dJobs);
    } catch {
      setFormState(FORM_STATES.SUBMISSION_FAILED);
      return;
    }
    resetState();
    setFormState(FORM_STATES.SUBMISSION_SUCCESSFUL);
  };

  const onSelectInputChange = (e, value) => {
    if (e == null || e.type !== "change" || value == null || value === "") {
      return;
    }
    setLoadingAvailableP3dJobs(true);
    clearTimeout(pollAvailableP3dJobsTimeout);
    const newPollAvailableInputsTimeout = setTimeout(async () => {
      try {
        const newAvailableP3dJobs = (await pollP3dJobs(value, inputType, versionMajMin)).filter(
          (retrievedJob) => {
            return !isJobAlreadySelected(retrievedJob);
          }
        );
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
                reset={[FORM_STATES.RESET, FORM_STATES.SUBMISSION_SUCCESSFUL].includes(formState)}
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
                label={inputLimitReached ? "Maximum Input Limit Reached" : "Select Inputs"}
                options={availableP3dJobs.map((j) => `${j.filename} (${formatDateTime(j.created_at)})`)}
                handleSelection={handleInputDropDownSelect}
                reset={
                  [FORM_STATES.RESET, FORM_STATES.SUBMISSION_SUCCESSFUL].includes(formState) ||
                  availableP3dJobs.length === 0 ||
                  inputLimitReached
                }
                width={500}
                disabled={formState === FORM_STATES.SUBMITTING || inputType == null || inputLimitReached}
                onInputChange={onSelectInputChange}
                loading={loadingAvailableP3dJobs}
              />
            </div>
          </DropDownContainer>
        </InputSelectionContainer>
        <SectionHeader>
          <b>{`Selected Inputs (${formattedJobSelection?.length || 0}/${MAX_NUM_INPUTS})`}</b>
        </SectionHeader>
        <InputSelectionTableContainer>
          <InputSelectionTable
            formattedJobSelection={formattedJobSelection}
            removeInputsFromSelection={removeInputsFromSelection}
          />
        </InputSelectionTableContainer>

        <SectionHeader style={{ marginTop: "50px" }}>
          <b>Analysis Options</b>
        </SectionHeader>
        <LongitudinalAnalysisParamsContainer>
          <LongitudinalAnalysisParams
            analysisParams={analysisParams}
            updateParams={updateAnalysisParams}
            errorMessages={analysisParamErrors}
          />
        </LongitudinalAnalysisParamsContainer>
        <ButtonContainer>
          {formState === FORM_STATES.SUBMISSION_SUCCESSFUL && (
            <SuccessText>Submission Successful!</SuccessText>
          )}
          {formState === FORM_STATES.SUBMISSION_FAILED && <ErrorText>Error Submitting Analysis</ErrorText>}
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
                      {label}: {getSortedWellListStr(wells)}
                    </div>
                  );
                });
          const color = name === "None" ? "red" : "black";
          return (
            <Tooltip title={<span style={{ fontSize: "15px" }}>{tooltipText}</span>}>
              <div style={{ color }}>{name}</div>
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
        Cell: ({ cell }) => {
          const val = cell.getValue();
          const color = val === "None" ? "red" : "black";
          return <div style={{ color }}>{val}</div>;
        },
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
      defaultSortDesc={false}
      rowSelection={checkedRows}
      setRowSelection={setCheckedRows}
      toolbarFn={actionsFn}
      enablePagination={false}
      showColumnFilters={false}
    />
  );
}

function LongitudinalAnalysisParams({ analysisParams, updateParams, errorMessages }) {
  return (
    <div>
      <AnalysisParamContainer
        label="Analysis Title"
        name="analysisTitle"
        tooltipText="Specifies the name of the output file."
        additionaErrorStyle={{ width: "150%" }}
        placeholder="Analysis Title"
        value={analysisParams.analysisTitle}
        changeFn={(e) => {
          updateParams({
            analysisTitle: e.target.value,
          });
        }}
        errorMsg={errorMessages.analysisTitle}
      />
      <AnalysisParamContainer
        label="Experiment Start Date"
        name="experimentStartDate"
        tooltipText="Specifies the start date and hour of the experiment. This is used to determine how many days into the experiment each recording was taken."
        additionaErrorStyle={{ width: "150%" }}
        placeholder="YYYY-MM-DD_HH"
        value={analysisParams.experimentStartDate}
        changeFn={(e) => {
          updateParams({
            experimentStartDate: e.target.value,
          });
        }}
        errorMsg={errorMessages.experimentStartDate}
      />
    </div>
  );
}
