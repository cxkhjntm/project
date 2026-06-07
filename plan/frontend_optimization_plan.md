# 专家团前端界面视觉与交互优化详细计划

此文档提供了对专家团（AI专家工作台）前端项目实施**「简约+玻璃态水蓝色」**视觉升级的详细代码级指导。本计划专为后续AI/开发人员执行代码修复和样式重构编写。

---

## 1. 基础样式与 Tailwind 配置升级

### 1.1 修改 `project/frontend/tailwind.config.js`
在配置中引入水蓝色（Aqua-blue）体系及自定义的快响应动画/阴影类。

```javascript
/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#eff6ff',
          100: '#dbeafe',
          200: '#bfdbfe',
          300: '#93c5fd',
          400: '#60a5fa',
          500: '#3b82f6',
          600: '#2563eb',
          700: '#1d4ed8',
          800: '#1e40af',
          900: '#1e3a8a',
          950: '#172554',
        },
        // 添加水蓝色（Aqua-blue）体系
        aqua: {
          50: '#f0fdfa',
          100: '#ccfbf1',
          200: '#99f6e4',
          300: '#5eead4',
          400: '#2dd4bf',
          500: '#14b8a6',
          600: '#0d9488',
          700: '#0f766e',
          800: '#115e59',
          900: '#134e4a',
          950: '#042f2e',
        },
        expert: {
          orchestrator: '#8b5cf6',
          pm: '#3b82f6',
          architect: '#10b981',
          doc: '#f59e0b',
        },
      },
      // 引入极致响应（Snappy）的 150ms 缓动时间与自定义阴影
      transitionDuration: {
        'snappy': '150ms',
      },
      transitionTimingFunction: {
        'snappy': 'cubic-bezier(0.16, 1, 0.3, 1)', // 快速启动并平滑减速
      },
      boxShadow: {
        'glass': '0 8px 32px 0 rgba(148, 163, 184, 0.08)',
        'glass-hover': '0 12px 40px 0 rgba(14, 165, 233, 0.12)',
        'glow-aqua': '0 0 15px 1px rgba(45, 212, 191, 0.2)',
      },
      animation: {
        'shimmer': 'shimmer 2s infinite',
        'thinking': 'thinking 1.5s ease-in-out infinite',
        'float-slow': 'floatSlow 12s ease-in-out infinite',
        'float-reverse': 'floatReverse 16s ease-in-out infinite',
      },
      keyframes: {
        shimmer: {
          '0%': { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
        thinking: {
          '0%, 100%': { opacity: '0.4' },
          '50%': { opacity: '1' },
        },
        floatSlow: {
          '0%, 100%': { transform: 'translate(0px, 0px) scale(1)' },
          '50%': { transform: 'translate(40px, -60px) scale(1.1)' },
        },
        floatReverse: {
          '0%, 100%': { transform: 'translate(0px, 0px) scale(1)' },
          '50%': { transform: 'translate(-50px, 50px) scale(0.95)' },
        },
      },
    },
  },
  plugins: [],
}
```

### 1.2 修改 `project/frontend/src/styles/globals.css`
加入玻璃态核心全局样式、全局呼吸光效背景规则：

```css
@import './expert-colors.css';

@tailwind base;
@tailwind components;
@tailwind utilities;

:root {
  font-family: Inter, system-ui, Avenir, Helvetica, Arial, sans-serif;
  line-height: 1.5;
  font-weight: 400;
  color-scheme: light;
  font-synthesis: none;
  text-rendering: optimizeLegibility;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

body {
  min-height: 100vh;
  /* 采用极淡的浅灰蓝背景色 */
  background-color: #f8fafc;
  background-image: radial-gradient(at 0% 0%, rgba(240, 253, 250, 0.5) 0px, transparent 50%),
                    radial-gradient(at 100% 100%, rgba(239, 246, 255, 0.4) 0px, transparent 50%);
}

#root {
  width: 100%;
  min-height: 100vh;
}

/* 玻璃态面板通用原子样式 */
.glass-panel {
  background: rgba(255, 255, 255, 0.65);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid rgba(226, 232, 240, 0.6);
}

.glass-panel-darker {
  background: rgba(255, 255, 255, 0.75);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border: 1px solid rgba(203, 213, 225, 0.5);
}

/* 隐藏滚动条但保留滚动功能，优化工作台清透感 */
.no-scrollbar::-webkit-scrollbar {
  display: none;
}
.no-scrollbar {
  -ms-overflow-style: none;
  scrollbar-width: none;
}
```

---

