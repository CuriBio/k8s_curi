import CircularProgress from "@mui/material/CircularProgress";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";

export default function CircularProgressWithLabel({
  value,
  colorOfTextLabel = "black",
  size = 40,
  fontSize,
}) {
  return (
    <Box sx={{ position: "relative", display: "inline-flex" }}>
      <CircularProgress
        variant="determinate"
        size={size}
        value={value}
        style={{ color: "var(--teal-green)" }}
      />
      <Box
        sx={{
          top: 0,
          left: 0,
          bottom: 0,
          right: 0,
          position: "absolute",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          textAlign: "center",
        }}
      >
        <Typography variant="caption" component="div" color={colorOfTextLabel} sx={{ fontSize }}>
          {`${Math.round(value)}%`}
        </Typography>
      </Box>
    </Box>
  );
}
