# 讨论室控制界面实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修改讨论室创建流程，添加讨论模式选择，并实现讨论室控制界面（开始、暂停、结束）

**Architecture:** 前端添加讨论室控制组件，后端添加讨论控制API端点，修改讨论室创建流程

**Tech Stack:** React, TypeScript, FastAPI, SQLAlchemy

---

## 当前问题分析

1. **讨论室创建后立即开始讨论**：当前创建讨论室后直接跳转到讨论页面并自动开始讨论
2. **缺少讨论模式选择**：RoomForm组件缺少mode和strategy字段
3. **缺少讨论控制界面**：DiscussionPage缺少开始、暂停、结束按钮

## 参考设计：酒馆ST群聊模式

根据SillyTavern的群聊模式，我们需要：
1. **角色卡设置**：描述、个性、场景等（已有）
2. **群聊模式**：切换角色卡片、合并角色卡片等
3. **自动模式**：自动回复（可选）
4. **静音角色**：暂时禁用某些角色（可选）
5. **强制发言**：手动触发特定角色回复（可选）

## 文件结构

### 前端文件
- `frontend/src/components/room/RoomForm.tsx` - 修改：添加mode和strategy字段
- `frontend/src/components/room/RoomControlPanel.tsx` - 新建：讨论控制面板
- `frontend/src/pages/RoomDetailPage.tsx` - 新建：讨论室详情页（包含控制面板）
- `frontend/src/pages/DiscussionPage.tsx` - 修改：移除自动开始逻辑
- `frontend/src/hooks/useDiscussionControl.ts` - 新建：讨论控制hook
- `frontend/src/api/client.ts` - 修改：添加讨论控制API

### 后端文件
- `backend/app/routers/discussion.py` - 修改：添加控制端点
- `backend/app/services/orchestrator.py` - 修改：添加暂停/恢复逻辑
- `backend/app/schemas/discussion.py` - 新建：讨论控制schema

---

## 任务分解

### Task 1: 修改RoomForm添加讨论模式选择

**Files:**
- Modify: `frontend/src/components/room/RoomForm.tsx`
- Modify: `frontend/src/types/index.ts`

- [ ] **Step 1: 添加mode和strategy字段到RoomForm**

```tsx
// 在RoomForm.tsx中添加状态
const [mode, setMode] = useState<RoomMode>('code_document');
const [strategy, setStrategy] = useState<RoomStrategy>('standard');

// 在表单中添加选择器
<div>
  <label className="block text-sm font-medium text-gray-700 mb-1">
    讨论模式
  </label>
  <select
    value={mode}
    onChange={e => setMode(e.target.value as RoomMode)}
    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
  >
    <option value="code_document">代码文档模式</option>
    <option value="document">纯文档模式</option>
    <option value="code">代码模式</option>
  </select>
</div>

<div>
  <label className="block text-sm font-medium text-gray-700 mb-1">
    讨论策略
  </label>
  <select
    value={strategy}
    onChange={e => setStrategy(e.target.value as RoomStrategy)}
    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
  >
    <option value="standard">标准模式</option>
    <option value="debate">辩论模式</option>
    <option value="sequential">顺序模式</option>
  </select>
</div>
```

- [ ] **Step 2: 修改handleSubmit包含mode和strategy**

```tsx
const handleSubmit = async (e: React.FormEvent) => {
  e.preventDefault();

  const participants: ParticipantInput[] = Array.from(selectedParticipants.entries()).map(
    ([roleCardId, providerId]) => ({ role_card_id: roleCardId, provider_id: providerId })
  );

  await onSubmit({
    name,
    goal,
    mode,
    strategy,
    output_directory: outputDirectory,
    round_limit: roundLimit,
    participants,
  });
};
```

- [ ] **Step 3: 添加讨论模式说明**

```tsx
const modeDescriptions: Record<RoomMode, string> = {
  code_document: '产出适合交给AI编辑器或开发人员执行的Markdown技术方案',
  document: '产出适合阅读、汇报、归档的文档或表格',
  code: '产出核心代码草案，用于快速判断技术方向是否可行',
};

const strategyDescriptions: Record<RoomStrategy, string> = {
  standard: '初步观点 + 交叉质询 + 汇总，适合大部分任务',
  debate: '多轮质询和风险检查，适合重要方案或复杂文档',
  sequential: '每个专家发言一轮后直接总结，适合简单任务',
};
```

