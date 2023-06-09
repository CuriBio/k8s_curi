import DashboardLayout from "@/components/layouts/DashboardLayout";
import DropDownWidget from "@/components/basicWidgets/DropDownWidget";
import { useState, useEffect } from "react";
import styled from "styled-components";
import DataTable from "react-data-table-component";
import CircularSpinner from "@/components/basicWidgets/CircularSpinner";
import ResizableColumn from "@/components/table/ResizableColumn";
import ColumnHead from "@/components/table/ColumnHead";
import Checkbox from "@mui/material/Checkbox";
import { Tooltip } from "@mui/material";
import ModalWidget from "@/components/basicWidgets/ModalWidget";
import PasswordForm from "@/components/account/PasswordForm";
// These can be overridden on a col-by-col basis by setting a value in an  obj in the columns array above
const columnProperties = {
  center: false,
  sortable: true,
};
const customStyles = {
  headRow: {
    style: {
      backgroundColor: "var(--dark-blue)",
      color: "white",
      fontSize: "1.2rem",
    },
  },
  subHeader: {
    style: {
      backgroundColor: "var(--dark-blue)",
    },
  },
  expanderButton: {
    style: { flex: "0", margin: "0" },
  },
  rows: {
    style: {
      height: "60px",
    },
  },
  cells: {
    style: { padding: "0 0 0 1.3%" },
  },
};

const DropDownContainer = styled.div`
  width: 250px;
  background-color: white;
  border-radius: 5px;
`;
const ErrorText = styled.span`
  color: red;
  font-style: italic;
  text-align: left;
  position: relative;
  width: 85%;
  padding-top: 2%;
`;

const Container = styled.div`
  position: relative;
  margin: 0% 3% 3% 3%;
  margin-top: 3rem;
  box-shadow: 0px 5px 5px -3px rgb(0 0 0 / 30%), 0px 8px 10px 1px rgb(0 0 0 / 20%),
    0px 3px 14px 2px rgb(0 0 0 / 12%);
`;

const SpinnerContainer = styled.div`
  margin: 50px;
`;

const ActiveVerifyLink = styled.div`
  font-style: italic;
  color: var(--dark-gray);
  &:hover {
    cursor: pointer;
    color: var(--teal-green);
    text-decoration: underline;
  }
`;

const DisabledLink = styled.div`
  font-style: italic;
  color: var(--dark-gray);
  cursor: default;
`;

const TooltipText = styled.span`
  font-size: 15px;
`;

