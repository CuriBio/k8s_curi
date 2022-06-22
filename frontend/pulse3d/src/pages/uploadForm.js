import DashboardLayout from "@/components/layouts/DashboardLayout";
import UploadFormComponent from "@/components/UploadForm";
export default function UploadForm() {
  return <UploadFormComponent />;
}

UploadForm.getLayout = (page) => {
  return <DashboardLayout>{page}</DashboardLayout>;
};
