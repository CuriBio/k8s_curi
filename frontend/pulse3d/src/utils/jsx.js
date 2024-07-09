import styled from "styled-components";
import Tooltip from "@mui/material/Tooltip";

const TooltipText = styled.span`
  font-size: 15px;
`;

const getShortUUIDWithTooltip = (uuid, numChars = 8) => {
  return (
    <Tooltip title={<TooltipText>{uuid}</TooltipText>}>
      <div>
        {uuid.slice(0, numChars)}...{uuid.slice(-numChars)}
      </div>
    </Tooltip>
  );
};

export { getShortUUIDWithTooltip };