## 2. 局部及全局导航布局优化

### 2.1 重构 `project/frontend/src/components/shared/Layout.tsx`
将页头改为玻璃态半透明，并将激活菜单态调整为水蓝色药丸状/气泡：

```tsx
// 修改 Layout 页头和导航链接部分
export default function Layout() {
  return (
    <div className="min-h-screen bg-transparent">
      {/* 玻璃态顶部导航 */}
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
```

---

## 3. 卡片与列表组件升级

### 3.1 改造主页 `project/frontend/src/pages/HomePage.tsx`
将主页卡片列表全部重构为清透的玻璃卡片形态，去除单调的亮绿/亮紫底色。

```tsx
const cards = [
  {
    title: 'Provider 设置',
    description: '配置 LLM API 提供商，管理 API 密钥和模型参数',
    path: '/settings',
    icon: '⚙️',
    // 改造为使用透明玻璃态与水蓝色激活边框的卡片样式
    color: 'hover:border-sky-300 hover:shadow-glass-hover',
  },
  {
    title: '角色卡管理',
    description: '创建和管理专家角色卡，定义专业领域和行为约束',
    path: '/role-cards',
    icon: '👤',
    color: 'hover:border-emerald-300 hover:shadow-glass-hover',
  },
  {
    title: '专家讨论室',
    description: '创建讨论室，邀请专家协作完成任务',
    path: '/rooms',
    icon: '💬',
    color: 'hover:border-purple-300 hover:shadow-glass-hover',
  },
];

// 卡片组件渲染部分
{cards.map((card) => (
  <Link
    key={card.path}
    to={card.path}
    className={`block p-6 rounded-2xl glass-panel shadow-glass transition-all duration-snappy ease-snappy transform hover:-translate-y-1 ${card.color}`}
  >
    <div className="text-3xl mb-4">{card.icon}</div>
    <h2 className="text-lg font-semibold text-slate-800 mb-2">
      {card.title}
    </h2>
    <p className="text-slate-500 text-sm leading-relaxed">
      {card.description}
    </p>
  </Link>
))}
```

### 3.2 改造 `project/frontend/src/components/role-card/RoleCardList.tsx`
将角色卡展示重构为精细的玻璃片设计，标签和按钮均提升美观度。

```tsx
// 优化后单张卡片结构示例
<div
  key={roleCard.id}
  className="glass-panel rounded-2xl p-5 shadow-glass hover:shadow-glass-hover hover:border-aqua-300 transition-all duration-snappy ease-snappy"
>
  <div className="flex items-start justify-between">
    <div className="flex-1 min-w-0">
      <div className="flex items-center space-x-2 mb-1.5">
        <h3 className="text-lg font-semibold text-slate-800 truncate">
          {roleCard.name}
        </h3>
        {roleCard.is_builtin && (
          <span className="inline-flex items-center px-2 py-0.5 rounded-lg text-xs font-medium bg-aqua-500/10 text-aqua-700 border border-aqua-500/10">
            内置
          </span>
        )}
        <span className="inline-flex items-center px-2 py-0.5 rounded-lg text-xs font-medium bg-slate-100 text-slate-600">
          温度: {roleCard.temperature}
        </span>
      </div>

      <p className="text-sm text-slate-500 mb-3 line-clamp-2 leading-relaxed">
        {roleCard.description}
      </p>

      {/* 技能标签改用水蓝色低饱度和半透明背景 */}
      <div className="flex flex-wrap gap-1.5 mb-3">
        {roleCard.expertise.slice(0, 5).map((item, i) => (
          <span
            key={i}
            className="inline-flex items-center px-2.5 py-0.5 rounded-lg text-xs font-medium bg-aqua-500/5 text-aqua-600 border border-aqua-500/10"
          >
            {item}
          </span>
        ))}
      </div>
    </div>
    
    {/* 按钮群组重构，去除了过硬的深色调，更换为精致的低饱和玻璃材质按钮 */}
    <div className="flex items-center space-x-2 ml-4">
      <button
        onClick={() => onPreview(roleCard)}
        className="px-3.5 py-2 text-xs font-medium text-aqua-700 bg-aqua-500/5 border border-aqua-500/20 rounded-xl hover:bg-aqua-500/10 transition-colors duration-snappy"
      >
        预览
      </button>
      {/* 其他按钮类似重构 */}
    </div>
  </div>
</div>
```

---

## 4. 专家讨论室沉浸式工作台（Discussion Room）重构

