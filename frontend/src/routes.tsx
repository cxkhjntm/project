import { createBrowserRouter } from 'react-router-dom';
import Layout from '@/components/shared/Layout';
import HomePage from '@/pages/HomePage';

const PlaceholderPage = ({ title }: { title: string }) => (
  <div className="text-center py-12">
    <h2 className="text-2xl font-semibold text-gray-900 mb-2">{title}</h2>
    <p className="text-gray-600">此页面正在开发中...</p>
  </div>
);

export const router = createBrowserRouter([
  {
    path: '/',
    element: <Layout />,
    children: [
      { index: true, element: <HomePage /> },
      { path: 'settings', element: <PlaceholderPage title="Provider 设置" /> },
      { path: 'role-cards', element: <PlaceholderPage title="角色卡管理" /> },
      { path: 'rooms', element: <PlaceholderPage title="讨论室" /> },
      { path: 'rooms/:id', element: <PlaceholderPage title="讨论室详情" /> },
    ],
  },
]);
