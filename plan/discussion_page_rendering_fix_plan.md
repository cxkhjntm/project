# 讨论室页面渲染 Bug 分析与修复计划

> 生成时间：2026-06-12
> 核心问题：讨论室对话显示不完整，出现空白遮挡，滚动查看已有对话时更明显
> 测试环境：QQ浏览器
> 表现：消息气泡内部出现空白区域，像白色遮罩覆盖在内容上方，导致文字被截断/部分不可见

---

## 问题总览

| # | 严重度 | Bug 描述 | 根因分类 | 涉及文件 |
|---|--------|----------|----------|----------|
| 1 | 🔴 严重 | 专家消息气泡使用 `float-left` 色条导致布局塌陷和空白 | CSS 布局 | `MessageBubble.tsx` |
| 2 | 🔴 严重 | `backdrop-filter: blur()` 在 QQ 浏览器 Chromium 内核中触发 GPU 合成层异常 | 浏览器渲染 | `MessageBubble.tsx`, `globals.css` |
| 3 | 🔴 严重 | 消息内容包含 Markdown 但使用 `whitespace-pre-wrap` 纯文本渲染 | 功能缺失 | `MessageBubble.tsx` |
| 4 | 🟡 中等 | `overflow-hidden` + `float` 组合导致气泡高度计算异常 | CSS 布局 | `MessageBubble.tsx` |
| 5 | 🟡 中等 | 自动滚动 `scrollIntoView` 干扰手动浏览，触发渲染抖动 | 滚动逻辑 | `DiscussionPage.tsx` |
| 6 | 🟡 中等 | `useMemo` 消息列表在滚动时因 streaming 状态频繁重渲染 | 性能 | `DiscussionPage.tsx` |
| 7 | 🟢 低 | 主持人消息气泡直接用 `{message.content}` 未处理 Markdown | 一致性 | `MessageBubble.tsx` |
| 8 | 🟢 低 | ThinkingIndicator 在消息到达后未及时清除导致残留空白 | 状态管理 | `useDiscussionSSE.ts` |

---

## Bug 1 🔴 `float-left` 色条导致布局塌陷

### 问题分析

**文件**: `frontend/src/components/discussion/MessageBubble.tsx` L131-165

```tsx
// L133: 外层容器设置了 overflow-hidden
<div className={`max-w-[80%] rounded-2xl bg-white/70 backdrop-blur-sm shadow-glass 
  border border-slate-200/30 overflow-hidden ...`}>
  
  // L134: 色条使用 float-left，h-full 依赖父容器高度
  <div className="w-[4px] float-left h-full min-h-[60px]" 
       style={{ backgroundColor: expertColor }} />
  
  // L135: 内容区域
  <div className="px-4 py-3">
    ...content...
  </div>
</div>
```

**根因**：
1. `float-left` 元素脱离正常文档流，**不参与父容器高度计算**
2. `h-full`（即 `height: 100%`）要求父容器有明确高度，但父容器的高度由内容撑开——形成**循环依赖**
3. 当内容很长时，`float-left` 色条的高度无法正确匹配内容高度
4. `overflow-hidden` 在父容器上建立了新的 BFC (Block Formatting Context)，`float` 元素被裁剪，但仍会与内容产生复杂的重叠关系
5. **QQ 浏览器** (基于 Chromium) 在处理 `float` + `overflow-hidden` + `backdrop-filter` 三者叠加时，合成层的裁剪区域计算有偏差，导致部分内容区域被空白覆盖

**为什么滚动时更明显**：
- 滚动触发浏览器重绘(repaint)，GPU 合成层重新计算裁剪区域
- `float` 元素的高度在重绘时可能与内容区域不同步
- `backdrop-filter` 强制创建新的合成层，叠加后产生渲染伪影

### 修复方案

**将 `float-left` 色条改为 Flexbox 布局**，彻底消除浮动带来的高度塌陷问题。

**修改文件**: `frontend/src/components/discussion/MessageBubble.tsx` L131-165