### 4.1 修改 `project/frontend/src/pages/DiscussionPage.tsx`
这是核心优化页面，要求增加漂浮的动态呼吸光晕，并将界面包裹改造成全悬浮玻璃质感。

- **动态呼吸光斑注入**：在 `DiscussionPage` 的最外层容器（要求为 `relative overflow-hidden`）内部注入背景光效：
```tsx
return (
  <div className="flex flex-col h-screen bg-slate-900/5 relative overflow-hidden">
    {/* 背景动态呼吸光斑 */}
    <div className="absolute top-12 left-12 w-96 h-96 bg-aqua-300/10 rounded-full blur-[100px] animate-float-slow pointer-events-none" />
    <div className="absolute bottom-12 right-12 w-[450px] h-[450px] bg-purple-300/10 rounded-full blur-[120px] animate-float-reverse pointer-events-none" />

    {/* Header - 半透明吸顶玻璃 */}
    <div className="bg-white/65 backdrop-blur-md border-b border-slate-200/30 px-6 py-3.5 shrink-0 z-10 flex items-center justify-between">
      {/* 状态与控制按钮 */}
    </div>

    {/* 主内容区域 - 左右浮动双面板 */}
    <div className="flex flex-1 overflow-hidden p-4 gap-4 z-10">
      {/* 左侧侧边栏组件 - 挂载单独的玻璃外观类 */}
      <ParticipantSidebar
        participants={roomData?.participants || []}
        currentSpeaker={currentSpeaker}
        status={status}
      />

      {/* 右侧聊天区域 - 用单独的玻璃面板包裹 */}
      <div className="flex-1 flex flex-col overflow-hidden glass-panel-darker rounded-2xl shadow-glass">
        {/* 对话列表与输入框 */}
      </div>
    </div>
  </div>
);
```

### 4.2 改造 `project/frontend/src/components/discussion/ParticipantSidebar.tsx`
改变侧边栏为符合主界面的卡片状：

```tsx
export const ParticipantSidebar: React.FC<ParticipantSidebarProps> = ({
  participants,
  currentSpeaker,
  status,
}) => {
  return (
    <div className="w-64 glass-panel rounded-2xl flex flex-col h-full shrink-0 shadow-glass overflow-hidden">
      <div className="px-4 py-3 border-b border-slate-200/30">
        <h3 className="text-sm font-semibold text-slate-800">参与专家</h3>
        <p className="text-xs text-slate-400 mt-0.5">{participants.length} 位已加入</p>
      </div>

      <div className="flex-1 overflow-y-auto py-2">
        {participants.map((p) => {
          const isSpeaking = currentSpeaker === p.role_card_name;
          return (
            <div
              key={p.role_card_id}
              className={`
                flex items-center gap-3 px-3 py-2.5 mx-2 my-1 rounded-xl transition-all duration-snappy ease-snappy
                ${isSpeaking 
                  ? 'bg-aqua-500/10 border border-aqua-300/40 shadow-sm shadow-aqua-500/5' 
                  : 'hover:bg-slate-100/40 border border-transparent'}
              `}
            >
              {/* 专家详情 */}
            </div>
          );
        })}
      </div>
    </div>
  );
};
```

### 4.3 改造 `project/frontend/src/components/discussion/MessageBubble.tsx`
重写消息气泡样式，强调半透明玻璃质感与专家的发光边界：

```tsx
// 1. 用户气泡：更换为渐变清透水蓝，具有科技感
if (isUser) {
  return (
    <div className="flex justify-end mb-4">
      <div className="max-w-[75%] bg-gradient-to-br from-sky-500 to-aqua-500 text-white rounded-2xl rounded-tr-sm px-4.5 py-3 shadow-md shadow-sky-500/10 border border-sky-400/20">
        <div className="text-sm leading-relaxed">{message.content}</div>
        <div className="text-[10px] text-sky-100 mt-1 text-right">
          {message.round ? `第 ${message.round} 轮生效` : ''}
        </div>
      </div>
    </div>
  );
}

// 2. 主持人（Orchestrator）气泡：使用淡淡的主持人专用色与水蓝玻璃渐变
if (isOrchestrator) {
  return (
    <div className="flex justify-center mb-4">
      <div className="bg-indigo-500/5 backdrop-blur-sm border border-indigo-200/30 rounded-2xl px-5 py-3 max-w-[80%] shadow-sm text-center">
        <div className="text-xs text-indigo-500 font-semibold mb-1">
          🎯 主持人 · 第 {message.round} 轮讨论
        </div>
        <div className="text-sm text-slate-700 font-medium leading-relaxed">{message.content}</div>
      </div>
    </div>
  );
}

// 3. 专家气泡：具有单独的阴影和色彩微弱侧边发光，磨砂质感
return (
  <div className="flex justify-start mb-4">
    <div className="max-w-[80%] rounded-2xl bg-white/70 backdrop-blur-sm shadow-glass border border-slate-200/30 overflow-hidden hover:border-aqua-300/40 transition-colors duration-snappy">
      {/* 用细线及淡淡的背景色突出专家的色彩属性 */}
      <div className="w-[4px] float-left h-full min-h-[60px]" style={{ backgroundColor: expertColor }} />
      <div className="px-4 py-3">
        <div className="flex items-center gap-2 mb-1.5">
          <span className="text-base">{emoji}</span>
          <span className="text-sm font-semibold text-slate-800">
            {resolvedName}
          </span>
          <span className="text-xs text-slate-400">第 {message.round} 轮</span>
        </div>
        <div className="text-slate-700 whitespace-pre-wrap text-sm leading-relaxed">{message.content}</div>
      </div>
    </div>
  </div>
);
```

