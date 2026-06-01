import { createBrowserRouter } from 'react-router-dom';
import Layout from '@/components/shared/Layout';
import HomePage from '@/pages/HomePage';
import SettingsPage from '@/pages/SettingsPage';
import RoleCardsPage from '@/pages/RoleCardsPage';
import RoomsPage from '@/pages/RoomsPage';
import RoomCreatePage from '@/pages/RoomCreatePage';
import RoomDetailPage from '@/pages/RoomDetailPage';
import DiscussionPage from '@/pages/DiscussionPage';
import ArtifactPage from '@/pages/ArtifactPage';

export const router = createBrowserRouter([
  {
    path: '/',
    element: <Layout />,
    children: [
      { index: true, element: <HomePage /> },
      { path: 'settings', element: <SettingsPage /> },
      { path: 'role-cards', element: <RoleCardsPage /> },
      { path: 'rooms', element: <RoomsPage /> },
      { path: 'rooms/create', element: <RoomCreatePage /> },
      { path: 'rooms/:roomId', element: <RoomDetailPage /> },
    ],
  },
  {
    path: '/rooms/:roomId/discussion',
    element: <DiscussionPage />,
  },
  {
    path: '/rooms/:roomId/artifacts',
    element: <ArtifactPage />,
  },
]);
