import DashboardLayout from "@/components/layouts/DashboardLayout";
import styled from "styled-components";

const Container = styled.div`
  display: flex;
  position: relative;
  justify-content: start;
  width: 100%;
`;

export default function UploadForm({ makeRequest, response }) {
  return <Container>Upload Form</Container>;
}

UploadForm.getLayout = (page) => {
  return <DashboardLayout>{page}</DashboardLayout>;
};