- [ ] **Step 4: 测试表单提交**

运行前端开发服务器，测试创建讨论室表单是否正确包含mode和strategy字段。

- [ ] **Step 5: 提交更改**

```bash
git add frontend/src/components/room/RoomForm.tsx
git commit -m "feat: add mode and strategy selection to room creation form"
```

---

### Task 2: 创建讨论控制API端点

**Files:**
- Modify: `backend/app/routers/discussion.py`
- Create: `backend/app/schemas/discussion.py`

- [ ] **Step 1: 创建讨论控制schema**

```python
# backend/app/schemas/discussion.py
from pydantic import BaseModel
from typing import Optional
from enum import Enum

class DiscussionAction(str, Enum):
    START = "start"
    PAUSE = "pause"
    RESUME = "resume"
    STOP = "stop"

class DiscussionControlRequest(BaseModel):
    action: DiscussionAction
    reason: Optional[str] = None

class DiscussionStatusResponse(BaseModel):
    room_id: str
    status: str
    current_round: int
    total_rounds: int
    is_paused: bool
    can_pause: bool
    can_resume: bool
    can_stop: bool
```

- [ ] **Step 2: 添加讨论控制端点**

```python
# backend/app/routers/discussion.py
from app.schemas.discussion import DiscussionControlRequest, DiscussionStatusResponse

@router.post("/{room_id}/control")
async def control_discussion(
    room_id: str,
    request: DiscussionControlRequest,
    session: AsyncSession = Depends(get_session),
):
    """Control discussion flow (start, pause, resume, stop)."""
    result = await session.execute(
        select(Room).where(Room.id == room_id)
    )
    room = result.scalar_one_or_none()
    
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    # 根据action执行相应操作
    if request.action == "start":
        if room.status != "draft":
            raise HTTPException(status_code=400, detail="Room is not in draft state")
        room.status = "running"
    elif request.action == "pause":
        if room.status != "running":
            raise HTTPException(status_code=400, detail="Room is not running")
        room.status = "paused"
    elif request.action == "resume":
        if room.status != "paused":
            raise HTTPException(status_code=400, detail="Room is not paused")
        room.status = "running"
    elif request.action == "stop":
        if room.status not in ("running", "paused"):
            raise HTTPException(status_code=400, detail="Room cannot be stopped")
        room.status = "completed"
    
    await session.commit()
    
    return {"status": room.status, "action": request.action}

@router.get("/{room_id}/status", response_model=DiscussionStatusResponse)
async def get_discussion_status(
    room_id: str,
    session: AsyncSession = Depends(get_session),
):
    """Get discussion status."""
    result = await session.execute(
        select(Room).where(Room.id == room_id)
    )
    room = result.scalar_one_or_none()
    
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    return DiscussionStatusResponse(
        room_id=room.id,
        status=room.status,
        current_round=0,  # 需要从消息中计算
        total_rounds=room.round_limit,
        is_paused=room.status == "paused",
        can_pause=room.status == "running",
        can_resume=room.status == "paused",
        can_stop=room.status in ("running", "paused"),
    )
```

- [ ] **Step 3: 测试API端点**

使用curl或Postman测试新的API端点。

- [ ] **Step 4: 提交更改**

```bash
git add backend/app/routers/discussion.py backend/app/schemas/discussion.py
git commit -m "feat: add discussion control API endpoints"
```

---

### Task 3: 创建讨论控制Hook

**Files:**
- Create: `frontend/src/hooks/useDiscussionControl.ts`
- Modify: `frontend/src/api/client.ts`

- [ ] **Step 1: 添加API方法到client**

```typescript
// frontend/src/api/client.ts
async controlDiscussion(roomId: string, action: 'start' | 'pause' | 'resume' | 'stop') {
  const response = await fetch(`/api/rooms/${roomId}/control`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ action }),
  });
  if (!response.ok) throw new Error('Failed to control discussion');
  return response.json();
},

async getDiscussionStatus(roomId: string) {
  const response = await fetch(`/api/rooms/${roomId}/status`);
  if (!response.ok) throw new Error('Failed to get discussion status');
  return response.json();
},
```

