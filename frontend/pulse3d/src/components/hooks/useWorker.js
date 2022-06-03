import { useEffect, useRef, useState } from 'react';

export function useWorker(requestParams) {
  const [state, setState] = useState({});
  const worker = useRef();

  // handles responses coming back from apis
  useEffect(() => {
    let setStateSafe = (nextState) => setState(nextState);

    worker.current = new Worker(
      new URL('../../utils/worker.js', import.meta.url)
    );

    worker.current.onmessage = ({ data }) => {
      data && data.error
        ? setStateSafe({ error: data.error })
        : setStateSafe({ response: data });
    };

    worker.current.onerror = () => {
      setStateSafe({ error: 500 });
    };

    return () => {
      // eslint-disable-next-line react/function-component-definition
      setStateSafe = () => null; // we should not setState after cleanup.
      worker.current.terminate();
      setState({});
    };
  }, []);

  // handles request to api
  useEffect(() => {
    worker.current.postMessage(requestParams);
  }, [requestParams]);

  return state;
}
