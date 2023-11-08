import { useEffect, useState } from "react";
import Box from "@mui/material/Box";
import TextField from "@mui/material/TextField";
import Autocomplete from "@mui/material/Autocomplete";

export default function InputDropdownWidget({
  label,
  options = [],
  initialOption,
  handleSelection,
  reset,
  width,
  disabled = false,
}) {
  const [selected, setSelected] = useState(initialOption || null);

  useEffect(() => {
    if (reset) setSelected(null);
  }, [reset]);

  return (
    <Autocomplete
      id="input-dropdown"
      sx={{ width }}
      disabled={disabled}
      value={selected}
      options={options}
      getOptionLabel={(option) => option}
      onChange={(_, newValue) => {
        setSelected(newValue);
        handleSelection(options.indexOf(newValue));
      }}
      renderOption={(props, option) => (
        <Box component="li" {...props} key={props.id}>
          {option}
        </Box>
      )}
      renderInput={(params) => (
        <TextField
          {...params}
          label={label}
          inputProps={{
            ...params.inputProps,
            autoComplete: "new-password", // disable autocomplete and autofill
          }}
        />
      )}
    />
  );
}
