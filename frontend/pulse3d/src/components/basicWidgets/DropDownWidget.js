import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import FormControl from "@mui/material/FormControl";
import Select, { SelectProps } from "@mui/material/Select";
import { useEffect, useState } from "react";
import styled from "styled-components";

const ErrorText = styled.span`
  color: red;
  padding-left: 15px;
  font-style: italic;
  text-align: left;
  position: relative;
  width: 80%;
  font-size: 16px;
`;

const MenuProps = {
  PaperProps: {
    style: {
      maxHeight: "400px",
      width: "inherit",
    },
  },
};
const ListItem = styled((MenuItemProps) => <MenuItem {...MenuItemProps} />)(
  () => ({
    fontSize: "16px",
    padding: "10px 30px",
    "&:hover": {
      backgroundColor: "var(--light-gray)",
    },
    "& .MuiMenu-list": {
      backgroundColor: "blue",
    },
  })
);

export default function DropDownWidget({
  options,
  label,
  error = "",
  handleSelection,
  reset,
  disabled = false
}) {
  const [selected, setSelected] = useState("");
  const [errorMsg, setErrorMsg] = useState(error);

  const handleChange = ({ target }) => {
    handleSelection(target.value);
    setSelected(target.value);
    setErrorMsg("");
  };

  useEffect(() => {
    if (reset) setSelected("");
  }, [reset]);

  return (
    <FormControl fullWidth disabled={disabled}>
      <InputLabel id="select-label">{label}</InputLabel>
      <Select
        labelId="select-label"
        id="select-dropdown"
        label={label}
        MenuProps={MenuProps}
        onChange={handleChange}
        value={selected}
      >
        {options.map((item, idx) => (
          <ListItem key={idx} value={idx}>
            {item}
          </ListItem>
        ))}
      </Select>
      <ErrorText>{errorMsg}</ErrorText>
    </FormControl>
  );
}
