import { useEffect } from 'react';
export default function Home() {
  // redirect user to login page
  useEffect(() => {
    Router.push('/login');
  });
  return <div></div>;
}