- [ ] **Step 2: 创建useDiscussionControl hook**

```typescript
// frontend/src/hooks/useDiscussionControl.ts
import { useState, useCallback, useEffect } from 'react';
import { apiClient } from '../api/client';

interface DiscussionStatus {
  room_id: string;
  status: string;
  current_round: number;
  total_rounds: number;
  is_paused: boolean;
  can_pause: boolean;
  can_resume: boolean;
  can_stop: boolean;
}

export function useDiscussionControl(roomId: string) {
  const [status, setStatus] = useState<DiscussionStatus | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchStatus = useCallback(async () => {
    try {
      const data = await apiClient.getDiscussionStatus(roomId);
      setStatus(data);
    } catch (err) {
      console.error('Failed to fetch discussion status:', err);
    }
  }, [roomId]);

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 5000); // 每5秒刷新状态
    return () => clearInterval(interval);
  }, [fetchStatus]);

  const controlDiscussion = useCallback(async (action: 'start' | 'pause' | 'resume' | 'stop') => {
    setIsLoading(true);
    setError(null);
    try {
      await apiClient.controlDiscussion(roomId, action);
      await fetchStatus(); // 刷新状态
    } catch (err) {
      setError(err instanceof Error ? err.message : '操作失败');
    } finally {
      setIsLoading(false);
    }
  }, [roomId, fetchStatus]);

  return {
    status,
    isLoading,
    error,
    startDiscussion: () => controlDiscussion('start'),
    pauseDiscussion: () => controlDiscussion('pause'),
    resumeDiscussion: () => controlDiscussion('resume'),
    stopDiscussion: () => controlDiscussion('stop'),
    refreshStatus: fetchStatus,
  };
}
```

- [ ] **Step 3: 测试hook**

在组件中使用hook并测试状态更新。

- [ ] **Step 4: 提交更改**

```bash
git add frontend/src/hooks/useDiscussionControl.ts frontend/src/api/client.ts
git commit -m "feat: add discussion control hook and API methods"
```

---

### Task 4: 创建讨论室详情页

**Files:**
- Create: `frontend/src/pages/RoomDetailPage.tsx`
- Modify: `frontend/src/routes.tsx`

- [ ] **Step 1: 创建RoomDetailPage组件**

```tsx
// frontend/src/pages/RoomDetailPage.tsx
import { useParams, useNavigate } from 'react-router-dom';
import { useDiscussionControl } from '../hooks/useDiscussionControl';
import RoomControlPanel from '../components/room/RoomControlPanel';

export default function RoomDetailPage() {
  const { roomId } = useParams<{ roomId: string }>();
  const navigate = useNavigate();
  
  if (!roomId) {
    return <div>Room ID is required</div>;
  }

  const {
    status,
    isLoading,
    error,
    startDiscussion,
    pauseDiscussion,
    resumeDiscussion,
    stopDiscussion,
  } = useDiscussionControl(roomId);

  const handleStartDiscussion = async () => {
    await startDiscussion();
    navigate(`/rooms/${roomId}/discussion`);
  };

  return (
    <div className="max-w-4xl mx-auto p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">讨论室详情</h1>
        <p className="text-sm text-gray-500 mt-1">
          Room ID: {roomId}
        </p>
      </div>

      {error && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
          {error}
        </div>
      )}

      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <RoomControlPanel
          status={status}
          isLoading={isLoading}
          onStart={handleStartDiscussion}
          onPause={pauseDiscussion}
          onResume={resumeDiscussion}
          onStop={stopDiscussion}
        />
      </div>
    </div>
  );
}
```

- [ ] **Step 2: 添加路由**

```tsx
// frontend/src/routes.tsx
import RoomDetailPage from './pages/RoomDetailPage';

// 在路由配置中添加
{
  path: '/rooms/:roomId',
  element: <RoomDetailPage />,
},
```

- [ ] **Step 3: 测试页面导航**

测试从讨论室列表页导航到详情页。

- [ ] **Step 4: 提交更改**

