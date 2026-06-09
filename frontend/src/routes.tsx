import { createBrowserRouter } from 'react-router-dom';
import Layout from '@/components/shared/Layout';

export const router = createBrowserRouter([
  {
    path: '/',
    element: <Layout />,
    children: [
      {
        index: true,
        lazy: async () => ({ Component: (await import('@/pages/HomePage')).default }),
      },
      {
        path: 'settings',
        lazy: async () => ({ Component: (await import('@/pages/SettingsPage')).default }),
      },
      {
        path: 'role-cards',
        lazy: async () => ({ Component: (await import('@/pages/RoleCardsPage')).default }),
      },
      {
        path: 'rooms',
        lazy: async () => ({ Component: (await import('@/pages/RoomsPage')).default }),
      },
      {
        path: 'rooms/create',
        lazy: async () => ({ Component: (await import('@/pages/RoomCreatePage')).default }),
      },
      {
        path: 'rooms/:roomId',
        lazy: async () => ({ Component: (await import('@/pages/RoomDetailPage')).default }),
      },
    ],
  },
  {
    path: '/rooms/:roomId/discussion',
    lazy: async () => ({ Component: (await import('@/pages/DiscussionPage')).default }),
  },
  {
    path: '/rooms/:roomId/artifacts',
    lazy: async () => ({ Component: (await import('@/pages/ArtifactPage')).default }),
  },
]);
