import styled from "styled-components";
import FormInput from "../basicWidgets/FormInput";

const InputContainer = styled.div(
  ({ user }) => `
  height: ${user ? "74%" : "69%"};
  position: relative;
  display: flex;
  flex-direction: column;
  justify-content: space-evenly;
  align-items: center;
  padding: 5%;
  width: inherit;
`
);

export default function LoginForm({
  children,
  setUserData,
  userData,
  loginType,
}) {
  return (
    <InputContainer user={loginType === "User"}>
      {loginType === "User" ? (
        <>
          <FormInput
            name="customer_id"
            label="Customer ID"
            placeholder="CuriBio"
            value={userData.customer_id}
            onChangeFn={(e) => {
              setUserData({
                ...userData,
                customer_id: e.target.value,
              });
            }}
          />
          <FormInput
            name="username"
            label="Username"
            placeholder="user"
            value={userData.username}
            onChangeFn={(e) => {
              setUserData({
                ...userData,
                username: e.target.value,
              });
            }}
          />
        </>
      ) : (
        <>
          <FormInput
            name="email"
            label="Email"
            placeholder="user@curibio.com"
            value={userData.email}
            onChangeFn={(e) => {
              setUserData({
                ...userData,
                email: e.target.value,
              });
            }}
          />
        </>
      )}
      <FormInput
        name="password"
        label="Password"
        placeholder="Password"
        value={userData.password}
        type="password"
        onChangeFn={(e) => {
          setUserData({
            ...userData,
            password: e.target.value,
          });
        }}
      />

      {children}
    </InputContainer>
  );
}
