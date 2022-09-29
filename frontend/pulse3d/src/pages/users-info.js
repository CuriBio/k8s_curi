import DashboardLayout from "@/components/layouts/DashboardLayout";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableContainer from "@mui/material/TableContainer";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import Paper from "@mui/material/Paper";
import { useState, useEffect } from "react";
import Row from "@/components/admin/UsersRow";
import styled from "styled-components";
import ModalWidget from "@/components/basicWidgets/ModalWidget";

const PageContainer = styled.div`
  width: 80%;
`;

const Pagination = styled.div`
  width: 100%;
  background-color: var(--dark-gray);
  display: flex;
  justify-content: right;
  padding: 1rem 1rem;
`;

const Container = styled.div`
  display: flex;
  position: relative;
  justify-content: start;
  padding: 0% 3% 3% 3%;
  flex-direction: column;
  margin-top: 1rem;
`;

export default function UserInfo() {
  const [currentPage, setCurrentPage] = useState(1);
  const [rows, setRows] = useState([]);
  const [currentRows, setCurrentRows] = useState([]);
  const [users, setUsers] = useState([]);
  const [actionAlertVisible, setActionAlertVisible] = useState(false);
  const [modalMessage, setModalMessage] = useState();
  const [actionToPreform, setActionToPerform] = useState("");
  const [confirm, setConfirm] = useState(false);
  const [userIdToEdit, setUserIdToEdit] = useState("");

  const dropDownOptions = ["Delete", "Deactivate"];

  const sendUserActionPutRequest = async () => {
    fetch(`${process.env.NEXT_PUBLIC_USERS_URL}/${userIdToEdit}`, {
      method: "PUT",
      body: JSON.stringify({ action_type: actionToPreform }),
    });
  };

  const userActionSelection = async (option, username, userId) => {
    let action = option.toLowerCase();

    setModalMessage(`Are you sure you would like to ${action} ${username}?`);
    setActionToPerform(action);
    setUserIdToEdit(userId);
  };

  const getAllUsers = async () => {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_USERS_URL}/`);
      if (response && response.status === 200) {
        const usersJson = await response.json();
        setUsers(usersJson);
        setCurrentRows(usersJson.slice(0, 10));
      }
    } catch (e) {
      console.log("ERROR fetching all users info");
    }
  };

  useEffect(() => {
    getAllUsers();
  }, []);

  useEffect(() => {
    if (users) {
      setRows([...users]);
    }
  }, [users]);

  useEffect(() => {
    if (actionToPreform && confirm) {
      try {
        sendUserActionPutRequest();
      } catch (e) {
        console.log("ERROR on user action");
      }
    }
  }, [confirm]);

  useEffect(() => {
    setCurrentRows(rows.slice(10 * (currentPage - 1), 10 * (currentPage - 1) + 10));
  }, [currentPage]);

  return (
    <>
      <ModalWidget
        open={actionAlertVisible}
        labels={[modalMessage]}
        buttons={["Yes", "No"]}
        header={"Attention"}
        closeModal={(idx, label) => {
          setConfirm(label === "Yes");
          setActionAlertVisible(false);
        }}
      />
      <PageContainer>
        <Container>
          <TableContainer component={Paper} sx={{ backgroundColor: "var(--light-gray" }}>
            <Table aria-label="collapsible table" size="small">
              <TableHead
                sx={{
                  backgroundColor: "var(--dark-blue)",
                }}
              >
                <TableRow
                  sx={{
                    height: "60px",
                  }}
                  align="center"
                >
                  <TableCell
                    sx={{
                      color: "var(--light-gray)",
                    }}
                    align="center"
                  >
                    Status
                  </TableCell>
                  <TableCell
                    sx={{
                      color: "var(--light-gray)",
                    }}
                    align="center"
                  >
                    Name
                  </TableCell>

                  <TableCell
                    sx={{
                      color: "var(--light-gray)",
                    }}
                    align="center"
                  >
                    Email
                  </TableCell>
                  <TableCell
                    sx={{
                      color: "var(--light-gray)",
                    }}
                    align="center"
                  >
                    Date Created
                  </TableCell>
                  <TableCell
                    sx={{
                      color: "var(--light-gray)",
                    }}
                    align="center"
                  >
                    Last Logged In
                  </TableCell>
                  <TableCell
                    sx={{
                      color: "var(--light-gray)",
                    }}
                    align="center"
                  >
                    Actions
                  </TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {currentRows.map((row) => (
                  <Row
                    key={row.id}
                    row={row}
                    dropDownOptions={dropDownOptions}
                    modalPopUp={() => {
                      setActionAlertVisible(true);
                    }}
                    userActions={userActionSelection}
                  />
                ))}
              </TableBody>
            </Table>
          </TableContainer>
          <Pagination>
            {" "}
            <button
              style={{
                color: "var(--light-gray)",
                backgroundColor: "var(--dark-blue)",
                border: "none",
                marginRight: "1rem",
              }}
              onClick={() => {
                const newPage = currentPage - 1 > 0 ? currentPage - 1 : currentPage;
                setCurrentPage(newPage);
              }}
            >
              Prev
            </button>
            {`Page ${currentPage} of ${Math.ceil(rows.length / 10)}`}
            <button
              style={{
                color: "var(--light-gray)",
                backgroundColor: "var(--dark-blue)",
                border: "none",
                marginLeft: "1rem",
              }}
              onClick={() => {
                const newPage =
                  currentPage + 1 < Math.ceil(rows.length / 10) + 1 ? currentPage + 1 : currentPage;
                setCurrentPage(newPage);
              }}
            >
              Next
            </button>
          </Pagination>
        </Container>
      </PageContainer>
    </>
  );
}
UserInfo.getLayout = (page) => {
  return <DashboardLayout>{page}</DashboardLayout>;
};
