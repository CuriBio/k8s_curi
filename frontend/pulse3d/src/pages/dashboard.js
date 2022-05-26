import ControlPanel from '@/components/ControlPanel';
import styled from 'styled-components';

const Container = styled.div`
  height: inherit;
  width: inherit;
  background-color: var(--light-gray);
`;

// TODO when creating this page, we'll need to add staticProps to prevent users from adding extension to redirect to page without logging in
export default function Dashboard() {
  return (
    <Container>
      <ControlPanel />
    </Container>
  );
}
