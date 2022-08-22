import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import FormControl from "@mui/material/FormControl";
import Select, { SelectProps } from "@mui/material/Select";
import { forwardRef, useEffect, useState } from "react";
import styled from "styled-components";
import OutlinedInput from "@mui/material/OutlinedInput";
import Tooltip from "@mui/material/Tooltip";

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
`;

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
const MenuProps = {
  PaperProps: {
    style: {
      maxHeight: "400px",
      width: "inherit",
    },
  },
};

const TooltipText = styled.span`
  font-size: 15px;
`;

export default function DropDownWidget({
  options,
  label,
  error = "",
  handleSelection,
  reset,
  disabled = false,
  disableOptions = Array(options.length).fill(false),
  optionsTooltipText,
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
          return options[selected];
        }}
      >
        <MenuItem disabled>
          <Placeholder>{label}</Placeholder>
        </MenuItem>
        {options.map((item, idx) => {
          return disableOptions[idx] ? (
            <Tooltip
              key={idx}
              title={<TooltipText>{optionsTooltipText[idx]}</TooltipText>}
              value={idx}
            >
              <div>
                <ListItem disabled={true}>{item}</ListItem>
              </div>
            </Tooltip>
          ) : (
            <ListItem key={idx} value={idx}>
              {item}
            </ListItem>
          );
        })}
      </Select>
      <ErrorText>{errorMsg}</ErrorText>
    </FormControl>
  );
}
