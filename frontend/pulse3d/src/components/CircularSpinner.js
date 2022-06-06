import * as React from "react";
import CircularProgress from "@mui/material/CircularProgress";
import Box from "@mui/material/Box";

export default function CircularSpinner({ color, size }) {
  return (
    <Box sx={{ display: "flex" }}>
      <CircularProgress color={color} size={size} />
    </Box>
  );
}
