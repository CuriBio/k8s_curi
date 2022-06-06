import ControlPanel from "@/components/ControlPanel";
import styled from "styled-components";

const Container = styled.div`
  height: inherit;
  width: inherit;
  background-color: var(--light-gray);
  display: flex;
`;

export default function DashboardLayout({ children }) {
  return (
    <Container>
      <ControlPanel />
      {children}
    </Container>
  );
}