```tsx
// === 修改前 ===
return (
  <div className="flex justify-start mb-4">
    <div className={`max-w-[80%] rounded-2xl bg-white/70 backdrop-blur-sm shadow-glass 
      border border-slate-200/30 overflow-hidden hover:border-aqua-300/40 
      transition-colors duration-snappy ${isStreaming ? 'streaming-message' : ''}`}>
      <div className="w-[4px] float-left h-full min-h-[60px]" 
           style={{ backgroundColor: expertColor }} />
      <div className="px-4 py-3">
        ...
      </div>
    </div>
  </div>
);

// === 修改后 ===
return (
  <div className="flex justify-start mb-4">
    <div className={`max-w-[80%] rounded-2xl bg-white/70 backdrop-blur-sm shadow-glass 
      border border-slate-200/30 overflow-hidden hover:border-aqua-300/40 
      transition-colors duration-snappy flex ${isStreaming ? 'streaming-message' : ''}`}>
      {/* 色条：改为 flex 子项，self-stretch 自动拉满父容器高度 */}
      <div 
        className="w-1 shrink-0 self-stretch rounded-l-2xl" 
        style={{ backgroundColor: expertColor }} 
      />
      <div className="px-4 py-3 min-w-0 flex-1">
        ...
      </div>
    </div>
  </div>
);
```

**关键改动说明**：
| 改动点 | 原代码 | 新代码 | 原因 |
|--------|--------|--------|------|
| 外层容器 | 默认 block 布局 | 添加 `flex` | 启用 Flexbox |
| 色条宽度 | `w-[4px]` | `w-1`（4px） | 等价写法，更规范 |
| 色条定位 | `float-left h-full` | `shrink-0 self-stretch` | `self-stretch` 在 Flex 中自动与容器等高 |
| 色条圆角 | 无 | `rounded-l-2xl` | 与外层圆角匹配 |
| 内容区域 | `<div className="px-4 py-3">` | 添加 `min-w-0 flex-1` | 防止长文本溢出 flex 子项 |

---

## Bug 2 🔴 `backdrop-filter: blur()` 触发 GPU 合成层异常

### 问题分析

**涉及文件**:
- `MessageBubble.tsx` L97, L133 — 消息气泡上使用 `backdrop-blur-sm`
- `globals.css` L36-48 — `.glass-panel` 和 `.glass-panel-darker` 使用 `backdrop-filter: blur()`
- `DiscussionPage.tsx` L293-296 — 背景光斑使用 `blur-[100px]`
- `ThinkingIndicator.tsx` L47 — 思考指示器使用 `backdrop-blur-sm`

**根因**：

`backdrop-filter` 强制浏览器为每个使用它的元素创建一个**独立的 GPU 合成层 (Compositing Layer)**。当讨论页面有 10-20+ 条消息时：

1. **合成层爆炸**：每条消息气泡 = 1 个合成层，20 条消息 = 20+ 个合成层
2. **GPU 显存压力**：每个合成层需要独立的纹理内存，QQ 浏览器可能在显存不足时出现渲染伪影
3. **层叠顺序错误**：大量合成层的 z-index 排列可能出现交叉，导致后面的层覆盖前面的内容
4. **Chromium 合成器 Bug**：在滚动容器内存在大量 `backdrop-filter` 元素时，Chromium 的 CC (Compositor Thread) 可能错误计算可见区域的裁剪矩形(clip rect)

**验证方法**：
1. 在 Chrome DevTools → Layers 面板中查看合成层数量
2. 在 Rendering 面板中开启 "Layer borders" 查看层边界
3. 临时注释掉 `backdrop-blur-sm`，观察空白问题是否消失

### 修复方案

**策略：减少合成层数量，只在必要的地方使用 backdrop-filter**

#### 方案 A（推荐）：移除消息气泡的 backdrop-filter

**修改文件**: `frontend/src/components/discussion/MessageBubble.tsx`

```tsx
// === 修改前 ===
// L97 主持人气泡:
<div className={`bg-indigo-500/5 backdrop-blur-sm border ...`}>

// L133 专家气泡:
<div className={`... bg-white/70 backdrop-blur-sm shadow-glass ...`}>

// === 修改后 ===
// L97 主持人气泡: 移除 backdrop-blur-sm，用纯色背景替代
<div className={`bg-indigo-50 border ...`}>

// L133 专家气泡: 移除 backdrop-blur-sm，提高背景不透明度
<div className={`... bg-white shadow-glass ...`}>
```

