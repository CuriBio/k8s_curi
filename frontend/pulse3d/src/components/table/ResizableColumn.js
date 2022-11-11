import styled from "styled-components";
const RowCell = styled.div`
  width: 100%;
`;
export default function ResizableColumn({ content }) {
  return <RowCell>{content}</RowCell>;
}
