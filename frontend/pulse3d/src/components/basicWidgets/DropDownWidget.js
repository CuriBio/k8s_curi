import MenuItem from "@mui/material/MenuItem";
import FormControl from "@mui/material/FormControl";
import Select from "@mui/material/Select";
import { useEffect, useState } from "react";
import styled from "styled-components";
import OutlinedInput from "@mui/material/OutlinedInput";
import Tooltip from "@mui/material/Tooltip";
import Accordion from "@mui/material/Accordion";
import AccordionSummary from "@mui/material/AccordionSummary";
import AccordionDetails from "@mui/material/AccordionDetails";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";

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

const ListItem = styled((MenuItemProps) => <MenuItem {...MenuItemProps} />)(() => ({
  fontSize: "15px",
  padding: "10px 30px",
  fontFamily: "Mulish",
  "&:hover": {
    backgroundColor: "var(--light-gray)",
  },
  "&:focus": {
    background: "white",
  },
  "& .Mui-selected": {
    background: "white",
  },
}));

const AccordionTab = styled((props) => <AccordionSummary {...props} />)(() => ({
  fontSize: "15px",
  "&.MuiAccordionSummary-root.Mui-expanded": {
    minHeight: "0px",
  },
  "&:hover": {
    background: "var(--light-gray)",
  },
  "& .MuiAccordionSummary-content": {
    margin: "11px 15px",
    minHeight: "0px",
  },
}));

const SubListItem = styled((MenuItemProps) => <MenuItem {...MenuItemProps} />)(() => ({
  fontSize: "15px",
  padding: "10px 30px",
  fontFamily: "Mulish",
  "&:hover": {
    backgroundColor: "var(--light-gray)",
  },
}));

const OutlinedComp = styled((props) => <OutlinedInput {...props} />)(() => ({
  height: "40px",
}));

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
  subOptions = {},
  label,
  error = "",
  handleSelection,
  reset,
  disabled = false,
  disableOptions = Array(options.length).fill(false),
  optionsTooltipText,
  initialSelected,
  handleSubSelection,
  disableSubOptions = {},
  subOptionsTooltipText = [],
}) {
  const [selected, setSelected] = useState("");
  const [errorMsg, setErrorMsg] = useState(error);
  const [open, setOpen] = useState(false);

  const handleChange = (idx) => {
    if (!disableOptions[idx]) {
      setSelected(idx);
      setErrorMsg("");
      handleSelection(idx);
    }
  };

  const handleDropdownChange = (e) => {
    if (!subOptions[options[e.target.value]]) handleChange(e.target.value);
  };

  useEffect(() => {
    // initialSelected needs to be the index of item
    if (initialSelected != null) {
      handleChange(initialSelected);
    }
  }, []);

  useEffect(() => {
    /*
     Sensitive function, this was added to control opening and closing of popup dropdown so that opening an accordion-style item doesn't auto close the dropdown. Material UI applies a modal backdrop that prevents ability to use a ClickAwayListener so applying click event to window and removing when closed.
    */
    if (window !== undefined) {
      if (open) window.addEventListener("click", handleDropdownState);
    }
    return () => window.removeEventListener("click", handleDropdownState);
  }, [open]);

  useEffect(() => {
    if (reset) {
      setSelected(initialSelected != null ? initialSelected : "");
    }
  }, [reset]);

  const handleDropdownState = (e) => {
    const option = e.target.innerText;
    if (subOptions[option] && !disableOptions[options.indexOf(option)]) {
      setSelected(options.indexOf(option));
    } else {
      /* Clicking on the select-dropdown to open will trigger this event and without this check, it will auto close and prevent dropdown from ever opening. If user selects outside select-dropdown component, then we want to close the modal */
      if (e.target.id !== "select-dropdown") {
        setOpen(false);
      }
    }
  };

  const handleSubChange = (option, subIdx) => {
    handleSubSelection({ [option]: subIdx });
  };

  const getDisabledListItem = (tooltipOptions, idx, item) => {
    return (
      <Tooltip key={idx} title={<TooltipText>{tooltipOptions[idx]}</TooltipText>} value={idx}>
        <div>
          <ListItem disabled={true}>{item}</ListItem>
        </div>
      </Tooltip>
    );
  };

  return (
    <FormControl
      fullWidth
      disabled={disabled}
      onClick={() => setOpen(true)}
      sx={{
        boxShadow:
          "0px 5px 5px -3px rgb(0 0 0 / 30%), 0px 8px 10px 1px rgb(0 0 0 / 20%), 0px 3px 14px 2px rgb(0 0 0 / 12%)",
      }}
    >
      <Select
        displayEmpty
        labelId="select-label"
        id="select-dropdown"
        input={<OutlinedComp />}
        MenuProps={MenuProps}
        onChange={handleDropdownChange}
        open={open}
        value={options[selected] ? selected : ""}
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
          if (disableOptions[idx]) return getDisabledListItem(optionsTooltipText, idx, item);
          else if (subOptions[item] && subOptions[item].length > 0)
            return (
              <Accordion key={idx} value={idx} onClick={() => setSelected(0)}>
                <AccordionTab expandIcon={<ExpandMoreIcon />} id={`${item}-dropdown`}>
                  {item}
                </AccordionTab>
                <AccordionDetails>
                  {subOptions[item].map((option, idx) => {
                    if (disableSubOptions[item][idx]) {
                      return getDisabledListItem(subOptionsTooltipText, idx, option);
                    } else
                      return (
                        <SubListItem
                          key={idx}
                          value={idx}
                          onClick={(e) => {
                            e.preventDefault();
                            handleSubChange(item, idx);
                          }}
                        >
                          {option}
                        </SubListItem>
                      );
                  })}
                </AccordionDetails>
              </Accordion>
            );
          else
            return (
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