**修改文件**: `frontend/src/components/discussion/ThinkingIndicator.tsx`

```tsx
// === 修改前 L47 ===
<div className="flex gap-3 py-4 px-4 bg-white/40 backdrop-blur-sm ...">

// === 修改后 ===
<div className="flex gap-3 py-4 px-4 bg-white/95 ...">
```

#### 方案 B（如果需要保留毛玻璃效果）：使用 `will-change` + `contain` 优化

```css
/* 在 globals.css 中添加 */
.message-bubble {
  contain: layout paint;  /* 限制重绘范围 */
  will-change: auto;      /* 不提前创建合成层 */
}

/* 只有鼠标悬停时才启用 backdrop-filter */
.message-bubble-glass {
  background: rgba(255, 255, 255, 0.95); /* 默认高不透明度 */
  transition: background-color 0.2s, backdrop-filter 0.2s;
}
.message-bubble-glass:hover {
  background: rgba(255, 255, 255, 0.7);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
}
```

---

## Bug 3 🔴 消息使用纯文本渲染，未处理 Markdown 内容

### 问题分析

**文件**: `frontend/src/components/discussion/MessageBubble.tsx` L151-153

```tsx
<div className="text-slate-700 whitespace-pre-wrap text-sm leading-relaxed">
  {message.content}    {/* ← 纯文本渲染 */}
  {isStreaming && <span className="typing-cursor" />}
</div>
```

项目已安装 `react-markdown` 和 `remark-gfm`（见 `package.json` L20-21），但**只在 `ArtifactPreview.tsx` 中使用**，讨论消息完全未使用。

**问题表现**：
- 专家消息中的 `#` 标题、`-` 列表、`**加粗**`、代码块 ``` 等 Markdown 语法以原始文本展示
- `whitespace-pre-wrap` 会保留所有空白和换行，当 Markdown 内容中有多个空行时，会产生大片空白区域
- Markdown 代码块中的 ``` 会变成可见的文本字符

### 修复方案

**修改文件**: `frontend/src/components/discussion/MessageBubble.tsx`

#### 步骤 1: 引入 react-markdown

```tsx
// 在文件顶部添加
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
```

#### 步骤 2: 创建 Markdown 渲染组件

```tsx
// 在 MessageBubble 组件之前添加
const MarkdownContent: React.FC<{ content: string; isStreaming?: boolean }> = ({ 
  content, 
  isStreaming 
}) => (
  <div className="prose prose-sm prose-slate max-w-none 
    prose-headings:text-slate-800 prose-headings:font-semibold prose-headings:mb-2 prose-headings:mt-3
    prose-p:text-slate-700 prose-p:leading-relaxed prose-p:my-1.5
    prose-li:text-slate-700 prose-li:my-0.5
    prose-code:text-indigo-600 prose-code:bg-indigo-50 prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-code:text-xs
    prose-pre:bg-slate-800 prose-pre:rounded-lg prose-pre:my-2
    prose-strong:text-slate-800
    prose-a:text-blue-600 prose-a:no-underline hover:prose-a:underline
    [&_ol]:list-decimal [&_ul]:list-disc [&_ol]:pl-5 [&_ul]:pl-5">
    <ReactMarkdown remarkPlugins={[remarkGfm]}>
      {content}
    </ReactMarkdown>
    {isStreaming && <span className="typing-cursor" />}
  </div>
);
```

> **注意**: 项目使用 TailwindCSS 但未安装 `@tailwindcss/typography` 插件（`prose` 类）。需要选择以下方案之一：
> - **方案 A**: 安装 `@tailwindcss/typography`（推荐，执行 `npm install -D @tailwindcss/typography` 并在 `tailwind.config.js` 的 plugins 中添加 `require('@tailwindcss/typography')`）
> - **方案 B**: 不安装插件，手动用自定义 CSS 样式覆盖 Markdown 元素

