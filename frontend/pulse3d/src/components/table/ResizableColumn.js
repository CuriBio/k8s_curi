import styled from "styled-components";
const RowCell = styled.div`
  padding-left: 20px;
`;
export default function ResizableColumn({ content, width }) {
  return <RowCell style={{ width: `${width}px` }}>{content}</RowCell>;
}
