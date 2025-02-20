import styled from "styled-components";
import { loadCsvInputToArray, isArrayOfWellNames } from "../../utils/generic";
import FormInput from "@/components/basicWidgets/FormInput";
import AddCircleOutlineIcon from "@mui/icons-material/AddCircleOutline";
import RemoveCircleOutlineIcon from "@mui/icons-material/RemoveCircleOutline";
import Tooltip from "@mui/material/Tooltip";
import { useEffect, useState } from "react";

const WellGroupingContainer = styled.div`
  display: grid;
  grid-template-columns: 50% 50%;
  height: 70px;
  justify-items: center;
  padding: 15px 0 10px 0;
  width: 400px;
`;

const ErrorText = styled.span`
  color: red;
  font-style: italic;
  text-align: left;
  position: relative;
  width: 150%;
  font-size: 13px;
`;

const InputErrorContainer = styled.div`
  display: flex;
  flex-direction: column;
  width: 70%;
  height: 60px;
`;

const SectionLabel = styled.span`
  display: flex;
  align-items: center;
  font-size: 20px;
  position: relative;
  font-weight: bolder;
  margin-top: 20px;
`;

const TooltipText = styled.span`
  font-size: 15px;
`;

const EmptyText = styled.div`
  color: var(--dark-gray);
  font-size: 16px;
  margin: 10px;
`;

const VALID_REGEX = new RegExp("^[0-9A-Za-z ./_-]+$");

