import { Outlet, NavLink } from 'react-router-dom';

const navItems = [
  { path: '/', label: '首页', icon: '🏠' },
  { path: '/settings', label: 'Provider', icon: '⚙️' },
  { path: '/role-cards', label: '角色卡', icon: '👤' },
  { path: '/rooms', label: '讨论室', icon: '💬' },
];

export default function Layout() {
  return (
    <div className="min-h-screen bg-transparent">
      <header className="glass-panel sticky top-0 z-50 border-b border-slate-200/40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <NavLink to="/" className="flex items-center space-x-2">
              <span className="text-xl font-bold bg-gradient-to-r from-sky-600 to-aqua-600 bg-clip-text text-transparent">
                专家团
              </span>
            </NavLink>

            <nav className="flex space-x-1.5">
              {navItems.map((item) => (
                <NavLink
                  key={item.path}
                  to={item.path}
                  end={item.path === '/'}
                  className={({ isActive }) =>
                    `px-4 py-2 rounded-xl text-sm font-medium transition-all duration-snappy ease-snappy ${
                      isActive
                        ? 'bg-aqua-500/10 text-aqua-700 border border-aqua-500/20 shadow-sm shadow-aqua-500/5'
                        : 'text-slate-600 hover:bg-slate-100/60 hover:text-slate-900 border border-transparent'
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
