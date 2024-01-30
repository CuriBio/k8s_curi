import DashboardLayout from "@/components/layouts/DashboardLayout";
import styled from "styled-components";
import { useEffect, useMemo, useState } from "react";
import DropDownWidget from "@/components/basicWidgets/DropDownWidget";
import Table from "@/components/table/Table";
import ModalWidget from "@/components/basicWidgets/ModalWidget";
import EditCustomerForm from "@/components/admin/EditCustomerForm";
import { formatDateTime } from "@/utils/generic";

import { Box } from "@mui/material";

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

export default function Customers() {
  const [customerData, setCustomerData] = useState([]);
  const [resetDropdown, setResetDropdown] = useState(false);
  const [openEditModal, setOpenEditModal] = useState(false);
  const [openErrorModal, setOpenErrorModal] = useState(false);
  const [rowSelection, setRowSelection] = useState({});
  const [isLoading, setIsLoading] = useState(true);

  // gets users at load
  useEffect(() => {
    getAllCustomers();
  }, []);

  useEffect(() => {
    if (resetDropdown) {
      setResetDropdown(false);
      // need to wait 2 seconds for the request to process, otherwise the /customers route returns with customer with information that has not been updated
      // less than two seconds doesn't work for multiple users at the same time
      setTimeout(() => getAllCustomers(), [2000]);
    }
  }, [resetDropdown]);

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
            scopes: scopes.length > 0 && scopes[0] == null ? [] : scopes,
            usage,
            suspended,
          })
        );
        console.log(customers);
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
        accessorFn: (row) => row,
        header: "Usage Restrictions",
        id: "usage",
        enableColumnFilter: false, // removing for now because it depends on the returned value for accessorFn which is an object, there are workarounds if needed
        size: 300,
        minSize: 130,
        Cell: ({ cell }) => getUsageDiv(cell),
      },
      {
        accessorFn: (row) => getStatusValue(row),
        id: "status",
        filterVariant: "autocomplete",
        header: "Status",
        size: 130,
        minSize: 130,
        Cell: ({ cell }) => getStatusDiv(cell),
      },
    ],
    []
  );

  const getUsageDiv = (c) => {
    const usageObj = JSON.parse(c.getValue().usage);
    const scopes = c.getValue().scopes.map((s) => s.split(":")[0]);

    return (
      <div style={{ display: "flex" }}>
        {Object.entries(usageObj)
          // filter out products that are not available to customer, unnecessary to show
          .filter(([product, _]) => scopes.includes(product))
          .map(([product, restrictions]) => (
            <div key={product}>
              {product}:
              {Object.keys(restrictions)
                // filter out uploads key
                .filter((label) => label !== "uploads")
                .map((label) => {
                  // swap jobs key for analyses for viewing
                  const displayLabel = label.split("_")[0] === "jobs" ? "analyses" : label.split("_")[0];
                  // swap -1 for unlimited
                  const displayValue = [null, -1].includes(restrictions[label])
                    ? "unlimited"
                    : restrictions[label];
                  // return in form of 'analyses: <val>'
                  return (
                    <ul key={label} style={{ margin: "3px" }}>
                      {displayLabel}: {displayValue}
                    </ul>
                  );
                })}
            </div>
          ))}
      </div>
    );
  };

  // Need to return in the order they need to be sorted
  const getStatusValue = (row) => {
    // set value so that filtering works as expected
    return row.suspended ? "inactive" : "active";
  };

  // based on sorted value, return visible div to show user
  const getStatusDiv = (c) => {
    return c.getValue() === "active" ? (
      <div style={{ color: "var(--teal-green)" }}>active</div>
    ) : (
      <div style={{ color: "red" }}>inactive</div>
    );
  };

  const resetTable = async () => {
    setResetDropdown(true);
    setOpenErrorModal(false);
    setOpenEditModal(false);
    setRowSelection({});
  };

  const sendUserActionPutRequest = async (actionToPreform, customers) => {
    try {
      customers.forEach(async ({ id }) => {
        await fetch(`${process.env.NEXT_PUBLIC_USERS_URL}/customers/${id}`, {
          method: "PUT",
          body: JSON.stringify({ action_type: actionToPreform }),
        });
      });
    } catch {
      console.log("ERROR on put request to selected customers");
    }
  };

  const actionsFn = (t) => {
    const dropdownOptions = ["Deactivate", "Reactivate", "Edit"];
    const checkedRows = t.getSelectedRowModel().rows;
    const checkedCustomers = checkedRows.map(({ original }) => original);
    // disabled states
    const deactivateState = checkedCustomers.length === 0 || checkedCustomers.some((cust) => cust.suspended);
    const reactivateState = checkedCustomers.length === 0 || checkedCustomers.some((cust) => !cust.suspended);
    const editState = checkedCustomers.length !== 1 || checkedCustomers.some((cust) => cust.suspended);

    const handleDropdownSelection = async (option) => {
      if ([0, 1].includes(option)) {
        // if delete, deactivate, or reactive
        await sendUserActionPutRequest(dropdownOptions[option].toLowerCase(), checkedCustomers);
        // update table state
        resetTable();
      } else {
        // else edit customer
        setOpenEditModal(checkedCustomers[0]);
      }
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
              "Must select an active customer to edit.",
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
