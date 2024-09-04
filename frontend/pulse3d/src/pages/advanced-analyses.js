import DashboardLayout from "@/components/layouts/DashboardLayout";
import Table from "@/components/table/Table";

export default function AdvancedAnalyses() {}

AdvancedAnalyses.getLayout = (page) => {
  return <DashboardLayout>{page}</DashboardLayout>;
};
