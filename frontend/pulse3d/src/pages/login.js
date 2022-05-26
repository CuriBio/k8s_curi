import styled from 'styled-components';
import { useRouter } from 'next/router';
import { useWorker } from '@/components/hooks/useWorker';
import { useEffect, useState } from 'react';

// TODO eventually need to find a better to way to handle some of these globally to use across app
const BackgroundContainer = styled.div`
  position: relative;
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100vh;
`;

const ModalContainer = styled.div`
  height: 400px;
  width: 450px;
  background-color: var(--light-gray);
  position: relative;
  border-radius: 3%;
  overflow: hidden;
`;

const InputContainer = styled.div`
  height: 85%;
  position: relative;
  display: flex;
  flex-direction: column;
  justify-content: space-evenly;
  align-items: center;
  padding: 5%;
  width: inherit;
`;

const Form = styled.form`
  height: inherit;
  position: relative;
  display: flex;
  flex-direction: column;
  width: inherit;
`;

const formStyle = [
  `
  position: relative;
  width: 80%;
  height: 40px;
  padding: 5px;
`,
];

const Field = styled.input(formStyle);

const Label = styled.label(formStyle);

const ErrorText = styled.span`
  color: red;
  font-style: italic;
  text-align: left;
  position: relative;
  width: 80%;
  padding-top: 2%;
`;

export default function Login() {
  const router = useRouter();
  const [state, setState] = useState({});
  const { error, result } = useWorker(state);
  const [errorMsg, setErrorMsg] = useState(null);
  const [userData, setUserData] = useState({
    customer_id: '',
    username: '',
    password: '',
  });

  useEffect(() => {
    // handles web workers request error if credentials error
    // TODO once more requests are added, we'll need to add a response differentiator so these don't respond to all web worker requests
    if (error)
      error === 401 || error === 422 // 422 gets returned if specific input is not of UUID type
        ? setErrorMsg('*Invalid credentials. Try again.')
        : setErrorMsg('*Internal error. Please try again later.');
    else if (result && result.status === 200) {
      router.push('/dashboard');
      setErrorMsg('');
    }
    setUserData({
      customer_id: '',
      username: '',
      password: '',
    });
  }, [error, result]);

  const submitForm = async (e) => {
    e.preventDefault(); // required for default functions to prevent resetting form

    if ([userData.username, userData.password].includes(''))
      setErrorMsg('*Username and password are required');
    // this state gets passed to web worker to attempt login request
    else {
      setState({
        method: 'POST',
        endpoint: '/users/login',
        body: userData,
      });
    }
  };

  return (
    <BackgroundContainer>
      <ModalContainer>
        <Form onSubmit={submitForm}>
          <InputContainer>
            <Label htmlFor='customer_id'>Customer ID</Label>
            <Field
              id='customer_id' // must be snakecase to post to backend
              placeholder='CuriBio'
              onChange={(e) =>
                setUserData({ ...userData, customer_id: e.target.value })
              }
            />
            <Label htmlFor='username'>Username</Label>
            <Field
              id='username'
              placeholder='User'
              onChange={(e) =>
                setUserData({ ...userData, username: e.target.value })
              }
            />
            <Label htmlFor='password'>Password</Label>
            <Field
              id='password'
              type='password'
              placeholder='Password'
              autoComplete='password' // chrome warns without this attribute
              onChange={(e) =>
                setUserData({ ...userData, password: e.target.value })
              }
            />
            <ErrorText id='loginError' role='errorMsg'>
              {errorMsg}
            </ErrorText>
          </InputContainer>
          <button type='submit'>Submit</button>
        </Form>
      </ModalContainer>
    </BackgroundContainer>
  );
}
