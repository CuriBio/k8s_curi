import * as React from 'react';
import CircularProgress from '@mui/material/CircularProgress';
import Box from '@mui/material/Box';
import { createTheme, ThemeProvider } from '@mui/material/styles';
import { purple } from '@mui/material/colors';
import Button from '@mui/material/Button';

export default function CircularSpinner({ color, size }) {
  const theme = createTheme({
    palette: {
      primary: {
        main: color,
      },
    },
  });

  return (
    <ThemeProvider theme={theme}>
      <Box sx={{ display: 'flex' }}>
        <CircularProgress color='primary' size={size} />
      </Box>
    </ThemeProvider>
  );
}
