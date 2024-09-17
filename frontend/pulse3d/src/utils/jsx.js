import styled from "styled-components";
import Tooltip, { tooltipClasses } from "@mui/material/Tooltip";

const TooltipText = styled.span`
  font-size: 15px;
`;

const NoMaxWidthTooltip = styled(({ className, ...props }) => (
  <Tooltip {...props} classes={{ popper: className }} />
))({
  [`& .${tooltipClasses.tooltip}`]: {
    maxWidth: "none",
  },
});

const getShortUUIDWithTooltip = (uuid, numChars = 8) => {
  return (
    <NoMaxWidthTooltip title={<TooltipText>{uuid}</TooltipText>}>
      <div>
        {uuid.slice(0, numChars)}...{uuid.slice(-numChars)}
      </div>
    </NoMaxWidthTooltip>
  );
};

export { getShortUUIDWithTooltip };
