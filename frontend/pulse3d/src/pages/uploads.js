import DashboardLayout from "@/components/DashboardLayout";
import UploadsTable from "@/components/UploadsTable";



export default function Uploads({ makeRequest, response }) {
  return <UploadsTable makeRequest={makeRequest} response={response} />;
}

Uploads.getLayout = (page) => {
  return <DashboardLayout>{page}</DashboardLayout>;
};