```bash
git add frontend/src/pages/RoomDetailPage.tsx frontend/src/routes.tsx
git commit -m "feat: add room detail page with control panel"
```

---

### Task 5: 创建讨论控制面板组件

**Files:**
- Create: `frontend/src/components/room/RoomControlPanel.tsx`

- [ ] **Step 1: 创建RoomControlPanel组件**

```tsx
// frontend/src/components/room/RoomControlPanel.tsx
import React from 'react';

interface DiscussionStatus {
  room_id: string;
  status: string;
  current_round: number;
  total_rounds: number;
  is_paused: boolean;
  can_pause: boolean;
  can_resume: boolean;
  can_stop: boolean;
}

interface RoomControlPanelProps {
  status: DiscussionStatus | null;
  isLoading: boolean;
  onStart: () => void;
  onPause: () => void;
  onResume: () => void;
  onStop: () => void;
}

export default function RoomControlPanel({
  status,
  isLoading,
  onStart,
  onPause,
  onResume,
  onStop,
}: RoomControlPanelProps) {
  if (!status) {
    return (
      <div className="text-center py-8">
        <div className="animate-spin text-2xl mb-2">⏳</div>
        <p className="text-gray-500">加载中...</p>
      </div>
    );
  }

  const getStatusBadge = () => {
    switch (status.status) {
      case 'draft':
        return <span className="bg-gray-100 text-gray-700 px-2 py-1 rounded text-sm">草稿</span>;
      case 'running':
        return <span className="bg-green-100 text-green-700 px-2 py-1 rounded text-sm">运行中</span>;
      case 'paused':
        return <span className="bg-yellow-100 text-yellow-700 px-2 py-1 rounded text-sm">已暂停</span>;
      case 'completed':
        return <span className="bg-blue-100 text-blue-700 px-2 py-1 rounded text-sm">已完成</span>;
      case 'failed':
        return <span className="bg-red-100 text-red-700 px-2 py-1 rounded text-sm">失败</span>;
      default:
        return <span className="bg-gray-100 text-gray-700 px-2 py-1 rounded text-sm">{status.status}</span>;
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-gray-900">讨论状态</h2>
          <p className="text-sm text-gray-500">
            当前轮次: {status.current_round} / {status.total_rounds}
          </p>
        </div>
        {getStatusBadge()}
      </div>

      <div className="flex space-x-3">
        {status.status === 'draft' && (
          <button
            onClick={onStart}
            disabled={isLoading}
            className="px-4 py-2 text-sm font-medium text-white bg-green-600 border border-transparent rounded-md hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 disabled:opacity-50"
          >
            {isLoading ? '启动中...' : '开始讨论'}
          </button>
        )}

        {status.can_pause && (
          <button
            onClick={onPause}
            disabled={isLoading}
            className="px-4 py-2 text-sm font-medium text-white bg-yellow-600 border border-transparent rounded-md hover:bg-yellow-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-yellow-500 disabled:opacity-50"
          >
            {isLoading ? '暂停中...' : '暂停讨论'}
          </button>
        )}

        {status.can_resume && (
          <button
            onClick={onResume}
            disabled={isLoading}
            className="px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
          >
            {isLoading ? '恢复中...' : '恢复讨论'}
          </button>
        )}

        {status.can_stop && (
          <button
            onClick={onStop}
            disabled={isLoading}
            className="px-4 py-2 text-sm font-medium text-white bg-red-600 border border-transparent rounded-md hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 disabled:opacity-50"
          >
            {isLoading ? '停止中...' : '结束讨论'}
          </button>
        )}
      </div>

      {status.status === 'completed' && (
        <div className="p-4 bg-green-50 border border-green-200 rounded-lg">
          <p className="text-green-700 text-sm">
            讨论已完成！您可以查看讨论记录或生成最终产出。
          </p>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: 测试组件渲染**

在RoomDetailPage中测试组件渲染和按钮点击。

- [ ] **Step 3: 提交更改**

```bash
git add frontend/src/components/room/RoomControlPanel.tsx
git commit -m "feat: add room control panel component"
```

---

### Task 6: 修改DiscussionPage移除自动开始逻辑

**Files:**
- Modify: `frontend/src/pages/DiscussionPage.tsx`

- [ ] **Step 1: 修改DiscussionPage**

```tsx
// frontend/src/pages/DiscussionPage.tsx
// 移除自动开始逻辑，改为手动触发
useEffect(() => {
  if (roomId) {
    // 只加载房间数据，不自动开始讨论
    apiClient.getRoom(roomId).then((room) => {
      setRoomData(room as RoomData);
    }).catch((err) => {
      console.error('Failed to fetch room data:', err);
    });
  }
  return () => reset();
}, [roomId, reset]);

