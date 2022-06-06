import DashboardLayout from "@/components/layouts/DashboardLayout";
import UploadFormComponent from "@/components/UploadForm";

export default function UploadForm({ makeRequest, response, error }) {
  return <UploadFormComponent makeRequest={makeRequest} response={response} error={error} />;
}

UploadForm.getLayout = (page) => {
  return <DashboardLayout>{page}</DashboardLayout>;
};