#### 步骤 3: 替换消息内容渲染

```tsx
// === 修改前 (L151-154) ===
<div className="text-slate-700 whitespace-pre-wrap text-sm leading-relaxed">
  {message.content}
  {isStreaming && <span className="typing-cursor" />}
</div>

// === 修改后 ===
<MarkdownContent content={message.content} isStreaming={isStreaming} />
```

同时修改主持人消息 (L101-104):

```tsx
// === 修改前 ===
<div className="text-sm text-slate-700 font-medium leading-relaxed">
  {message.content}
  {isStreaming && <span className="typing-cursor" />}
</div>

// === 修改后 ===
<MarkdownContent content={message.content} isStreaming={isStreaming} />
```

#### 步骤 4: 添加 Markdown 渲染的 CSS 样式

如果选择 **方案 B**（不安装 typography 插件），在 `globals.css` 中添加：

```css
/* Markdown 渲染样式 */
.markdown-body h1,
.markdown-body h2,
.markdown-body h3 {
  font-weight: 600;
  color: #1e293b;
  margin-top: 0.75rem;
  margin-bottom: 0.5rem;
}
.markdown-body h1 { font-size: 1.25rem; }
.markdown-body h2 { font-size: 1.125rem; }
.markdown-body h3 { font-size: 1rem; }

.markdown-body p {
  margin: 0.375rem 0;
  line-height: 1.625;
}

.markdown-body ul,
.markdown-body ol {
  padding-left: 1.25rem;
  margin: 0.375rem 0;
}

.markdown-body li {
  margin: 0.125rem 0;
}

.markdown-body code {
  background-color: #eef2ff;
  color: #4f46e5;
  padding: 0.125rem 0.375rem;
  border-radius: 0.25rem;
  font-size: 0.8125rem;
}

.markdown-body pre {
  background-color: #1e293b;
  border-radius: 0.5rem;
  padding: 0.75rem 1rem;
  margin: 0.5rem 0;
  overflow-x: auto;
}
.markdown-body pre code {
  background: none;
  color: #e2e8f0;
  padding: 0;
}

.markdown-body blockquote {
  border-left: 3px solid #94a3b8;
  padding-left: 0.75rem;
  margin: 0.5rem 0;
  color: #64748b;
}

.markdown-body table {
  width: 100%;
  border-collapse: collapse;
  margin: 0.5rem 0;
  font-size: 0.8125rem;
}
.markdown-body th,
.markdown-body td {
  border: 1px solid #e2e8f0;
  padding: 0.375rem 0.625rem;
  text-align: left;
}
.markdown-body th {
  background-color: #f8fafc;
  font-weight: 600;
}

.markdown-body hr {
  border: none;
  border-top: 1px solid #e2e8f0;
  margin: 0.75rem 0;
}

.markdown-body strong {
  font-weight: 600;
  color: #1e293b;
}
```

---

## Bug 4 🟡 `overflow-hidden` 与 `float` 组合的裁剪问题

### 问题分析

**文件**: `frontend/src/components/discussion/MessageBubble.tsx` L133

```tsx
<div className={`... overflow-hidden ...`}>
```

`overflow-hidden` 在这里有两个作用：
1. 裁剪圆角边缘的内容（配合 `rounded-2xl`）
2. 为 `float-left` 元素建立 BFC

**问题**：
- `overflow-hidden` 会裁剪超出容器范围的所有内容
- 当 `float-left` 色条的高度计算不正确时，可能导致内容区域的一部分被裁剪为空白
- 特别是当内容非常长时，浏览器在滚动中动态计算可见区域，裁剪矩形可能不准确

### 修复方案

**此 Bug 在 Bug 1 修复后自动解决**。改用 Flexbox 后不再需要 `float`，`overflow-hidden` 仅保留裁剪圆角的作用，不会影响布局。

如需额外保险，可以将 `overflow-hidden` 改为：

```tsx
// 仅裁剪圆角，不影响内容
<div className={`... overflow-clip ...`}>
```

> `overflow-clip` 与 `overflow-hidden` 的区别：
> - `overflow-hidden` 创建新的滚动容器（即使不可滚动）
> - `overflow-clip` 纯粹裁剪，不创建滚动容器，性能更好

