import ControlPanel from "@/components/ControlPanel";
import styled from "styled-components";

const Container = styled.div`
  height: inherit;
  width: inherit;
  background-color: var(--light-gray);
`;

export default function Dashboard() {
  return (
    <Container>
      <ControlPanel />
    </Container>
  );
}
