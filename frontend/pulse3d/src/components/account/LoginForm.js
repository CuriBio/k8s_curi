import styled from "styled-components";

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

const formStyle = [
  `
  position: relative;
  width: 80%;
  height: 40px;
  padding: 5px;
  line-height: 2;
`,
];

const Field = styled.input(formStyle);

const Label = styled.label(formStyle);

export default function LoginForm({
  children,
  setUserData,
  userData,
  userType,
}) {
  return (
    <InputContainer user={userType === "User"}>
      {userType === "User" ? (
        <>
          <Label htmlFor="customer_id">Customer ID</Label>
          <Field
            id="customer_id" // must be snakecase to post to backend
            placeholder="CuriBio"
            type="text"
            onChange={(e) => {
              setUserData({
                ...userData,
                customer_id: e.target.value,
              });
            }}
          />
          <Label htmlFor="username">Username</Label>
          <Field
            id="username"
            type="text"
            placeholder="User"
            onChange={(e) =>
              setUserData({ ...userData, username: e.target.value })
            }
          />
        </>
      ) : (
        <>
          <Label htmlFor="email">Email</Label>
          <Field
            id="email"
            type="text"
            placeholder="Email"
            onChange={(e) =>
              setUserData({ ...userData, email: e.target.value })
            }
          />
        </>
      )}
      <Label htmlFor="password">Password</Label>
      <Field
        id="password"
        type="password"
        placeholder="Password"
        onChange={(e) => setUserData({ ...userData, password: e.target.value })}
      />

      {children}
    </InputContainer>
  );
}
