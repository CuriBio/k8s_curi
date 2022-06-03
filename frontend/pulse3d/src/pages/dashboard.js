import ControlPanel from '@/components/ControlPanel';
import UploadsTable from '@/components/UploadsTable';
import styled from 'styled-components';

const Container = styled.div`
  height: inherit;
  width: inherit;
  background-color: var(--light-gray);
  display: flex;
`;

export default function Dashboard({ makeRequest, response }) {
  return (
    <Container>
      <ControlPanel />
      <UploadsTable makeRequest={makeRequest} response={response} />
    </Container>
  );
}
