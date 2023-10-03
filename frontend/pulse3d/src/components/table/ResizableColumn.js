import styled from "styled-components";
const RowCell = styled.div`
  width: 100%;
  overflow: hidden;
`;
export default function ResizableColumn({ content }) {
  const getContent = (content) => {
    return Array.isArray(content) ? content.map((item) => <div key={item}>{item}</div>) : content;
  };

  return <RowCell>{getContent(content)}</RowCell>;
}