// 添加开始讨论按钮
const handleStartDiscussion = () => {
  if (roomId) {
    startDiscussion(roomId);
  }
};
```

- [ ] **Step 2: 添加开始讨论按钮**

```tsx
// 在DiscussionPage中添加开始按钮
{status === 'idle' && (
  <div className="text-center py-8">
    <p className="text-gray-500 mb-4">点击开始按钮开始讨论</p>
    <button
      onClick={handleStartDiscussion}
      className="px-6 py-3 text-sm font-medium text-white bg-green-600 border border-transparent rounded-md hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500"
    >
      开始讨论
    </button>
  </div>
)}
```

- [ ] **Step 3: 测试讨论开始流程**

测试从讨论室详情页进入讨论页面，点击开始按钮。

- [ ] **Step 4: 提交更改**

```bash
git add frontend/src/pages/DiscussionPage.tsx
git commit -m "feat: modify discussion page to manual start"
```

---

### Task 7: 修改讨论室创建流程

**Files:**
- Modify: `frontend/src/pages/RoomCreatePage.tsx`
- Modify: `frontend/src/pages/RoomsPage.tsx`

- [ ] **Step 1: 修改RoomCreatePage**

```tsx
// frontend/src/pages/RoomCreatePage.tsx
const handleCreate = async (data: RoomCreate) => {
  try {
    setIsSubmitting(true);
    setError(null);
    const room = await apiClient.createRoom(data);
    // 创建成功后跳转到讨论室详情页，而不是讨论页
    navigate(`/rooms/${room.id}`);
  } catch (err) {
    setError(err instanceof Error ? err.message : '创建讨论室失败');
  } finally {
    setIsSubmitting(false);
  }
};
```

- [ ] **Step 2: 修改RoomsPage**

```tsx
// frontend/src/pages/RoomsPage.tsx
// 修改讨论室列表项点击事件
const handleRoomClick = (roomId: string) => {
  navigate(`/rooms/${roomId}`);
};
```

- [ ] **Step 3: 测试创建流程**

测试创建讨论室后是否正确跳转到详情页。

- [ ] **Step 4: 提交更改**

```bash
git add frontend/src/pages/RoomCreatePage.tsx frontend/src/pages/RoomsPage.tsx
git commit -m "feat: modify room creation flow to detail page"
```

---

### Task 8: 集成测试和验证

**Files:**
- Test: 整个流程测试

- [ ] **Step 1: 测试完整流程**

1. 创建讨论室（选择模式和策略）
2. 跳转到讨论室详情页
3. 点击开始讨论
4. 进入讨论页面
5. 测试暂停/恢复功能
6. 测试结束讨论

- [ ] **Step 2: 验证API端点**

使用curl测试所有新的API端点。

- [ ] **Step 3: 提交最终更改**

```bash
git add .
git commit -m "feat: complete discussion room control implementation"
```

---

## 验收标准

1. ✅ 用户能在创建讨论室时选择讨论模式和策略
2. ✅ 创建讨论室后跳转到详情页，而不是直接开始讨论
3. ✅ 用户能在详情页点击"开始讨论"按钮
4. ✅ 讨论开始后能暂停和恢复
5. ✅ 用户能结束讨论
6. ✅ 讨论状态实时更新
7. ✅ 所有API端点正常工作
8. ✅ 前端界面响应式设计

## 后续扩展（参考酒馆ST）

1. **静音角色**：暂时禁用某些专家
2. **强制发言**：手动触发特定专家回复
3. **自动模式**：自动回复模式
4. **用户插话**：用户中途发言影响讨论
5. **角色卡片合并**：合并多个角色信息
