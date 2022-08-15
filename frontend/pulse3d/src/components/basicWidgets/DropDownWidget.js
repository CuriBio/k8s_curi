import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import FormControl from "@mui/material/FormControl";
import Select, { SelectProps } from "@mui/material/Select";
import { useEffect, useState } from "react";
import styled from "styled-components";
import OutlinedInput from "@mui/material/OutlinedInput";

const ErrorText = styled.span`
  color: red;
  padding-left: 15px;
  font-style: italic;
  text-align: left;
  position: relative;
  width: 80%;
  font-size: 16px;
`;

const Placeholder = styled.em`
  font-size: 18px;
  font-weight: bolder;
`

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
      <Select
        displayEmpty
        labelId="select-label"
        id="select-dropdown"
        input={<OutlinedInput />}
        MenuProps={MenuProps}
        onChange={handleChange}
        value={selected}
        renderValue={(selected) => {
          if (selected.length === 0) {
            return <Placeholder>{label}</Placeholder>;
          }
          return options[selected]
        }}
      >
        <MenuItem disabled value="">
          <Placeholder>{label}</Placeholder>
        </MenuItem>
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
