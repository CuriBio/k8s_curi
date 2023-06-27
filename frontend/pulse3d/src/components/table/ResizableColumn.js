import styled from "styled-components";
const RowCell = styled.div`
  width: 100%;
  overflow: hidden;
`;
export default function ResizableColumn({ content }) {
  return <RowCell>{content}</RowCell>;
}
