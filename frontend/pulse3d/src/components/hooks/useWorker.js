import { useEffect, useRef, useState } from 'react';

export function useWorker(request_params = null) {
  const [state, setState] = useState({});
  const workerRef = useRef();

  // handles responses coming back from api
  useEffect(() => {
    let setStateSafe = (nextState) => setState(nextState);
    workerRef.current = new Worker(
      new URL('../../utils/worker.js', import.meta.url)
    );

    workerRef.current.onmessage = ({ data }) => {
      if (data.error) setStateSafe({ error: data.error });
      else setStateSafe({ result: data });
    };

    // perform cleanup on web worker
    return () => {
      setStateSafe = () => null; // we should not setState after cleanup.
      workerRef.current.terminate();
      setState({});
    };
  }, [workerRef]);

  // handles request to api
  useEffect(() => {
    workerRef.current.postMessage(request_params);
  }, [request_params]);

  return state;
}
