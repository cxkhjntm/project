import { Outlet, NavLink } from 'react-router-dom';

const navItems = [
  { path: '/', label: '首页', icon: '🏠' },
  { path: '/settings', label: 'Provider', icon: '⚙️' },
  { path: '/role-cards', label: '角色卡', icon: '👤' },
  { path: '/rooms', label: '讨论室', icon: '💬' },
];

export default function Layout() {
  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <NavLink to="/" className="flex items-center space-x-2">
              <span className="text-xl font-bold text-gray-900">专家团</span>
            </NavLink>

            <nav className="flex space-x-1">
              {navItems.map((item) => (
                <NavLink
                  key={item.path}
                  to={item.path}
                  end={item.path === '/'}
                  className={({ isActive }) =>
                    `px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                      isActive
                        ? 'bg-gray-900 text-white'
                        : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
                    }`
                  }
                >
                  <span className="mr-1.5">{item.icon}</span>
                  {item.label}
                </NavLink>
              ))}
            </nav>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <Outlet />
      </main>
    </div>
  );
}
