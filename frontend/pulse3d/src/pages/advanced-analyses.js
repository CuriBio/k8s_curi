import DashboardLayout from "@/components/layouts/DashboardLayout";

export default function AdvancedAnalyses() {}
AdvancedAnalyses.getLayout = (page) => {
  return <DashboardLayout>{page}</DashboardLayout>;
};
