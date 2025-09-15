import styled from "styled-components";
import FormInput from "@/components/basicWidgets/FormInput";
import AddCircleOutlineIcon from "@mui/icons-material/AddCircleOutline";
import RemoveCircleOutlineIcon from "@mui/icons-material/RemoveCircleOutline";
import Tooltip from "@mui/material/Tooltip";
import InfoOutlinedIcon from "@mui/icons-material/InfoOutlined";

const WindowBoundsContainer = styled.div`
  display: grid;
  grid-template-columns: 49% 49% 2%;
  height: 70px;
  justify-items: center;
  padding: 15px 0 10px 0;
  width: 400px;
`;

const LabelContainer = styled.div`
  display: grid;
  grid-template-columns: 50% 50%;
  padding-left: 21px;
  width: 420px;
`;

const Label = styled.label`
  position: relative;
  height: 25px;
  padding: 10px;
  border-radius: 5px;
  display: flex;
  justify-content: left;
  padding-right: 3%;
  white-space: nowrap;
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

export default function AnalysisWindows({ analysisParams, updateParams, errorMsgs }) {
  const addWindow = () => {
    const updatedWindows = [...analysisParams.windows];
    updatedWindows.push({ start: "", end: "" });
    updateParams({ windows: updatedWindows });
  };

  const updateWindows = (value, key, windowIdxToEdit) => {
    const updatedWindows = [...analysisParams.windows];
    if (windowIdxToEdit < updatedWindows.length) {
      updatedWindows[windowIdxToEdit][key] = value;
    }
    updateParams({ windows: updatedWindows });
  };

  const removeWindow = (idx) => {
    const updatedWindows = [...analysisParams.windows];
    updatedWindows.splice(idx, 1);
    updateParams({ windows: updatedWindows });
  };

  return (
    <>
      <SectionLabel>
        {"Windowed Analysis "}
        <Tooltip
          title={
            <TooltipText>
              {
                "Specify analysis windows to use. Each window will be run in its own analysis. Multiple credits may be consumed, up to 1 per file per window"
              }
            </TooltipText>
          }
          placement={"top"}
        >
          <InfoOutlinedIcon sx={{ marginLeft: "5px", fontSize: 20 }} />
        </Tooltip>
        <Tooltip title={<TooltipText>{"Remove Final Window"}</TooltipText>} placement={"top"}>
          <RemoveCircleOutlineIcon
            sx={{ cursor: "pointer", marginLeft: "15px", "&:hover": { color: "var(--teal-green)" } }}
            onClick={() => removeWindow(analysisParams.windows.length - 1)}
          />
        </Tooltip>
        <Tooltip title={<TooltipText>{"Add Window"}</TooltipText>} placement={"top"}>
          <AddCircleOutlineIcon
            sx={{ cursor: "pointer", marginLeft: "5px", "&:hover": { color: "var(--teal-green)" } }}
            onClick={addWindow}
          />
        </Tooltip>
      </SectionLabel>

      {analysisParams.windows.length === 0 && <EmptyText>Click the plus to add a window</EmptyText>}
      {analysisParams.windows.length > 0 && (
        <LabelContainer>
          <Label htmlFor={"windowStart"} style={{}}>
            Start Time (s):
            <Tooltip
              title={
                <TooltipText>
                  {"Specifies the earliest timepoint (in seconds) to use in analysis."}
                </TooltipText>
              }
            >
              <InfoOutlinedIcon sx={{ marginLeft: "5px", fontSize: 20 }} />
            </Tooltip>
          </Label>
          <Label htmlFor={"windowEnd"} style={{}}>
            End Time (s):
            <Tooltip
              title={
                <TooltipText>{"Specifies the latest timepoint (in seconds) to use in analysis."}</TooltipText>
              }
            >
              <InfoOutlinedIcon sx={{ marginLeft: "5px", fontSize: 20 }} />
            </Tooltip>
          </Label>
        </LabelContainer>
      )}
      {analysisParams.windows.map(({ start, end }, i) => (
        <WindowBoundsContainer key={i}>
          <InputErrorContainer>
            <FormInput
              name="windowStart"
              placeholder={"0"}
              value={start}
              onChangeFn={(e) => {
                updateWindows(e.target.value.trim(), "start", i);
              }}
            >
              <ErrorText id="windowStartError" role="errorMsg">
                {errorMsgs?.[i]?.start || ""}
              </ErrorText>
            </FormInput>
          </InputErrorContainer>
          <InputErrorContainer>
            <FormInput
              name="windowEnd"
              placeholder={"End"}
              value={end}
              onChangeFn={(e) => {
                updateWindows(e.target.value.trim(), "end", i);
              }}
            >
              <ErrorText id="windowEndError" role="errorMsg">
                {errorMsgs?.[i]?.end || ""}
              </ErrorText>
            </FormInput>
          </InputErrorContainer>
          <div style={{ position: "relative" }}>
            <Tooltip title={<TooltipText>{"Remove Window"}</TooltipText>} placement={"top"}>
              <RemoveCircleOutlineIcon
                sx={{
                  cursor: "pointer",
                  position: "absolute",
                  left: "-40px",
                  marginTop: "5px",
                  "&:hover": { color: "var(--teal-green)" },
                }}
                onClick={() => removeWindow(i)}
              />
            </Tooltip>
          </div>
        </WindowBoundsContainer>
      ))}
    </>
  );
}