---

## 5. 表单、输入框与控制面板（补漏）

### 5.1 聊天输入区 `project/frontend/src/components/discussion/UserInputBar.tsx`
原有的输入区域是死板的白色底栏，需重构为沉浸式的浮动毛玻璃输入舱（Floating Glass Pill）。

```tsx
export const UserInputBar: React.FC<UserInputBarProps> = ({ /* ... */ }) => {
  return (
    // 移除边框和实色背景，改为浮动毛玻璃
    <div className="px-6 py-4 bg-transparent shrink-0">
      <div className="flex items-end gap-3 glass-panel rounded-2xl p-2.5 shadow-glass-hover border border-slate-200/40">
        <textarea
          // ... 其他属性保持不变
          className="flex-1 resize-none bg-transparent px-3 py-2 text-sm text-slate-800
                     focus:outline-none placeholder:text-slate-400 no-scrollbar"
        />
        <button
          // 发送按钮更新为微发光的水蓝色渐变按钮
          className="px-5 py-2.5 text-sm font-medium text-white bg-gradient-to-r from-aqua-500 to-sky-500 rounded-xl
                     hover:from-aqua-400 hover:to-sky-400 focus:outline-none focus:ring-2 focus:ring-offset-2
                     focus:ring-aqua-500 disabled:opacity-50 disabled:cursor-not-allowed shadow-md shadow-aqua-500/20
                     transition-all duration-snappy shrink-0"
        >
          {isSending ? '发送中...' : '发送'}
        </button>
      </div>
      <p className="text-xs text-slate-400 mt-2 text-center">
        Enter 发送 · Shift+Enter 换行
      </p>
    </div>
  );
};
```

### 5.2 弹窗与抽屉（Modals & Drawers）
包括 `RoleCardForm` 的弹窗和 `DiscussionPage` 右侧的历史记录抽屉，需要替换生硬的黑色背景和纯白面板。

**模态框遮罩（Backdrop）**：
- 替换所有的 `bg-black bg-opacity-50` 为 `bg-slate-900/40 backdrop-blur-sm transition-all duration-snappy`。

**面板主体（Panel Body）**：
- 替换纯白面板 `bg-white shadow-xl` 为 `glass-panel-darker shadow-glass-hover border border-slate-200/50`。

### 5.3 配置页与新建表单 (`SettingsPage.tsx`, `RoomCreatePage.tsx`)
所有的纯输入框 `<input>` 和 `<select>` 也应该融入整个主题。
- **输入框样式**：从 `border-gray-300 focus:border-primary-500` 变更为 `bg-slate-50/50 border-slate-200/60 focus:bg-white focus:border-aqua-400 focus:ring-aqua-400/20 rounded-xl transition-all duration-snappy`。
- **表单区块背景**：表单外部包裹层同样采用 `.glass-panel`，赋予表单悬浮清透的高级质感。

---

## 6. 动画与微交互打磨

在所有的 `className` 中，确保对状态转变涉及的属性（如：`hover:border-*`, `hover:bg-*`, `hover:shadow-*`）搭配：
- `transition-all duration-snappy ease-snappy` 

这可使原本生硬的代码切换呈现清脆、高响应的微动态效果。同时修复 `ThinkingIndicator`（打字指示器）的跳动感，使其变为柔和的水波呼吸。

完成以上所有界面的无死角修改后，通过本地运行 `npm run dev` 即可完整呈现精细度大幅上升的玻璃质感 AI 工作台。