const PasswordInputContainer = styled.div`
  margin: 25px 0px;
  justify-content: center;
  align-items: center;
  display: flex;
  width: 100%;
`;
const formatDateTime = (datetime) => {
  if (datetime)
    return new Date(datetime + "Z").toLocaleDateString(undefined, {
      hour: "numeric",
      minute: "numeric",
    });
  else {
    const now = new Date();
    const datetime =
      now.getFullYear() +
      "-" +
      (now.getMonth() + 1) +
      "-" +
      now.getDate() +
      "-" +
      now.getHours() +
      now.getMinutes() +
      now.getSeconds();
    return datetime;
  }
};
export default function UserInfo() {
  const [resetDropdown, setResetDropdown] = useState(false);
  const [displayData, setDisplayData] = useState([]);
  const [filterString, setFilterString] = useState("");
  const [filterColumn, setFilterColumn] = useState("");
  const [usersData, setUsersData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [nameWidth, setNameWidth] = useState("20%");
  const [emailWidth, setEmailWidth] = useState("20%");
  const [dateWidth, setDateWidth] = useState("20%");
  const [loginWidth, setLoginWidth] = useState("20%");
  const [statusWidth, setStatusWidth] = useState("15%");
  const [checkedUsers, setCheckedUsers] = useState([]);
  const [sortColumn, setSortColumn] = useState("");
  const [openVerifyModal, setOpenVerifyModal] = useState(false);
  const [verifyLink, setVerifyLink] = useState();
  const [errorMsg, setErrorMsg] = useState();
  const [passwords, setPasswords] = useState({ password1: "", password2: "" });
  const [inProgress, setInProgress] = useState(false);
  const [openErrorModal, setOpenErrorModal] = useState(false);
  const columns = [
    {
      width: "5%",
      cell: (row) => (
        <Checkbox
          id={row.id}
          checked={checkedUsers.includes(row.id)}
          onChange={(e) => {
            //add user to checked list
            if (e.target.checked === true) {
              setCheckedUsers([...checkedUsers, row.id]);
            } else {
              //remove user from checked list
              const idxToSplice = checkedUsers.indexOf(e.target.id);
              const temp = [...checkedUsers];
              temp.splice(idxToSplice, 1);
              setCheckedUsers(temp);
            }
          }}
        />
      ),
    },
    {
      name: (
        <ColumnHead
          title="Name"
          setFilterString={setFilterString}
          columnName="name"
          setFilterColumn={setFilterColumn}
          width={nameWidth.replace("%", "")}
          setSelfWidth={setNameWidth}
          setRightNeighbor={setEmailWidth}
          rightWidth={emailWidth.replace("%", "")}
          setSortColumns={setSortColumn}
          sortColumn={sortColumn}
          filterColumn={filterColumn}
        />
      ),
      width: nameWidth,
      sortFunction: (rowA, rowB) => rowA.name.localeCompare(rowB.name),
      cell: (row) => <ResizableColumn content={row.name} />,
    },
    {
      name: (
        <ColumnHead
          title="Email"
          setFilterString={setFilterString}
          columnName="email"
          setFilterColumn={setFilterColumn}
          width={emailWidth.replace("%", "")}
          setSelfWidth={setEmailWidth}
          setRightNeighbor={setDateWidth}
          rightWidth={dateWidth.replace("%", "")}
          setSortColumns={setSortColumn}
          sortColumn={sortColumn}
          filterColumn={filterColumn}
        />
      ),
      width: emailWidth,
      sortFunction: (rowA, rowB) => rowA.email.localeCompare(rowB.email),
      cell: (row) => <ResizableColumn content={row.email} />,
    },
    {
      name: (
        <ColumnHead
          title="Date Created"
          setFilterString={setFilterString}
          columnName="createdAt"
          setFilterColumn={setFilterColumn}
          width={dateWidth.replace("%", "")}
          setSelfWidth={setDateWidth}
          setRightNeighbor={setLoginWidth}
          rightWidth={loginWidth.replace("%", "")}
          setSortColumns={setSortColumn}
          sortColumn={sortColumn}
          filterColumn={filterColumn}
        />
      ),
      width: dateWidth,
      sortFunction: (rowA, rowB) => new Date(rowB.createdAt) - new Date(rowA.createdAt),
      cell: (row) => <ResizableColumn content={formatDateTime(row.createdAt)} />,
    },
    {
      name: (
        <ColumnHead
          title="Last Login"
          setFilterString={setFilterString}
          columnName="lastLogin"
          setFilterColumn={setFilterColumn}
          width={loginWidth.replace("%", "")}
          setSelfWidth={setLoginWidth}
          setRightNeighbor={setStatusWidth}
          rightWidth={statusWidth.replace("%", "")}
          setSortColumns={setSortColumn}
          sortColumn={sortColumn}
          filterColumn={filterColumn}
        />
      ),
      id: "lastLogin",
      width: loginWidth,
      sortFunction: (rowA, rowB) => new Date(rowB.lastLogin) - new Date(rowA.lastLogin),
      cell: (row) => <ResizableColumn content={formatDateTime(row.lastLogin)} />,
    },
    {
      name: (
        <ColumnHead
          title="Status"
          setFilterString={setFilterString}
          columnName="suspended"
          setFilterColumn={setFilterColumn}
          width={statusWidth.replace("%", "")}
          setSelfWidth={setStatusWidth}
          setRightNeighbor={() => {}}
          setSortColumns={setSortColumn}
          sortColumn={sortColumn}
          filterColumn={filterColumn}
          last={true}
        />
      ),
      width: statusWidth,
      sortFunction: (rowA, rowB) => rowB.verified - rowA.verified - rowA.suspended,
      cell: (row) => (
        <ResizableColumn
          content={
            !row.suspended && row.verified ? (
              <div style={{ color: "var(--teal-green)" }}>active</div>
            ) : !row.verified && !row.suspended ? (
              getVerificationDiv(row)
            ) : (
              <div style={{ color: "red" }}>suspended</div>
            )
          }
          width={statusWidth.replace("px", "")}
        />
      ),
    },
  ];

  //gets users at load
  useEffect(() => {
    getAllUsers();
  }, []);

  useEffect(() => {
    if (resetDropdown) setResetDropdown(false);
  }, [resetDropdown]);

  //when filter string changes refilter results
  useEffect(() => {
    if (filterColumn && filterColumn !== "suspended") {
      const newList = filterColumns();
      if (newList.length > 0) {
        setDisplayData(newList);
      }
    }
  }, [filterString]);

  const getVerificationDiv = (row) => {
    return row.verifyLink ? (
      <ActiveVerifyLink onClick={() => handleVerifyModal(row.verifyLink)}>
        needs verification
      </ActiveVerifyLink>
    ) : (
      <Tooltip title={<TooltipText>{"Verification link has expired, please send a new one."}</TooltipText>}>
        <div>
          <DisabledLink>needs verification</DisabledLink>
        </div>
      </Tooltip>
    );
  };

  const getAllUsers = async () => {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_USERS_URL}/`);
      if (response && response.status === 200) {
        const usersJson = await response.json();
        const formatedUserJson = usersJson.map(
          ({ created_at, email, id, last_login, name, suspended, verified, pw_reset_verify_link }) => ({
            createdAt: created_at,
            email: email,
            id: id,
            lastLogin: last_login,
            name: name,
            suspended,
            verified,
            verifyLink: pw_reset_verify_link,
          })
        );
        setUsersData(formatedUserJson);
        setDisplayData(formatedUserJson);
        setLoading(false);
      }
    } catch (e) {
      console.log("ERROR fetching all users info");
    }
  };

  const handleVerifyModal = (link) => {
    setOpenVerifyModal(true);
    setVerifyLink(link);
  };

  const filterColumns = () => {
    return usersData.filter((row) =>
      row[filterColumn].toLocaleLowerCase().includes(filterString.toLocaleLowerCase())
    );
  };

  const sendUserActionPutRequest = async (actionToPreform) => {
    checkedUsers.forEach(async (checkedUser) => {
      try {
        await fetch(`${process.env.NEXT_PUBLIC_USERS_URL}/${checkedUser}`, {
          method: "PUT",
          body: JSON.stringify({ action_type: actionToPreform }),
        });
      } catch {
        console.log("ERROR on put request to get users");
      }
    });
    setTimeout(resetTable, 300);
  };

  const handleDropdownSelection = async (option) => {
    if (option === 0) {
      await sendUserActionPutRequest("delete");
    } else if (option === 1 || option === 2) {
      const checkUsersData = usersData.filter(({ id }) => checkedUsers.includes(id));
      let deactiveUsers = checkUsersData.filter(({ suspended }) => suspended).map(({ name }) => name);
      setCheckedUsers(checkedUsers.filter(({ name }) => deactiveUsers.includes(name) === (option === 1)));

      const action = option === 1 ? "deactivate" : "reactivate";
      await sendUserActionPutRequest(action);
    } else {
      await resendVerificationLink();
    }
  };

  const resendVerificationLink = async () => {
    try {
      const selectedUser = usersData.find(({ id }) => id === checkedUsers[0]);
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_USERS_URL}/email?email=${encodeURIComponent(
          selectedUser.email
        )}&type=verify&user=true`
      );

      if (res && res.status === 204) {
        resetTable();
      } else throw Error();
    } catch (e) {
      setOpenErrorModal(true);
      console.log("ERROR resending verification email", e);
    }
  };

  const onChangePassword = ({ target }) => {
    setPasswords({ ...passwords, [target.id]: target.value });
  };

  const closeVerificationModal = async (idx) => {
    setInProgress(true);
    if (idx === 1) {
      try {
        // attach jwt token to verify request
        const headers = new Headers({
          "Content-Type": "application/json",
          Authorization: `Bearer ${verifyLink}`,
        });

        const res = await fetch(`${process.env.NEXT_PUBLIC_USERS_URL}/account`, {
          method: "PUT",
          body: JSON.stringify({ ...passwords, verify: true }),
          headers,
        });

        const resBody = await res.json();
        if (res.status === 200) {
          // if successful, reset table to let user know it was successful, or open new error modal telling them to try again later. Catch all error handling
          !resBody ? resetTable() : setOpenErrorModal(true);
        } else {
          throw Error();
        }
      } catch (e) {
        console.log(`ERROR verifying new user account: ${e}`);
        // if error, open error modal to let user know it didn't work
        setOpenErrorModal(true);
      }
    }
    // always close verification modal and set progress spinner back to false
    setOpenVerifyModal(false);
    setInProgress(false);
  };

  const resetTable = () => {
    setCheckedUsers([]);
    getAllUsers();
    setResetDropdown(true);
    setOpenVerifyModal(false);
    setVerifyLink();
    setInProgress(false);
    setOpenErrorModal(false);
  };

  return (
    <>
      <Container>
        <DataTable
          sortIcon={<></>}
          responsive={true}
          columns={columns.map((e) => {
            return {
              ...columnProperties,
              ...e,
            };
          })}
          data={displayData}
          customStyles={customStyles}
          pagination
          defaultSortFieldId="lastLogin"
          progressPending={loading}
          progressComponent={
            <SpinnerContainer>
              <CircularSpinner size={200} color={"secondary"} />
            </SpinnerContainer>
          }
          subHeader={true}
          subHeaderComponent={
            <DropDownContainer>
              <DropDownWidget
                label="Actions"
                options={["Delete", "Deactivate", "Reactivate", "Resend Verification Link"]}
                disableOptions={[
                  checkedUsers.length === 0,
                  checkedUsers.length === 0 ||
                    usersData
                      .filter((user) => checkedUsers.includes(user.id))
                      .filter((checkedUsers) => checkedUsers.suspended).length !== 0,
                  checkedUsers.length === 0 ||
                    usersData
                      .filter((user) => checkedUsers.includes(user.id))
                      .filter((checkedUsers) => !checkedUsers.suspended).length !== 0,
                  checkedUsers.length !== 1 ||
                    (checkedUsers.length === 1 &&
                      usersData.filter(({ id }) => checkedUsers.includes(id))[0].verified) ||
                    (checkedUsers.length === 1 &&
                      !usersData.filter(({ id }) => checkedUsers.includes(id))[0].verified &&
                      usersData.filter(({ id }) => checkedUsers.includes(id))[0].verifyLink),
                ]}
                optionsTooltipText={[
                  "Must make a selection below before action become available.",
                  "Must select a user who is active before action become available.",
                  "Must select a user who is suspended before action become available.",
                  "Must select an unverified user with an expired link.",
                ]}
                handleSelection={handleDropdownSelection}
                reset={resetDropdown}
              />
            </DropDownContainer>
          }
        />
      </Container>
      <ModalWidget
        open={openVerifyModal}
        width={500}
        closeModal={closeVerificationModal}
        header={"Verify User"}
        labels={["Please enter a new password."]}
        buttons={["Cancel", "Verify"]}
      >
        <PasswordInputContainer>
          {!inProgress ? (
            <PasswordForm
              password1={passwords.password1}
              password2={passwords.password2}
              onChangePassword={onChangePassword}
              setErrorMsg={setErrorMsg}
            >
              <ErrorText id="passwordError" role="errorMsg">
                {errorMsg}
              </ErrorText>
            </PasswordForm>
          ) : (
            <CircularSpinner size={150} color={"secondary"} />
          )}
        </PasswordInputContainer>
      </ModalWidget>
      <ModalWidget
        open={openErrorModal}
        width={500}
        closeModal={resetTable}
        header={"Error Occurred!"}
        labels={["Something went wrong while performing this action.", "Please try again later."]}
        buttons={["Close"]}
      />
    </>
  );
}
UserInfo.getLayout = (page) => {
  return <DashboardLayout>{page}</DashboardLayout>;
};
