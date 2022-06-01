import ControlPanel from "@/components/ControlPanel";
import UploadForm from "@/components/UploadForm";
import styled from "styled-components";

const Container = styled.div`
  height: inherit;
  width: inherit;
  background-color: white;
  display: flex;
`;

// TODO when creating this page, we'll need to add staticProps to prevent users from adding extension to redirect to page without logging in
export default function Uploads() {
  return (
    <Container>
      <ControlPanel />
      <UploadForm />
    </Container>
  );
}
