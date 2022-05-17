import { useEffect, useRef, useState } from 'react';

/**
 * use worker
 */
export function useWorker(request_params) {
  const [state, setState] = useState({});
  const workerRef = useRef();
  
  // handles responses coming back from api
  useEffect(() => {
    let setStateSafe = (nextState) => setState(nextState);
    workerRef.current = new Worker(new URL('../../worker.js', import.meta.url));

    workerRef.current.onmessage = (e) => setStateSafe({ result: e.data });
    workerRef.current.onerror = () => setStateSafe({ error: 'error' });
    workerRef.current.onmessageerror = () =>
      setStateSafe({ error: 'messageerror' });

    // perform cleanup on web worker
    return () => {
      setStateSafe = () => null; // we should not setState after cleanup.
      workerRef.current.terminate();
      setState({});
    };
  }, []);

  // handles request to api
  useEffect(() => {
    workerRef.current.postMessage(request_params);
  }, [request_params]);

  return state;
}
