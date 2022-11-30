import { useEffect, useState } from "react";
import { useRouter } from "next/router";
import UpdateAccount from "@/components/account/UpdateAccount";

export default function VerifyAccount() {
  const router = useRouter();
  const [shortTermToken, setShortTermToken] = useState();

  useEffect(() => {
    const currentPage = router.pathname;
    const { token } = router.query;
    // TODO protect these pages if no token is found
    if (token && currentPage === "/account/verify") {
      setShortTermToken(token);
    }
  }, [router]);

  return <UpdateAccount type={"verify"} shortTermToken={shortTermToken} modalHeader={"Verify Account"} />;
}
