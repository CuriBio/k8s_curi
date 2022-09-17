import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import FormControl from "@mui/material/FormControl";
import Select, { SelectProps } from "@mui/material/Select";
import { useEffect, useState } from "react";
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
  initialSelected,
}) {
  const [selected, setSelected] = useState("");
  const [errorMsg, setErrorMsg] = useState(error);

  const handleChange = (e) => {
    if (!disableOptions[e.target.value]) {
      handleSelection(e.target.value);
      setSelected(e.target.value);
      setErrorMsg("");
    }
  };
  useEffect(() => {
    // initialSelected needs to be the index of item
    if (initialSelected) setSelected(initialSelected);
  }, []);

  useEffect(() => {
    if (reset) setSelected(initialSelected ? initialSelected : "");
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
          /* 
             Must be initialSelected === undefined and not !initialSelected,
             An index of 0 will pass !initialSelected as truthy
          */
          if (selected.length === 0 && initialSelected === undefined) {
            return <Placeholder>{label}</Placeholder>;
          } else if (selected === "" && initialSelected !== undefined) {
            return options[initialSelected];
          } else {
            return options[selected];
          }
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
