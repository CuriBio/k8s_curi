import { useEffect, useState } from "react";
import { useRouter } from "next/router";
import UpdateAccount from "@/components/account/UpdateAccount";

export default function UpdatePassword() {
  const router = useRouter();
  const [shortTermToken, setShortTermToken] = useState();

  useEffect(() => {
    const currentPage = router.pathname;
    const { token } = router.query;

    if (token && currentPage === "/account/reset") {
      setShortTermToken(token);
    }
  }, [router]);

  return <UpdateAccount type={"reset"} shortTermToken={shortTermToken} modalHeader={"Change Password"} />;
}
