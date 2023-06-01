import { useEffect, useState } from "react";
import Box from "@mui/material/Box";
import TextField from "@mui/material/TextField";
import Autocomplete from "@mui/material/Autocomplete";

export default function InputDropdownWidget({
  options = [],
  width,
  label,
  reset,
  handleSelection,
  defaultIndex,
}) {
  const [selected, setSelected] = useState(options[defaultIndex] || null);

  useEffect(() => {
    if (reset) setSelected(null);
  }, [reset]);

  useEffect(() => {
    if (defaultIndex && defaultIndex !== -1) handleSelection(defaultIndex);
  }, [defaultIndex]);

  return (
    <Autocomplete
      id="input-dropdown"
      sx={{ width }}
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
