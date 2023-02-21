import styled from "styled-components";
import { loadCsvInputToArray, isArrayOfWellNames } from "../../utils/generic";
import FormInput from "../basicWidgets/FormInput";
import AddCircleOutlineIcon from "@mui/icons-material/AddCircleOutline";
import Tooltip from "@mui/material/Tooltip";
import { useEffect, useState } from "react";

const WellGroupingContainer = styled.div`
  display: grid;
  grid-template-columns: 45% 45% 10%;
  height: 70px;
  justify-items: center;
  padding: 15px 0 10px 0;
  height: 70px;
  width: 400px;
`;

const ErrorText = styled.span`
  color: red;
  font-style: italic;
  text-align: left;
  position: relative;
  width: 150%;
  font-size: 13px;
  white-space: nowrap;
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

export default function AnalysisParamForm({ setAnalysisParams, analysisParams }) {
  const [errorMsgs, setErrorMsgs] = useState([]);
  const [numOfInputs, setNumOfInputs] = useState(1);
  const [localGroups, setLocalGroups] = useState([]);

  const updateGroupName = (newName, groupIdxToEdit) => {
    const existingGroups = JSON.parse(JSON.stringify(localGroups));

    // const valid_regex = new RegExp("^[0-9A-Za-z _-]+$");
    // if (!text || text.length === 0) feedback = "Required";
    // else if (!valid_regex.test(text))
    console.log(groupIdxToEdit, existingGroups.length);
    if (groupIdxToEdit < existingGroups.length) {
      // assign new name with wells then delete old name from state
      const newGroup = {
        name: newName,
        wells: existingGroups[groupIdxToEdit].wells,
      };
      existingGroups.splice(groupIdxToEdit, 1, newGroup);
    } else {
      while (groupIdxToEdit > existingGroups.length) {
        existingGroups.push({ name: "", wells: [] });
        groupIdxToEdit++;
      }
      existingGroups.push({ name: newName, wells: [] });

      //   errorMsgs.push({ name: "", wells: "Required" });
    }

    setLocalGroups(existingGroups);
  };

  useEffect(() => {
    console.log("ANALYSIS PARAMS: ", JSON.stringify(localGroups));
  }, [localGroups]);
  useEffect(() => {
    console.log("ERR MESSAGES: ", JSON.stringify(errorMsgs));
  }, [errorMsgs]);

  const updateWellGroups = (wells, groupIdxToEdit) => {
    const existingGroups = JSON.parse(JSON.stringify(localGroups));
    // validate names are accepted well names and return as array instead of string
    // const { errorMsg, formattedWellNames } = validateWellNames(wells);
    console.log(groupIdxToEdit, existingGroups.length);
    if (groupIdxToEdit < existingGroups.length) existingGroups[groupIdxToEdit].wells = wells;
    else {
      existingGroups.push({ name: "", wells });
    }
    // make sure name has been enteres first
    setLocalGroups(existingGroups);
  };

  const validateWellNames = (wells) => {
    let formattedWellNames, errorMsg;
    if (wells === null || wells === "") {
      formattedWellNames = "";
    } else {
      // load into an array
      let wellNameArr = loadCsvInputToArray(wells);
      // make sure it's an array of valid well names
      if (isArrayOfWellNames(wellNameArr, true)) {
        formattedWellNames = Array.from(new Set(wellNameArr));
        errorMsg = "";
      } else {
        errorMsg = "*Must be comma-separated Well Names (i.e. A1, D6)";
      }
    }

    return { errorMsg, formattedWellNames };
  };

  return (
    <>
      <SectionLabel>Well Groupings</SectionLabel>
      {[...Array(numOfInputs).keys()].map((i) => {
        const groupNames = localGroups.map(({ name }) => name);
        const noGroupsAssigned = localGroups.length === 0;
        const groupName = !noGroupsAssigned ? groupNames[i] : null;

        return (
          <WellGroupingContainer key={i}>
            <InputErrorContainer>
              <FormInput
                name="groupLabel"
                placeholder={"Name"}
                value={noGroupsAssigned ? "" : groupName}
                onChangeFn={(e) => {
                  updateGroupName(e.target.value, i);
                }}
              >
                <ErrorText id="labelNameError" role="errorMsg">
                  {/* {errorMessages.baseToPeak} */}
                </ErrorText>
              </FormInput>
            </InputErrorContainer>
            <InputErrorContainer>
              <FormInput
                name="wells"
                placeholder={"A1, B2, C3"}
                value={noGroupsAssigned ? "" : localGroups[i].wells}
                onChangeFn={(e) => {
                  updateWellGroups(e.target.value, i);
                }}
              >
                <ErrorText id="wellsError" role="errorMsg">
                  {/* {errorMessages.baseToPeak} */}
                </ErrorText>
              </FormInput>
            </InputErrorContainer>
            {i === groupNames.length && (
              <Tooltip title={<TooltipText>{"Add Label"}</TooltipText>} placement={"top"}>
                <AddCircleOutlineIcon
                  sx={{ cursor: "pointer", marginTop: "10px" }}
                  onClick={() => setNumOfInputs(numOfInputs++)}
                />
              </Tooltip>
            )}
          </WellGroupingContainer>
        );
      })}
    </>
  );
}
