import SerialNumberTable from "@/components/table/SerialNumberTable";
import DashboardLayout from "@/components/layouts/DashboardLayout";
import styled from "styled-components";

const Container = styled.div`
  padding: 3.5rem 3.5rem;
`;

const SectionHeader = styled.div`
  padding-bottom: 10px;
  padding-left: 10px;
`;

export default function ProductionConsole() {
  return (
    <Container>
      <SectionHeader>Mantarray Serial Numbers</SectionHeader>
      <SerialNumberTable />
    </Container>
  );
}

ProductionConsole.getLayout = (page) => {
  return <DashboardLayout>{page}</DashboardLayout>;
};
