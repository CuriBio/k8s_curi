import { useEffect, useRef, useState } from "react";

export function useWorker(request_params) {
  const [state, setState] = useState({});
  const workerRef = useRef();

  // handles responses coming back from apis
  useEffect(() => {
    let setStateSafe = (nextState) => setState(nextState);
    workerRef.current = new Worker(new URL("../../utils/worker.js", import.meta.url));
    workerRef.current.onmessage = ({ data }) => {
      console.log("###", data);
      data && data.error ? setStateSafe({ error: data.error }) : setStateSafe({ response: data });
    };
    workerRef.current.onerror = () => {
      setStateSafe({ error: 500 });
    };

    return () => {
      // eslint-disable-next-line react/function-component-definition
      setStateSafe = () => null; // we should not setState after cleanup.
      workerRef.current.terminate();
      setState({});
    };
    // perform cleanup on web worker
  }, [workerRef]);

  // handles request to api
  useEffect(() => {
    setState({}); // ensures change if same error/response is returned
    workerRef.current.postMessage(request_params);
  }, [request_params]);

  return state;
}
