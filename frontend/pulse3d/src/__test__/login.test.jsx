import { render, screen } from '@testing-library/react';
import Login from '../pages/login';
import '@testing-library/jest-dom';

describe('Login', () => {
  it('renders a login form with input fields', () => {
    render(<Login />);

    const cust_input_field = document.querySelector('#customer_id');
    const user_input_field = document.querySelector('#username');
    const pw_input_field = document.querySelector('#password');
    
    expect(cust_input_field).toBeInTheDocument();
    expect(user_input_field).toBeInTheDocument();
    expect(pw_input_field).toBeInTheDocument();
  });
});
