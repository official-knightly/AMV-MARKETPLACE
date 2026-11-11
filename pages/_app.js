import '../styles/globals.css';
import { useEffect } from 'react';
import { Toaster } from 'react-hot-toast';
import { GoogleOAuthProvider } from '@react-oauth/google';
import { useAuthStore } from '../lib/store';
import { getCurrentUser } from '../lib/api';
import Navbar from '../components/Navbar';
import MarketplaceAssistant from '../components/MarketplaceAssistant';

function MyApp({ Component, pageProps }) {
  const { setAuth, setAuthReady } = useAuthStore();
  const googleClientId = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID;

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) {
      setAuthReady(true);
      return;
    }
    getCurrentUser()
      .then((res) => setAuth(res.data, token))
      .catch(() => {
        localStorage.removeItem('token');
      })
      .finally(() => setAuthReady(true));
  }, [setAuth, setAuthReady]);

  const appShell = (
    <>
      <Navbar />
      <Component {...pageProps} />
      <MarketplaceAssistant />
      <Toaster 
        position="top-right"
        toastOptions={{
          style: {
            background: '#131313',
            color: '#fff',
            border: '1px solid rgba(255,255,255,0.1)',
          },
        }}
      />
    </>
  );

  if (!googleClientId) {
    return appShell;
  }

  return (
    <GoogleOAuthProvider clientId={googleClientId}>
      {appShell}
    </GoogleOAuthProvider>
  );
}

export default MyApp;