---

## Bug 5 🟡 自动滚动干扰手动浏览

### 问题分析

**文件**: `frontend/src/pages/DiscussionPage.tsx` L150-152

```tsx
useEffect(() => {
  messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
}, [messages.length, streamingScrollTick]);
```

**问题**：
1. 每次 `messages.length` 变化（新消息到达）或 `streamingScrollTick` 变化（流式内容更新，每 100ms 一次）都会**强制滚动到底部**
2. 当用户向上翻阅历史消息时，新消息到达会立即将视口拉回底部
3. 用户反馈"查看前面的对话时出现空白"——可能正是因为自动滚动正在将页面拉走，与手动滚动产生冲突
4. `scrollIntoView({ behavior: 'smooth' })` 会触发平滑滚动动画，期间浏览器需要连续重绘，加剧了 `backdrop-filter` 合成层的渲染负担

### 修复方案

**修改文件**: `frontend/src/pages/DiscussionPage.tsx`

#### 步骤 1: 添加"是否在底部"检测

```tsx
const scrollContainerRef = useRef<HTMLDivElement>(null);
const isAtBottomRef = useRef(true);

// 监听滚动事件，判断用户是否在底部
const handleScroll = useCallback(() => {
  const el = scrollContainerRef.current;
  if (!el) return;
  // 距底部 100px 内认为"在底部"
  const threshold = 100;
  isAtBottomRef.current = el.scrollHeight - el.scrollTop - el.clientHeight < threshold;
}, []);
```

#### 步骤 2: 条件性自动滚动

```tsx
useEffect(() => {
  // 只有用户在底部时才自动滚动
  if (isAtBottomRef.current) {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }
}, [messages.length, streamingScrollTick]);
```

#### 步骤 3: 给滚动容器添加 ref 和事件监听

```tsx
// === 修改前 (L438) ===
<div className="flex-1 overflow-y-auto px-6 py-4">

// === 修改后 ===
<div 
  ref={scrollContainerRef}
  onScroll={handleScroll}
  className="flex-1 overflow-y-auto px-6 py-4"
>
```

#### 步骤 4（可选）: 添加"回到底部"按钮

当用户不在底部且有新消息时，显示一个浮动按钮：

```tsx
const [showScrollButton, setShowScrollButton] = useState(false);

// 在 handleScroll 中更新按钮显示状态
const handleScroll = useCallback(() => {
  const el = scrollContainerRef.current;
  if (!el) return;
  const threshold = 100;
  const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < threshold;
  isAtBottomRef.current = atBottom;
  setShowScrollButton(!atBottom);
}, []);

// 在消息列表底部添加按钮
{showScrollButton && (
  <button
    onClick={() => {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }}
    className="fixed bottom-24 right-8 z-20 w-10 h-10 rounded-full bg-primary-600 text-white 
               shadow-lg flex items-center justify-center hover:bg-primary-700 transition-colors"
    title="回到最新消息"
  >
    ↓
  </button>
)}
```

---

## Bug 6 🟡 streaming 状态导致频繁重渲染

### 问题分析

**文件**: `frontend/src/pages/DiscussionPage.tsx` L220-249

```tsx
const messageElements = useMemo(() => {
  // 每次 messages 引用变化都会重新计算
  ...
}, [messages, participantNameMap]);
```

**文件**: `frontend/src/hooks/useDiscussionSSE.ts` L63-67

```tsx
const flushTokenBuffer = useCallback(() => {
  tokenFlushTimeoutRef.current = null;
  setStreamingMessages({ ...tokenBufferRef.current });  // ← 每 100ms 触发一次
  setStreamingScrollTick((value) => value + 1);          // ← 触发滚动
}, []);
```

**问题链**：
1. SSE 流式数据每秒可能发送 10-20 个 token 事件
2. `flushTokenBuffer` 每 100ms 调用一次 `setStreamingMessages` 和 `setStreamingScrollTick`
3. `streamingScrollTick` 变化触发 `scrollIntoView`
4. 每次 state 变化都触发 DiscussionPage 重渲染
5. 虽然 `messageElements` 有 `useMemo`，但 `streamingMessages` 的 `Object.entries()` (L464) 在每次渲染时都会执行
6. 大量消息气泡 + `backdrop-filter` + 频繁重渲染 = 渲染性能问题

