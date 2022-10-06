import styled from "styled-components";

const Container = styled.div`
  background-color: var(--dark-gray);
  display: flex;
  justify-content: space-around;
  padding: 1rem;
`;

export default function UsersActionSelector(props) {
  const sendUserActionPutRequest = async (actionToPreform) => {
    try {
      await fetch(`${process.env.NEXT_PUBLIC_USERS_URL}/${props.data.id}`, {
        method: "PUT",
        body: JSON.stringify({ action_type: actionToPreform }),
      });
    } catch {
      console.log("Error on put request to get users");
    }
  };
  const buttonAction = async (action) => {
    await sendUserActionPutRequest(action);
    props.getAllUsers();
  };
  return (
    <>
      <Container>
        <button
          onClick={() => {
            buttonAction("delete");
          }}
        >
          Delete
        </button>
        {!props.data.suspended ? (
          <button
            onClick={() => {
              buttonAction("deactivate");
            }}
          >
            Deactivate
          </button>
        ) : null}
      </Container>
    </>
  );
}
