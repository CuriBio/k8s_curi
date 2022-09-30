import DashboardLayout from "@/components/layouts/DashboardLayout";
import { useState, useEffect } from "react";
import styled from "styled-components";
import DataTable from "react-data-table-component";
import UsersActionSelector from "@/components/table/UsersActionsSelector";
import FilterHeader from "@/components/table/FilterHeader";
const columns = [
  {
    name: "Status",
    center: true,
    sortable: true,
    selector: (row) => (row.suspended ? "Deactive" : "Active"),
  },
  {
    name: "Name",
    center: true,
    sortable: true,
    selector: (row) => row.name,
  },
  {
    name: "Email",
    center: true,
    sortable: true,
    selector: (row) => row.email,
  },
  {
    name: "Date Created",
    center: true,
    sortable: true,
    selector: (row) => row.created_at,
  },
  {
    name: "Last Loggedin",
    center: true,
    sortable: true,
    selector: (row) => row.last_login,
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
export default function UserInfo() {
  const [displayData, setDisplayData] = useState([]);
  const [filterString, setFilterString] = useState("");
  const [filtercolumn, setFilterColumn] = useState("");
  const [usersData, setUsersData] = useState([]);
  const getAllUsers = async () => {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_USERS_URL}/`);
      if (response && response.status === 200) {
        const usersJson = await response.json();
        setUsersData(usersJson);
        setDisplayData(usersJson);
      }
    } catch (e) {
      console.log("ERROR fetching all users info");
    }
  };

  useEffect(() => {
    getAllUsers();
  }, []);

  const toUserField = {
    Name: "name",
    Email: "email",
  };
  useEffect(() => {
    const newList = usersData.filter((user) =>
      user[toUserField[filtercolumn]].includes(filterString)
    );
    setDisplayData(newList);
  }, [filterString]);
  useEffect(() => {}, [filtercolumn]);

  const ExpandedComponent = ({ data }) => (
    <UsersActionSelector
      data={data}
      getAllUsers={getAllUsers}
      setUsersData={setUsersData}
    />
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
            subHeader
            subHeaderAlign="right"
            subHeaderComponent={
              <FilterHeader
                columns={["", "Name", "Email", "", ""]}
                setFilterString={setFilterString}
                setFilterColumn={setFilterColumn}
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