export default function PlatemapOverride({
  requirePlatemapName,
  setAnalysisParams,
  analysisParams,
  setWellGroupErr,
  platemapNameError,
  setPlatemapNameError,
  presetLoadTime,
}) {
  const [errorMsgs, setErrorMsgs] = useState([]);
  const [localGroups, setLocalGroups] = useState([]);

  const sectionHeader = requirePlatemapName ? "Plate Map" : "Well Groupings";

  // this use effect is only to update local groups after a preset is loaded
  useEffect(() => {
    if (presetLoadTime != null) {
      localGroups.length = 0;
      errorMsgs.length = 0;
      for (const [name, wellsArr] of Object.entries(analysisParams.wellGroups || {})) {
        localGroups.push({ name, wells: wellsArr.join(",") });
        errorMsgs.push({ name: "", wells: "" });
      }
      setLocalGroups(localGroups);
      setErrorMsgs(errorMsgs);
    }
  }, [presetLoadTime]);

  useEffect(() => {
    let wellGroupsUpdate = {};
    let errExists = false;
    for (const [idx, { name, wells }] of localGroups.entries()) {
      const nameErrMsg = validateGroupName(name);
      const { wellErrMsg, formattedWellNames } = validateWellNames(wells);
      errorMsgs[idx].name = nameErrMsg;
      errorMsgs[idx].wells = wellErrMsg;
      wellGroupsUpdate[name] = formattedWellNames;
      if (errorMsgs[idx].name.length !== 0 || errorMsgs[idx].wells.length !== 0) {
        errExists = true;
      }
    }

    const updatedAnalysisParams = { ...analysisParams, wellGroups: wellGroupsUpdate };
    // pass error state up to parent to enable or disable submit button
    setWellGroupErr(errExists);
    setErrorMsgs([...errorMsgs]);

    if (requirePlatemapName) {
      if (localGroups.length === 0) {
        updatedAnalysisParams.platemapName = "";
        setPlatemapNameError("");
      } else if (analysisParams.platemapName === "") {
        setPlatemapNameError("*Required");
      } else {
        const errMsg = VALID_REGEX.test(analysisParams.platemapName) ? "" : "*Invalid character present.";
        setPlatemapNameError(errMsg);
      }
    } else {
      updatedAnalysisParams.platemapName = "";
      setPlatemapNameError("");
    }

    setAnalysisParams(updatedAnalysisParams);
  }, [localGroups, analysisParams.platemapName, requirePlatemapName]);

  useEffect(() => {
    // reset well groups after reset or submit buttons are selected
    const { wellGroups } = analysisParams;
    if (Object.keys(wellGroups).length === 0 && localGroups.length !== 0) {
      setLocalGroups([]);
    }
  }, [analysisParams]);

  const updatePlatemapName = (newName) => {
    setAnalysisParams({ ...analysisParams, platemapName: newName });
  };

  const addWellGroup = () => {
    localGroups.push({ name: "", wells: "" });
    errorMsgs.push({ name: "*Required", wells: "*Required" });

    // spread operator important here to trigger change in localGroups and errorMsgs
    setLocalGroups([...localGroups]);
    setErrorMsgs([...errorMsgs]);
  };

  const validateGroupName = (name) => {
    let feedback = "";
    if (name.length > 0) {
      if (!VALID_REGEX.test(name)) {
        feedback = "*Invalid character present.";
      } else if (localGroups.filter((group) => group.name.toLowerCase() === name.toLowerCase()).length > 1) {
        feedback = "*This name already exists";
      }
    } else {
      feedback = "*Required";
    }
    return feedback;
  };

  const updateGroupName = (newName, groupIdxToEdit) => {
    const existingGroups = JSON.parse(JSON.stringify(localGroups));

    if (groupIdxToEdit < existingGroups.length) {
      // assign new name with wells then delete old name from state
      const newGroup = {
        name: newName,
        wells: existingGroups[groupIdxToEdit].wells,
      };
      existingGroups.splice(groupIdxToEdit, 1, newGroup);
    }

    setLocalGroups(existingGroups);
  };

  const updateWellGroups = (wells, groupIdxToEdit) => {
    const existingGroups = JSON.parse(JSON.stringify(localGroups));
    // validate names are accepted well names and return as array instead of string
    if (groupIdxToEdit < existingGroups.length) {
      existingGroups[groupIdxToEdit].wells = wells;
    }

    // make sure name has been enteres first
    setLocalGroups(existingGroups);
  };

  const validateWellNames = (wells) => {
    let formattedWellNames = "",
      wellErrMsg = "";

    if (wells && wells.length > 0) {
      // load into an array
      let wellNameArr = loadCsvInputToArray(wells);
      // make sure it's an array of valid well names
      if (isArrayOfWellNames(wellNameArr)) {
        formattedWellNames = Array.from(new Set(wellNameArr));
      } else {
        wellErrMsg = "*Must be comma-separated Well Names (i.e. A1, D6)";
      }
    } else {
      wellErrMsg = "*Required";
    }

    return { wellErrMsg, formattedWellNames };
  };

  const removeWellGroup = () => {
    localGroups.pop();
    setLocalGroups([...localGroups]);
  };

  return (
    <>
      <SectionLabel>
        {sectionHeader + " "}
        <Tooltip title={<TooltipText>{"Remove Label"}</TooltipText>} placement={"top"}>
          <RemoveCircleOutlineIcon
            sx={{ cursor: "pointer", marginLeft: "15px", "&:hover": { color: "var(--teal-green)" } }}
            onClick={removeWellGroup}
          />
        </Tooltip>
        <Tooltip title={<TooltipText>{"Add Label"}</TooltipText>} placement={"top"}>
          <AddCircleOutlineIcon
            sx={{ cursor: "pointer", marginLeft: "5px", "&:hover": { color: "var(--teal-green)" } }}
            onClick={addWellGroup}
          />
        </Tooltip>
      </SectionLabel>

      {localGroups.length === 0 ? (
        <EmptyText>Click the plus to add a group</EmptyText>
      ) : (
        requirePlatemapName && (
          <WellGroupingContainer key="name">
            <InputErrorContainer>
              <FormInput
                name="platemapName"
                placeholder={"Plate Map Name"}
                value={analysisParams.platemapName}
                onChangeFn={(e) => {
                  updatePlatemapName(e.target.value.trim());
                }}
              >
                <ErrorText id="platemapNameError" role="errorMsg">
                  {platemapNameError}
                </ErrorText>
              </FormInput>
            </InputErrorContainer>
          </WellGroupingContainer>
        )
      )}
      {localGroups.map(({ name, wells }, i) => (
        <WellGroupingContainer key={i}>
          <InputErrorContainer>
            <FormInput
              name="groupLabel"
              placeholder={"Label Name"}
              value={name}
              onChangeFn={(e) => {
                updateGroupName(e.target.value.trim(), i);
              }}
            >
              <ErrorText id="labelNameError" role="errorMsg">
                {errorMsgs[i].name}
              </ErrorText>
            </FormInput>
          </InputErrorContainer>
          <InputErrorContainer>
            <FormInput
              name="wells"
              placeholder={"A1, B2, C3"}
              value={wells}
              onChangeFn={(e) => {
                updateWellGroups(e.target.value.trim(), i);
              }}
            >
              <ErrorText id="wellsError" role="errorMsg">
                {errorMsgs[i].wells}
              </ErrorText>
            </FormInput>
          </InputErrorContainer>
        </WellGroupingContainer>
      ))}
    </>
  );
}
