import styled from 'styled-components';
import { Formik } from 'formik';
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

  const values = {
    customer_id: '',
    username: '',
    password: '',
  };

  useEffect(() => console.log(result, error), [result, error]);

  const handleSubmit = async (inputs, { setErrors }) => {
    try {
      setState({
        method: 'POST',
        endpoint: '/users/login',
        body: JSON.stringify(inputs),
      });
    } catch (e) {
      e.response && e.response.status === 401
        ? setErrors({ message: '*Invalid credentials' })
        : setErrors({ message: '*Internal error. Please try again later.' });
    }
  };

  const validate = (inputs) => {
    return !inputs.customer_id || !inputs.username || !inputs.password
      ? { message: '*All fields are required' }
      : {};
  };

  return (
    <BackgroundContainer>
      <Formik
        initialValues={values}
        onSubmit={handleSubmit}
        validate={validate}
      >
        {(formik) => {
          const {
            values,
            handleChange,
            handleSubmit,
            errors,
            touched,
            handleBlur,
            isValid,
            dirty,
          } = formik;
          return (
            <Form onSubmit={handleSubmit}>
              <InputContainer>
                <Label htmlFor="customer_id">Customer ID</Label>
                <Field
                  id="customer_id"
                  name="customer_id"
                  placeholder="CuriBio"
                  value={values.customer_id}
                  onChange={handleChange}
                />

                <Label htmlFor="username">Username</Label>
                <Field
                  id="username"
                  name="username"
                  placeholder="User"
                  value={values.username}
                  onChange={handleChange}
                />

                <Label htmlFor="password">Password</Label>
                <Field
                  id="password"
                  name="password"
                  type="password"
                  placeholder="Password"
                  value={values.password}
                  onChange={handleChange}
                />
                {errors.message ? (
                  <ErrorText>{errors.message}</ErrorText>
                ) : null}
              </InputContainer>
              <Button type="submit">Submit</Button>
            </Form>
          );
        }}
      </Formik>
    </BackgroundContainer>
  );
}
