import * as React from "react";
import Checkbox from "@mui/material/Checkbox";

export default function CheckboxWidget({
  handleCheckbox,
  color,
  size,
  checkedState,
}) {
  return (
    <div>
      <Checkbox
        color={color}
        size={size}
        checked={checkedState}
        onChange={(e) => handleCheckbox(e.target.checked)}
      />
    </div>
  );
}
