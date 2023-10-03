import Checkbox from "@mui/material/Checkbox";

export default function CheckboxWidget({ handleCheckbox, color, size, checkedState, disabled = false }) {
  return (
    <div>
      <Checkbox
        color={color}
        size={size}
        disabled={disabled}
        checked={checkedState}
        onChange={(e) => handleCheckbox(e.target.checked)}
      />
    </div>
  );
}
