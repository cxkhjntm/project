import { RouterProvider } from 'react-router-dom';
import { router } from './routes';

export default function App() {
  return (
    <RouterProvider
      router={router}
      fallbackElement={
        <div className="flex min-h-screen items-center justify-center bg-slate-50 text-sm text-slate-500">
          加载中...
        </div>
      }
    />
  );
}
