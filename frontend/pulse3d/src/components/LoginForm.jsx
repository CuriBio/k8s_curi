import styled from 'styled-components';
import { useForm } from 'react-hook-form';
import axios from 'axios';
import { useRouter } from 'next/router';
import { useWorker } from './hooks/useWorker';
import { useEffect, useState } from 'react';

const BackgroundContainer = styled.div`
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

const Button = styled.button`
  position: absolute;
  width: inherit;
  height: 15%;
  background-color: var(--dark-blue);
  color: var(--light-gray);
  bottom: 0px;
  border-radius: 3%;
  font-size: inherit;
  cursor: pointer;
  border: none;
  &:hover {
    background-color: var(--teal-green);
  }
`;

const ErrorText = styled.span`
  color: red;
  font-style: italic;
  text-align: left;
  position: relative;
  width: 80%;
  padding-top: 2%;
`;

export default function LoginForm() {
  const router = useRouter();
  const [state, setState] = useState({});
  const { result, error } = useWorker(state);
  const [errorMsg, setErrorMsg] = useState(null);

  const {
    register,
    handleSubmit,
    trigger,
    formState: { errors },
  } = useForm();

  //   useEffect(() => console.log(result, error), [result, error]);

  const submitForm = async (inputs) => {
    if (Object.values(inputs).includes(''))
      setErrorMsg('*All fields are required');
    else {
      try {
        //   setState({
        //     method: 'POST',
        //     endpoint: '/users/login',
        //     body: JSON.stringify(inputs),
        //   });
        // router.append('/dashboard');
        setErrorMsg('');
      } catch (e) {
        e.response && e.response.status === 401
          ? setErrorMsg('*Invalid credentials')
          : setErrorMsg('*Internal error. Please try again later.');
      }
    }
  };

  return (
    <BackgroundContainer>
      <Form onSubmit={handleSubmit(submitForm)}>
        <InputContainer>
          <Label htmlFor="customer_id">Customer ID</Label>
          <Field
            id="customer_id"
            placeholder="CuriBio"
            {...register('customer_id')}
          />

          <Label htmlFor="username">Username</Label>
          <Field id="username" placeholder="User" {...register('username')} />

          <Label htmlFor="password">Password</Label>
          <Field
            id="password"
            type="password"
            placeholder="Password"
            {...register('password')}
          />
          <ErrorText>{errorMsg}</ErrorText>
        </InputContainer>
        <Button type="submit">Submit</Button>
      </Form>
    </BackgroundContainer>
  );
}
