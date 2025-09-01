import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from 'react-query'
import { ToastContainer, toast } from 'react-toastify'
import App from './App.tsx'
import './index.css'
import 'react-toastify/dist/ReactToastify.css'



// Create a query client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: (failureCount: number, error: unknown) => {
        // Don't retry on 4xx errors (client errors)
        const status =
          typeof error === 'object' && error !== null && 'response' in error &&
          typeof (error as any).response?.status === 'number'
            ? (error as any).response.status
            : undefined;
        if (status && status >= 400 && status < 500) {
          return false;
        }
        // Only retry once for server errors
        return failureCount < 1;
      },
      staleTime: 5 * 60 * 1000, // 5 minutes
      onError: (error: any) => {
        // Only show toast for final error after all retries
        console.error('Query error:', error);
      }
    },
  },
})

// Custom toast function to save to history
const originalToast = { ...toast };
const saveToHistory = (type: 'success' | 'error' | 'warning' | 'info', message: string) => {
  const history = JSON.parse(localStorage.getItem('notificationHistory') || '[]');
  const newNotification = {
    id: Date.now().toString(),
    type,
    message,
    timestamp: new Date().toISOString()
  };
  const updatedHistory = [newNotification, ...history].slice(0, 50);
  localStorage.setItem('notificationHistory', JSON.stringify(updatedHistory));
};

// Override toast methods to save to history
toast.success = (content: any, options?: any) => {
  const message = typeof content === 'string' ? content : 'Success';
  saveToHistory('success', message);
  return originalToast.success(content, options);
};

toast.error = (content: any, options?: any) => {
  const message = typeof content === 'string' ? content : 'Error';
  saveToHistory('error', message);
  return originalToast.error(content, options);
};

toast.warning = (content: any, options?: any) => {
  const message = typeof content === 'string' ? content : 'Warning';
  saveToHistory('warning', message);
  return originalToast.warning(content, options);
};

toast.info = (content: any, options?: any) => {
  const message = typeof content === 'string' ? content : 'Info';
  saveToHistory('info', message);
  return originalToast.info(content, options);
};

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <App />
        <ToastContainer
          position="top-right"
          autoClose={5000}
          hideProgressBar={false}
          newestOnTop={false}
          closeOnClick
          rtl={false}
          pauseOnFocusLoss
          draggable
          pauseOnHover
          theme="dark"
          toastClassName="bg-bg-card"
        />
      </BrowserRouter>
    </QueryClientProvider>
  </React.StrictMode>,
)
