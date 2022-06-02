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

export default function AnalysisParamForm() {
  return (
    <Container>
      <ParamNameContainer>
        <Label htmlFor="twitch_widths">Twitch Widths:</Label>
        <Label htmlFor="start_time">Start Time (s):</Label>
        <Label htmlFor="end_time">End Time (s):</Label>
      </ParamNameContainer>
      <InputContainer>
        <Field
          id="twitch_widths" // must be snakecase to post to backend
          placeholder="[50, 90]"
          // onChange={(e) => {
          //   setUserData({
          //     ...userData,
          //     twitch_widths: e.target.value,
          //   });
          // }}
        />
        <Field
          id="start_time" // must be snakecase to post to backend
          placeholder="0"
        />
        <Field
          id="end_time" // must be snakecase to post to backend
          placeholder="30"
        />
      </InputContainer>
    </Container>
  );
}
