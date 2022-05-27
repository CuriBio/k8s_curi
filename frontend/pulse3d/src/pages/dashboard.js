import ControlPanel from '@/components/ControlPanel';
import UploadsTable from '@/components/UploadsTable';
import styled from 'styled-components';
import { useWorker } from '@/components/hooks/useWorker';
import { useEffect } from 'react';
import Router from 'next/router';

const Container = styled.div`
  height: inherit;
  width: inherit;
  background-color: var(--light-gray);
  display: flex;
`;

export default function Dashboard() {
  return (
    <Container>
      <ControlPanel />
      <UploadsTable />
    </Container>
  );
}
