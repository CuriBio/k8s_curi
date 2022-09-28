import TableRow from "@mui/material/TableRow";
import TableCell from "@mui/material/TableCell";
import DropDownWidget from "@/components/basicWidgets/DropDownWidget";

export default function UsersRow({ row, dropDownOptions, modalPopUp, userActions }) {
  const status = row.suspended ? "Deactivated" : "Active";
  const options = row.suspended ? dropDownOptions.slice(0, 1) : dropDownOptions;
  const tableCellStyle = {
    color: row.suspended ? "var(--dark-gray)" : "var(--teal-green)",
    width: `${100 / 6}%`,
  };
  const usersAction = (optionIdx) => {
    modalPopUp();
    userActions(options[optionIdx], row.name, row.id);
  };

  return (
    <TableRow key={row.id}>
      {/* TODO: could probably create all these TableCells inside of a loop */}
      <TableCell align="center" style={tableCellStyle}>
        {status}
      </TableCell>
      <TableCell align="center" style={tableCellStyle}>
        {row.name}
      </TableCell>
      <TableCell align="center" style={tableCellStyle}>
        {row.email}
      </TableCell>
      <TableCell align="center" style={tableCellStyle}>
        {row.created_at.substring(0, 10)}
      </TableCell>
      <TableCell align="center" style={tableCellStyle}>
        {row.last_login.substring(0, 10)}
      </TableCell>
      <TableCell>
        <DropDownWidget label="Action" options={options} handleSelection={usersAction} />
      </TableCell>
    </TableRow>
  );
}
