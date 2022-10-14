import DashboardLayout from "@/components/layouts/DashboardLayout";
import { useState, useEffect } from "react";
import styled from "styled-components";
import DataTable from "react-data-table-component";
import UsersActionSelector from "@/components/table/UsersActionsSelector";
import FilterHeader from "@/components/table/FilterHeader";
import CircularSpinner from "@/components/basicWidgets/CircularSpinner";
const columns = [
  {
    name: "Status",
    center: false,
    sortable: true,
    selector: (row) => (row.suspended ? "Inactive" : "Active"),
  },
  {
    name: "Name",
    center: false,
    sortable: true,
    selector: (row) => row.name,
  },
  {
    name: "Email",
    center: false,
    sortable: true,
    selector: (row) => row.email,
  },
  {
    name: "Date Created",
    center: false,
    sortable: true,
    selector: (row) => formatDateTime(row.created_at),
  },
  {
    name: "Last Loggedin",
    center: false,
    sortable: true,
    selector: (row) => formatDateTime(row.last_login),
  },
];
const customStyles = {
  headRow: {
    style: {
      backgroundColor: "var(--dark-blue)",
      color: "white",
    },
  },
  subHeader: {
    style: {
      backgroundColor: "var(--dark-blue)",
    },
  },
};

const conditionalRowStyles = [
  {
    when: (row) => row.suspended === true,
    style: {
      color: "var(--dark-gray  )",
    },
  },
  {
    when: (row) => row.suspended === false,
    style: {
      color: "var(--teal-green)",
    },
  },
];

const PageContainer = styled.div`
  width: 80%;
`;

const Container = styled.div`
  position: relative;
  padding: 0% 3% 3% 3%;
  margin-top: 1rem;
`;

const SpinnerContainer = styled.div`
  margin: 50px;
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
  const [displayData, setDisplayData] = useState([]);
  const [filterString, setFilterString] = useState("");
  const [filtercolumn, setFilterColumn] = useState("");
  const [usersData, setUsersData] = useState([]);
  const [loading, setLoading] = useState(true);
  const getAllUsers = async () => {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_USERS_URL}/`);
      if (response && response.status === 200) {
        const usersJson = await response.json();
        setUsersData(usersJson);
        setDisplayData(usersJson);
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

  //when user data changes make sure to refilter the results
  useEffect(() => {
    if (usersData.length > 0 && filtercolumn.length > 0) {
      const newList = usersData.filter((user) => user[toUserField[filtercolumn]].includes(filterString));
      setDisplayData(newList);
    }
  }, [usersData]);

  const toUserField = {
    Name: "name",
    Email: "email",
    "Date Created": "created_at",
    "Last Loggedin": "last_login",
  };
  //when filter string changes refilter results
  useEffect(() => {
    const newList = usersData.filter((user) => {
      //if the column containes date data
      //TODO add better date filter
      if (toUserField[filtercolumn] === "created_at" || toUserField[filtercolumn] === "last_login") {
        return formatDateTime(user[toUserField[filtercolumn]])
          .toLocaleLowerCase()
          .includes(filterString.toLocaleLowerCase());
      } else if (user[toUserField[filtercolumn]]) {
        return user[toUserField[filtercolumn]].includes(filterString);
      }
    });
    setDisplayData(newList);
  }, [filterString]);

  const ExpandedComponent = ({ data }) => (
    <UsersActionSelector data={data} getAllUsers={getAllUsers} setUsersData={setUsersData} />
  );
  return (
    <>
      <PageContainer>
        <Container>
          <DataTable
            columns={columns}
            data={displayData}
            customStyles={customStyles}
            expandableRows
            expandableRowsComponent={ExpandedComponent}
            conditionalRowStyles={conditionalRowStyles}
            pagination
            defaultSortFieldId={1}
            progressPending={loading}
            progressComponent={
              <SpinnerContainer>
                <CircularSpinner size={200} color={"secondary"} />
              </SpinnerContainer>
            }
            subHeader
            subHeaderComponent={
              <FilterHeader
                columns={["", "Name", "Email", "Date Created", "Last Loggedin"]}
                setFilterString={setFilterString}
                setFilterColumn={setFilterColumn}
                loading={loading}
              />
            }
          />
        </Container>
      </PageContainer>
    </>
  );
}
UserInfo.getLayout = (page) => {
  return <DashboardLayout>{page}</DashboardLayout>;
};
