import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import UploadsTable from '../../components/UploadsTable';
import * as hooks from '../../components/hooks/useWorker';
import '@testing-library/jest-dom';

describe('Dashboard', () => {
  it('renders progress spinner while loading user data', () => {
    render(<UploadsTable />);

    const targetContainer = document.querySelector('#spinnerContainer');
    expect(targetContainer).toBeInTheDocument();
  });

  it('renders progress spinner while loading user data', () => {
    render(<UploadsTable />);

    expect(testWorker).toBeCalledWith();
  });
});
