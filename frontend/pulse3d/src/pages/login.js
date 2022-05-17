import LoginForm from '@/components/LoginForm';
import styled from 'styled-components';

const LoginContainer = styled.div`
  position: relative;
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100vh;
`;

export default function Login() {
    
  return (
    <LoginContainer>
      <LoginForm />
    </LoginContainer>
  );
}
