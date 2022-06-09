import styled from "styled-components";

const Container = styled.div`
  left: 5%;
  top: 15%;
  padding-left: 5%;
  height: 55%;
  width: 90%;
  position: relative;
  display: flex;
  flex-direction: row;
  border: solid;
  border-color: var(--dark-gray);
  border-width: 2px;
  border-radius: 7px;
  background-color: var(--med-gray);
`;

const ParamNameContainer = styled.div`
  display: flex;
  flex-direction: column;
  justify-content: space-evenly;
`;

const InputContainer = styled.div`
  padding-left: 5%;
  display: flex;
  flex-direction: column;
  justify-content: space-evenly;
  width: 80%;
`;

const formStyle = [
  `
  width: 100%;
  position: relative;
  height: 40px;
  padding: 5px;
  border-radius: 5px;
`,
];

const Field = styled.input(formStyle);

const Label = styled.label(formStyle);

export default function AnalysisParamForm({ updateAnalysisParams }) {
  return (
    <Container>
      <ParamNameContainer>
        <Label htmlFor="twitchWidths">Twitch Widths (%):</Label>
        <Label htmlFor="startTime">Start Time (s):</Label>
        <Label htmlFor="endTime">End Time (s):</Label>
      </ParamNameContainer>
      <InputContainer>
        <Field
          id="twitchWidths"
          placeholder="50, 90"
          onChange={(e) => {
            updateAnalysisParams({ twitchWidths: `[${e.target.value}]` });
          }}
        />
        <Field
          id="startTime"
          placeholder="0"
          onChange={(e) => {
            updateAnalysisParams({
              startTime: e.target.value,
            });
          }}
        />
        <Field
          id="endTime"
          placeholder="30"
          onChange={(e) => {
            updateAnalysisParams({
              endTime: e.target.value,
            });
          }}
        />
      </InputContainer>
    </Container>
  );
}