### 修复方案

#### 方案 1: 使用 `React.memo` 包裹 MessageBubble

**修改文件**: `frontend/src/components/discussion/MessageBubble.tsx`

```tsx
// === 修改前 ===
export const MessageBubble: React.FC<MessageBubbleProps> = ({ ... }) => { ... };

// === 修改后 ===
export const MessageBubble: React.FC<MessageBubbleProps> = React.memo(({ ... }) => {
  ...
});
```

#### 方案 2: 将 streaming 消息独立为子组件

**修改文件**: `frontend/src/pages/DiscussionPage.tsx`

```tsx
// 将 streaming 消息抽取为独立组件，避免整个列表重渲染
const StreamingMessages = React.memo(({ 
  streamingMessages, 
  currentRound, 
  roomId, 
  participantNameMap 
}: { ... }) => (
  <>
    {Object.entries(streamingMessages).map(([roleName, content]) => (
      <MessageBubble
        key={`stream-${roleName}`}
        message={{ ... }}
        isStreaming={true}
        participantNameMap={participantNameMap}
      />
    ))}
  </>
));
```

#### 方案 3: 降低 token flush 频率

**修改文件**: `frontend/src/hooks/useDiscussionSSE.ts`

```tsx
// === 修改前 (L71) ===
tokenFlushTimeoutRef.current = setTimeout(flushTokenBuffer, 100);

// === 修改后 ===
tokenFlushTimeoutRef.current = setTimeout(flushTokenBuffer, 200); // 200ms 足够流畅
```

---

## Bug 7 🟢 主持人消息未处理 Markdown

### 问题分析

**文件**: `frontend/src/components/discussion/MessageBubble.tsx` L94-108

主持人（orchestrator）消息也使用纯文本渲染 `{message.content}`，如果主持人消息包含 Markdown 格式（列表、强调等），同样会显示为原始文本。

### 修复方案

**在 Bug 3 修复时一并处理**，将主持人消息的 `{message.content}` 替换为 `<MarkdownContent content={message.content} />`。

---

## Bug 8 🟢 ThinkingIndicator 状态残留

### 问题分析

**文件**: `frontend/src/hooks/useDiscussionSSE.ts` L159-178

```tsx
// 当收到 expert 消息时，清除所有 thinking 状态
setThinking((prev) => {
  const next = { ...prev };
  Object.keys(next).forEach((key) => {
    if (next[key]) next[key] = false;  // ← 设为 false 而不是删除
  });
  return next;
});
```

**问题**：
- `thinking` 状态的 key 被设为 `false` 而不是删除
- DiscussionPage L270-272 过滤 `thinking` 为 `true` 的项：
  ```tsx
  const thinkingRoles = Object.entries(thinking)
    .filter(([, isThinking]) => isThinking)
    .map(([role]) => role);
  ```
- 虽然过滤后不会渲染 ThinkingIndicator，但 `thinking` 对象越来越大（所有历史角色都保留为 `false`）
- 这不会直接导致空白，但增加不必要的重渲染

### 修复方案

**修改文件**: `frontend/src/hooks/useDiscussionSSE.ts`

```tsx
// === 修改前 ===
setThinking((prev) => {
  const next = { ...prev };
  Object.keys(next).forEach((key) => {
    if (next[key]) next[key] = false;
  });
  return next;
});

// === 修改后 ===
setThinking({});  // 直接清空所有 thinking 状态
```

---

## 修复优先级与执行顺序

