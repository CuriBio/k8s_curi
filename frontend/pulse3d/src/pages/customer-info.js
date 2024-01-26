import DashboardLayout from "@/components/layouts/DashboardLayout";
import styled from "styled-components";
import { useEffect, useMemo, useState } from "react";
import DropDownWidget from "@/components/basicWidgets/DropDownWidget";
import { Tooltip } from "@mui/material";
import Table from "@/components/table/Table";
import ModalWidget from "@/components/basicWidgets/ModalWidget";
import PasswordForm from "@/components/account/PasswordForm";
import EditCustomerForm from "@/components/admin/EditCustomerForm";
import CircularSpinner from "@/components/basicWidgets/CircularSpinner";
import { formatDateTime } from "@/utils/generic";

import { Box } from "@mui/material";

// These can be overridden on a col-by-col basis by setting a value in an  obj in the columns array above
const TooltipText = styled.span`
  font-size: 15px;
`;

const TableContainer = styled.div`
  margin: 3% 3% 3% 3%;
  overflow: auto;
  white-space: nowrap;
  box-shadow: 0px 5px 5px -3px rgb(0 0 0 / 30%), 0px 8px 10px 1px rgb(0 0 0 / 20%),
    0px 3px 14px 2px rgb(0 0 0 / 12%);
`;

const DropDownContainer = styled.div`
  width: 250px;
  background-color: white;
  border-radius: 8px;
  position: relative;
  margin: 15px 20px;
`;

const ErrorText = styled.span`
  color: red;
  font-style: italic;
  text-align: left;
  position: relative;
  width: 85%;
  padding-top: 2%;
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

const PasswordInputContainer = styled.div`
  margin: 25px 0px;
  justify-content: center;
  align-items: center;
  display: flex;
  width: 100%;
