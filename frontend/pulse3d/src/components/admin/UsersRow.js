import TableRow from "@mui/material/TableRow";
import TableCell from "@mui/material/TableCell";
import DropDownWidget from "@/components/basicWidgets/DropDownWidget";

export default function UsersRow({ row, modalPopUp, userActions }) {
  const usersAction = (option) => {
    modalPopUp();
    userActions(option, row.name, row.email);
  };

  return (
    <>
      {row.deactivated ? (
        <TableRow key={row.email}>
          <TableCell
            align="center"
            style={{ color: "var(--dark-gray)", width: `${100 / 6}%` }}
          >
            Deactivated
          </TableCell>
          <TableCell
            align="center"
            style={{ color: "var(--dark-gray)", width: `${100 / 6}%` }}
          >
            {row.name}
          </TableCell>
          <TableCell
            align="center"
            style={{ color: "var(--dark-gray)", width: `${100 / 6}%` }}
          >
            {row.email}
          </TableCell>
          <TableCell
            align="center"
            style={{ color: "var(--dark-gray)", width: `${100 / 6}%` }}
          >
            {row.date_created.substring(0, 10)}
          </TableCell>
          <TableCell
            align="center"
            style={{ color: "var(--dark-gray)", width: `${100 / 6}%` }}
          >
            {row.last_loggedin.substring(0, 10)}
          </TableCell>
          <TableCell>
            <DropDownWidget
              label="Action"
              options={["Delete"]}
              handleSelection={usersAction}
            />
          </TableCell>
        </TableRow>
      ) : (
        <TableRow key={row.email}>
          <TableCell
            align="center"
            style={{ color: "var(--teal-green)", width: `${100 / 6}%` }}
          >
            Active
          </TableCell>
          <TableCell
            align="center"
            style={{ color: "var(--teal-green)", width: `${100 / 6}%` }}
          >
            {row.name}
          </TableCell>
          <TableCell
            align="center"
            style={{ color: "var(--teal-green)", width: `${100 / 6}%` }}
          >
            {row.email}
          </TableCell>
          <TableCell
            align="center"
            style={{ color: "var(--teal-green)", width: `${100 / 6}%` }}
          >
            {row.date_created.substring(0, 10)}
          </TableCell>
          <TableCell
            align="center"
            style={{ color: "var(--teal-green)", width: `${100 / 6}%` }}
          >
            {row.last_loggedin.substring(0, 10)}
          </TableCell>
          <TableCell>
            <DropDownWidget
              label="Actions"
              options={["Delete", "Deactivate"]}
              handleSelection={usersAction}
            />
          </TableCell>
        </TableRow>
      )}
    </>
  );
}
