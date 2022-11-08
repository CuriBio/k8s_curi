import DashboardLayout from "@/components/layouts/DashboardLayout";
import DropDownWidget from "@/components/basicWidgets/DropDownWidget";
import { useState, useEffect } from "react";
import styled from "styled-components";
import DataTable from "react-data-table-component";
import CircularSpinner from "@/components/basicWidgets/CircularSpinner";
import ResizableColumn from "@/components/table/ResizableColumn";
import ColumnHead from "@/components/table/ColumnHead";
import Checkbox from "@mui/material/Checkbox";
import ModalWidget from "@/components/basicWidgets/ModalWidget";
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
  expanderCell: {},
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

const modalObjs = {
  deactivate: {
    header: "Attention",
    messages: [
      "You are trying to deactivate some already inactive accounts. They will be ignored. Error Users :",
    ],
  },
};
const DropDownContainer = styled.div`
  width: 250px;
  background-color: white;
  border-radius: 5px;
`;
const PageContainer = styled.div`
  width: 85%;
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

const formatDateTime = (datetime) => {
  if (datetime)
    return new Date(datetime).toLocaleDateString(undefined, {
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
  const [nameWidth, setNameWidth] = useState("15%");
  const [emailWidth, setEmailWidth] = useState("20%");
  const [dateWidth, setDateWidth] = useState("20%");
  const [loginWidth, setLoginWidth] = useState("20%");
  const [statusWidth, setStatusWidth] = useState("20%");
  const [checkedUsers, setCheckedUsers] = useState([]);
  const [sortColumn, setSortColumns] = useState("");
  const [modalState, setModalState] = useState(false);
  const [modalLabels, setModalLabels] = useState({ header: "", messages: [] });
  const [modalButtons, setModalButtons] = useState([]);

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
          setSortColumns={setSortColumns}
          sortColumn={sortColumn}
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
          setSortColumns={setSortColumns}
          sortColumn={sortColumn}
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
          columnName="created_at"
          setFilterColumn={setFilterColumn}
          width={dateWidth.replace("%", "")}
          setSelfWidth={setDateWidth}
          setRightNeighbor={setLoginWidth}
          rightWidth={loginWidth.replace("%", "")}
          setSortColumns={setSortColumns}
          sortColumn={sortColumn}
        />
      ),
      width: dateWidth,
      sortFunction: (rowA, rowB) => new Date(rowB.created_at) - new Date(rowA.created_at),
      cell: (row) => <ResizableColumn content={formatDateTime(row.created_at)} />,
    },
    {
      name: (
        <ColumnHead
          title="Last Login"
          setFilterString={setFilterString}
          columnName="last_login"
          setFilterColumn={setFilterColumn}
          width={loginWidth.replace("%", "")}
          setSelfWidth={setLoginWidth}
          setRightNeighbor={setStatusWidth}
          rightWidth={statusWidth.replace("%", "")}
          setSortColumns={setSortColumns}
          sortColumn={sortColumn}
        />
      ),
      id: "last_login",
      width: loginWidth,
      sortFunction: (rowA, rowB) => new Date(rowB.last_login) - new Date(rowA.last_login),
      cell: (row) => <ResizableColumn content={formatDateTime(row.last_login)} />,
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
          setSortColumns={setSortColumns}
          sortColumn={sortColumn}
          last={true}
        />
      ),
      width: statusWidth,
      sortFunction: (rowA, rowB) => rowA.suspended.localeCompare(rowB.suspended),
      cell: (row) => (
        <ResizableColumn
          content={
            row.suspended === "active" ? (
              <div style={{ color: "var(--teal-green)" }}>{row.suspended}</div>
            ) : (
              <div style={{ color: "red" }}>{row.suspended}</div>
            )
          }
          width={statusWidth.replace("px", "")}
        />
      ),
    },
  ];

  const getAllUsers = async () => {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_USERS_URL}/`);
      if (response && response.status === 200) {
        const usersJson = await response.json();
        const formatedUserJson = usersJson.map(({ created_at, email, id, last_login, name, suspended }) => {
          return {
            created_at: formatDateTime(created_at),
            email: email,
            id: id,
            last_login: formatDateTime(last_login),
            name: name,
            suspended: suspended ? "suspended" : "active",
          };
        });
        setUsersData(formatedUserJson);
        setDisplayData(formatedUserJson);
        setLoading(false);
      }
    } catch (e) {
      console.log("ERROR fetching all users info");
    }
  };

  //gets users at load
  useEffect(() => {
    getAllUsers();
  }, []);

  const filterColumns = () => {
    return usersData.filter((row) => {
      return row[filterColumn].toLocaleLowerCase().includes(filterString.toLocaleLowerCase());
    });
  };
  //when filter string changes refilter results
  useEffect(() => {
    if (filterColumn) {
      const newList = filterColumns();
      if (newList.length > 0) {
        setDisplayData(newList);
      }
    }
  }, [filterString]);

  const sendUserActionPutRequest = async (actionToPreform) => {
    await checkedUsers.forEach(async (checkedUser) => {
      try {
        await fetch(`${process.env.NEXT_PUBLIC_USERS_URL}/${checkedUser}`, {
          method: "PUT",
          body: JSON.stringify({ action_type: actionToPreform }),
        });
      } catch {
        console.log("Error on put request to get users");
      }
    });
    setTimeout(resetTable, 300);
  };
  const resetTable = () => {
    setCheckedUsers([]);
    getAllUsers();
  };
  const handleDropdownSelection = async (option) => {
    if (option === 0) {
      await sendUserActionPutRequest("delete");
    } else if (option === 1) {
      const checkUsersData = usersData.filter((user) => checkedUsers.includes(user.id));
      let deactiveUsers = checkUsersData.filter((user) => user.suspended === "suspended");
      deactiveUsers = deactiveUsers.map((user) => user.name);
      modalObjs.deactivate.messages.push(deactiveUsers);
      setModalButtons(["Close"]);
      setModalLabels(modalObjs.deactivate);
      setModalState("generic");
      setCheckedUsers(checkedUsers.filter((user) => deactiveUsers.includes(user.name)));
      await sendUserActionPutRequest("deactivate");
    }
  };
  return (
    <>
      <PageContainer>
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
            defaultSortFieldId="last_login"
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
                  options={["Delete", "Deactivate"]}
                  disableOptions={[checkedUsers.length === 0, checkedUsers.length === 0]}
                  optionsTooltipText={[
                    "Must make a selection below before actions become available.",
                    "Must select a user who is active before actions become available.",
                  ]}
                  handleSelection={handleDropdownSelection}
                  reset={resetDropdown}
                />
              </DropDownContainer>
            }
          />
        </Container>
      </PageContainer>
      <ModalWidget
        open={modalState === "generic"}
        labels={modalLabels.messages}
        buttons={modalButtons}
        closeModal={() => {
          setModalState("");
        }}
        header={modalLabels.header}
      />
    </>
  );
}
UserInfo.getLayout = (page) => {
  return <DashboardLayout>{page}</DashboardLayout>;
};