`;

export default function Customers() {
  const [customerData, setCustomerData] = useState([]);
  const [resetDropdown, setResetDropdown] = useState(false);
  const [openEditModal, setOpenEditModal] = useState(false);
  // const [openVerifyModal, setOpenVerifyModal] = useState(false);
  // const [resetToken, setResetToken] = useState();
  // const [passwords, setPasswords] = useState({ password1: "", password2: "" });
  const [errorMsg, setErrorMsg] = useState();
  const [openErrorModal, setOpenErrorModal] = useState(false);
  const [inProgress, setInProgress] = useState(false);
  const [rowSelection, setRowSelection] = useState({});
  const [isLoading, setIsLoading] = useState(true);

  // gets users at load
  useEffect(() => {
    getAllCustomers();
  }, []);

  // useEffect(() => {
  //   if (resetDropdown) setResetDropdown(false);
  // }, [resetDropdown]);

  const getAllCustomers = async () => {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_USERS_URL}/customers`);
      if (response && response.status === 200) {
        const customersJson = await response.json();
        const customers = customersJson.map(
          ({ email, id, last_login: lastLogin, scopes, usage_restrictions: usage, suspended }) => ({
            email,
            id,
            lastLogin,
            scopes,
            usage,
            suspended,
          })
        );

        setCustomerData([...customers]);
        setIsLoading(false);
      }
    } catch (e) {
      console.log("ERROR fetching all customer info");
    }
  };

  const columns = useMemo(
    () => [
      {
        accessorKey: "id", //accessorFn used to join multiple data into a single cell
        id: "id", //id is still required when using accessorFn instead of accessorKey
        header: "Customer ID",
        filterVariant: "autocomplete",
        size: 300,
        minSize: 130,
      },
      {
        accessorKey: "email", //accessorKey used to define `data` column. `id` gets set to accessorKey automatically
        filterVariant: "autocomplete",
        id: "email",
        header: "Email",
        size: 275,
        minSize: 130,
      },
      {
        accessorFn: (row) => new Date(row.lastLogin),
        header: "Last Login",
        id: "lastLogin",
        filterVariant: "date-range",
        sortingFn: "datetime",
        size: 275,
        minSize: 275,
        Cell: ({ cell }) => formatDateTime(cell.getValue()),
      },
      {
        accessorKey: "scopes",
        id: "products",
        filterVariant: "autocomplete",
        header: "Products",
        size: 170,
        minSize: 130,
        Cell: ({ cell }) => (
          <Box component="div">
            {cell.getValue().map((s) => (
              <div key={s}>{s.split(":")[0]}</div>
            ))}
          </Box>
        ),
      },
      {
        accessorKey: "usage",
        header: "Usage Restrictions",
        id: "usage",
        filterVariant: "autocomplete",
        size: 200,
        minSize: 130,
        Cell: ({ cell }) => getUsageDiv(cell),
      },
      {
        accessorFn: (row) => getStatusValue(row),
        id: "status",
        filterVariant: "autocomplete",
        header: "Status",
        size: 200,
        minSize: 130,
        Cell: ({ cell }) => getStatusDiv(cell),
      },
    ],
    []
  );

  const getUsageDiv = (c) => {
    const usageObj = JSON.parse(c.getValue());
    return (
      <Box component="div">
        {Object.entries(usageObj).map(([product, restrictions]) => (
          <div key={product}>
            <strong>{product}:</strong>
            {Object.keys(restrictions).map((label) => (
              <ul key={label} style={{ margin: "3px" }}>
                {label.split("_")[0]}:{" "}
                {[null, -1].includes(restrictions[label]) ? "unlimited" : restrictions[label]}
              </ul>
            ))}
          </div>
        ))}
      </Box>
    );
  };

  // Need to return in the order they need to be sorted
  const getStatusValue = (row) => {
    // if user is verified and not suspended
    if (!row.suspended) {
      return "A";
      // else if user is not verified
      // } else if (!row.verified && !row.suspended) {
      //   // if a user has an active resetToken and is not verified, then allow for a reset
      //   if (row.resetToken) {
      //     return "A";
      //     // else the link has been expired and user requires a new verification link to be sent
      //   } else {
      //     return "B";
      //   }
    } else {
      // else a user is suspended or inactive
      return "B";
    }
  };

  // based on sorted value, return visible div to show user
  const getStatusDiv = (c) => {
    // TODO clean this up
    const v = c.getValue();
    // if user is verified and not suspended
    if (v === "A") {
      return <div style={{ color: "var(--teal-green)" }}>active</div>;
      // if a user has an active resetToken and is not verified, then allow for a reset
      // } else if (v === "A") {
      //   return (
      //     <ActiveVerifyLink onClick={() => handleVerifyModal(c.row.original.resetToken)}>
      //       needs verification
      //     </ActiveVerifyLink>
      //   );
      //   // else the link has been expired and user requires a new verification link to be sent
      // } else if (v === "B") {
      //   return (
      //     <Tooltip title={<TooltipText>{"Verification link has expired, please send a new one."}</TooltipText>}>
      //       <div>
      //         <DisabledLink>needs verification</DisabledLink>
      //       </div>
      //     </Tooltip>
      //   );
    } else {
      // else a user is suspended or inactive
      return <div style={{ color: "red" }}>inactive</div>;
    }
  };

  // const closeVerificationModal = async (idx) => {
  //   setInProgress(true);
  //   if (idx === 1) {
  //     try {
  //       // attach jwt token to verify request
  //       const headers = new Headers({
  //         "Content-Type": "application/json",
  //         Authorization: `Bearer ${resetToken}`,
  //       });

  //       const res = await fetch(`${process.env.NEXT_PUBLIC_USERS_URL}/account`, {
  //         method: "PUT",
  //         body: JSON.stringify({ ...passwords, verify: true }),
  //         headers,
  //       });

  //       const resBody = await res.json();
  //       if (res.status === 200) {
  //         // if successful, reset table to let user know it was successful, or open new error modal telling them to try again later. Catch all error handling
  //         !resBody ? await resetTable() : setOpenErrorModal(true);
  //       } else {
  //         throw Error();
  //       }
  //     } catch (e) {
  //       console.log(`ERROR verifying new user account: ${e}`);
  //       // if error, open error modal to let user know it didn't work
  //       setOpenErrorModal(true);
  //     }
  //   }
  //   // always close verification modal and set progress spinner back to false
  //   setOpenVerifyModal(false);
  //   setInProgress(false);
  // };

  // const onChangePassword = ({ target }) => {
  //   setPasswords({ ...passwords, [target.id]: target.value });
  // };

  // const resendVerificationLink = async (email) => {
  //   try {
  //     const res = await fetch(
  //       `${process.env.NEXT_PUBLIC_USERS_URL}/email?email=${encodeURIComponent(email)}&type=verify&user=true`
  //     );
  //     if (res && res.status === 204) {
  //       await resetTable();
  //     } else throw Error();
  //   } catch (e) {
  //     setOpenErrorModal(true);
  //     console.log("ERROR resending verification email", e);
  //   }
  // };

  const resetTable = async () => {
    setResetDropdown(true);
    // setOpenVerifyModal(false);
    setResetToken();
    setOpenErrorModal(false);
    setOpenEditModal(false);
    setInProgress(false);
    setRowSelection({});
    setPasswords({ password1: "", password2: "" });
    setErrorMsg();

    await getAllUsers();
  };

  // const handleVerifyModal = (link) => {
  //   setOpenVerifyModal(true);
  //   setResetToken(link);
  // };

  // const sendUserActionPutRequest = async (actionToPreform, users) => {
  //   try {
  //     users.forEach(async ({ id }) => {
  //       await fetch(`${process.env.NEXT_PUBLIC_USERS_URL}/${id}`, {
  //         method: "PUT",
  //         body: JSON.stringify({ action_type: actionToPreform }),
  //       });
  //     });
  //   } catch {
  //     console.log("ERROR on put request to selected users");
  //   }
  // };

  const actionsFn = (t) => {
    const dropdownOptions = ["Deactivate", "Reactivate", "Edit"];
    const checkedRows = t.getSelectedRowModel().rows;
    const checkedCustomers = checkedRows.map(({ original }) => original);
    // // dropdown disable states
    // const deleteState = checkedUsers.length === 0;
    const deactivateState = checkedCustomers.length === 0 || checkedCustomers.some((cust) => cust.suspended);
    const reactivateState = checkedCustomers.length === 0 || checkedCustomers.some((cust) => !cust.suspended);
    // const resendState =
    //   checkedUsers.length !== 1 ||
    //   (checkedUsers.length === 1 && checkedUsers[0].verified) ||
    //   (checkedUsers.length === 1 && !checkedUsers[0].verified && checkedUsers[0].resetToken);
    const editState = checkedCustomers.length !== 1;

    const handleDropdownSelection = async (option) => {
      // if ([0, 1, 2].includes(option)) {
      //   // if delete, deactivate, or reactive
      //   await sendUserActionPutRequest(dropdownOptions[option].toLowerCase(), checkedUsers);
      //   // update table state
      //   await resetTable();
      // } else if (option === 3) {
      //   // else if resend verification link
      //   const { email } = checkedRows[0].original;
      //   await resendVerificationLink(email);
      // } else {
      // else edit user
      setOpenEditModal(checkedCustomers[0]);
      // }
    };

    return (
      <Box sx={{ width: "100%", position: "relative", display: "flex", justifyContent: "end" }}>
        <DropDownContainer>
          <DropDownWidget
            label="Actions"
            options={dropdownOptions}
            disableOptions={[deactivateState, reactivateState, editState]}
            optionsTooltipText={[
              "Must select a customer who is active before action become available.",
              "Must select a customer who is inactive before action become available.",
              "Must select a customer to edit.",
            ]}
            handleSelection={handleDropdownSelection}
            reset={resetDropdown}
          />
        </DropDownContainer>
      </Box>
    );
  };

  return (
    <>
      <TableContainer>
        <Table
          columns={columns}
          rowData={customerData}
          toolbarFn={actionsFn}
          defaultSortColumn={"lastLogin"}
          rowSelection={rowSelection}
          setRowSelection={setRowSelection}
          isLoading={isLoading}
        />
      </TableContainer>
      {/* <ModalWidget
        open={openVerifyModal}
        width={500}
        closeModal={closeVerificationModal}
        header={"Verify User"}
        labels={inProgress ? [] : ["Please enter a new password."]}
        buttons={["Cancel", "Verify"]}
      >
        <PasswordInputContainer>
          {inProgress ? (
            <CircularSpinner size={150} color={"secondary"} />
          ) : (
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
          )}
        </PasswordInputContainer>
      </ModalWidget> */}
      <ModalWidget
        open={openErrorModal}
        width={500}
        closeModal={resetTable}
        header={"Error Occurred!"}
        labels={["Something went wrong while performing this action.", "Please try again later."]}
        buttons={["Close"]}
      />
      <EditCustomerForm
        customerData={openEditModal}
        openEditModal={openEditModal}
        setOpenEditModal={setOpenEditModal}
        resetTable={resetTable}
      />
    </>
  );
}

Customers.getLayout = (page) => {
  return <DashboardLayout>{page}</DashboardLayout>;
};
