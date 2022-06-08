import { createContext, useState, useEffect } from "react";
import { useWorker } from "@/components/hooks/useWorker";
import { useRouter } from "next/router";
export const WorkerContext = createContext();
export const { Consumer } = WorkerContext;

export function WorkerWrapper({ children }) {
  const [reqParams, setReqParams] = useState({});
  const [loginStatus, setLoginStatus] = useState(false); // Shallow user auth status to pass down. Still handled in web worker.
  const { error, response } = useWorker(reqParams);
  const router = useRouter();

  // Catch all for all unauthorized routes for now. Immediately redirects to login page.
  useEffect(() => {
    if (error && error.status === 401 && router.pathname !== "/login") {
      router.push("/login"); // routes back to login page when receiving unauthorized and not already on login
      setLoginStatus(false);
    }
  }, [error]);

  return (
    <WorkerContext.Provider
      value={{
        reqParams,
        setReqParams,
        loginStatus,
        setLoginStatus,
        error,
        response,
        router,
      }}
    >
      {children}
    </WorkerContext.Provider>
  );
}
