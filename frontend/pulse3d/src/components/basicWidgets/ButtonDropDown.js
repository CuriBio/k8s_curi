import { useState } from "react";
import Button from "@mui/material/Button";
import Menu from "@mui/material/Menu";
import MenuItem from "@mui/material/MenuItem";
import styled from "styled-components";

const MenuLabel = styled.span`
  color: var(--light-gray);
  font-size: 19px;
  &:hover {
    color: var(--teal-green);
  }
`;

export default function DropDownMenu({ items, label, handleSelection }) {
  const [anchorEl, setAnchorEl] = useState(null);
  const open = Boolean(anchorEl);

  const handleOpen = ({ currentTarget }) => {
    setAnchorEl(currentTarget);
  };

  const handleClose = () => {
    setAnchorEl(null);
  };

  const handleClick = ({ target }) => {
    handleSelection(target.id);
    handleClose();
  };

  return (
    <div>
      <Button
        id="basic-button"
        aria-controls={open || "basic-menu"}
        aria-haspopup="true"
        aria-expanded={open || "true"}
        onClick={handleOpen}
      >
        <MenuLabel>{label}</MenuLabel>
      </Button>
      <Menu
        id="basic-menu"
        anchorEl={anchorEl}
        open={open}
        onClose={handleClose}
        MenuListProps={{
          "aria-labelledby": "basic-button",
          disablePadding: true,
        }}
      >
        {items.map((option, idx) => {
          return (
            <MenuItem key={option} id={idx} onClick={handleClick} sx={{ fontSize: "18px", padding: "1" }}>
              {option}
            </MenuItem>
          );
        })}
      </Menu>
    </div>
  );
}