```
阶段 1: 核心布局修复 (Bug 1 + Bug 4) — 预计 15 分钟
  ├── 1.1 MessageBubble.tsx: float-left 改为 Flexbox
  └── 1.2 MessageBubble.tsx: overflow-hidden 改为 overflow-clip

阶段 2: GPU 渲染优化 (Bug 2) — 预计 10 分钟
  ├── 2.1 MessageBubble.tsx: 移除消息气泡的 backdrop-blur-sm
  ├── 2.2 ThinkingIndicator.tsx: 移除 backdrop-blur-sm
  └── 2.3 (可选) 添加 contain: layout paint CSS

阶段 3: Markdown 渲染 (Bug 3 + Bug 7) — 预计 30 分钟
  ├── 3.1 安装 @tailwindcss/typography（或手写 CSS）
  ├── 3.2 创建 MarkdownContent 组件
  ├── 3.3 专家消息改用 MarkdownContent
  └── 3.4 主持人消息改用 MarkdownContent

阶段 4: 滚动优化 (Bug 5) — 预计 20 分钟
  ├── 4.1 添加"是否在底部"检测
  ├── 4.2 条件性自动滚动
  └── 4.3 (可选) 添加"回到底部"浮动按钮

阶段 5: 性能优化 (Bug 6 + Bug 8) — 预计 15 分钟
  ├── 5.1 React.memo 包裹 MessageBubble
  ├── 5.2 StreamingMessages 独立组件
  ├── 5.3 降低 token flush 频率到 200ms
  └── 5.4 清理 thinking 状态的残留 key
```

---

## 文件修改清单

| 文件 | 改动类型 | 涉及 Bug |
|------|----------|----------|
| `frontend/src/components/discussion/MessageBubble.tsx` | 重构布局 + 添加 Markdown 渲染 | Bug 1, 2, 3, 4, 7 |
| `frontend/src/components/discussion/ThinkingIndicator.tsx` | 移除 backdrop-blur | Bug 2 |
| `frontend/src/pages/DiscussionPage.tsx` | 滚动优化 + 性能优化 | Bug 5, 6 |
| `frontend/src/hooks/useDiscussionSSE.ts` | 状态清理优化 | Bug 8 |
| `frontend/src/styles/globals.css` | 添加 Markdown 渲染样式 | Bug 3 |
| `frontend/tailwind.config.js` | 添加 typography 插件（如果选方案 A） | Bug 3 |
| `frontend/package.json` | 添加 @tailwindcss/typography 依赖（如果选方案 A） | Bug 3 |

---

## 验证清单

- [ ] 修复后在 QQ 浏览器中打开讨论室页面
- [ ] 发起讨论，等待 10+ 条消息后查看是否有空白
- [ ] 对话进行中手动向上翻阅历史消息，确认无空白和自动拉回
- [ ] 对话完成后上下滚动查看所有消息，确认显示完整
- [ ] 确认 Markdown 格式（标题、列表、代码块、加粗等）正确渲染
- [ ] 确认主持人消息和专家消息的左侧色条高度与内容匹配
- [ ] 打开 Chrome DevTools → Layers 面板，确认合成层数量合理（< 10）
- [ ] 快速滚动时无明显卡顿
- [ ] 流式打字效果正常，typing-cursor 光标闪烁正常
- [ ] ThinkingIndicator 在专家发言完成后立即消失
- [ ] 窗口缩放时布局正常，无溢出

---

## 附录: 根因分析图

```
用户报告: "对话显示不完整有空白"
    │
    ├── 直接原因 1: float-left 色条布局塌陷
    │   ├── float 脱离文档流，不参与父容器高度计算
    │   ├── h-full 在无明确父高度时失效
    │   └── overflow-hidden 裁剪了不正确的区域
    │
    ├── 直接原因 2: backdrop-filter GPU 合成层问题
    │   ├── 每个消息气泡创建独立合成层
    │   ├── 滚动时合成层裁剪矩形计算错误
    │   └── QQ 浏览器 Chromium 内核对 backdrop-filter 支持不佳
    │
    ├── 加剧因素: 自动滚动干扰
    │   ├── 用户翻阅时被强制拉回底部
    │   ├── smooth scroll 期间连续重绘加剧渲染负担
    │   └── 用户误以为内容消失（实际是被滚走了）
    │
    └── 加剧因素: 频繁重渲染
        ├── streaming 每 100ms 触发 state 更新
        ├── 整个消息列表重新渲染
        └── 大量 backdrop-filter 元素的重绘成本高
```
