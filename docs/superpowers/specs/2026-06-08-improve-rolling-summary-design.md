# 改进滚动摘要机制设计

## 整体目标
改进`build_rolling_summary`方法，保留第一轮讨论的完整内容，后续轮次只保留关键信息，控制总长度在`max_summary_tokens`内。

## 修改文件
1. `backend/app/services/context_builder.py`
2. `backend/app/services/orchestrator.py`
3. `backend/tests/test_context_builder.py`

## 具体要求

### 1. 修改 `context_builder.py`
- 修改 `build_rolling_summary` 方法签名，添加 `first_round_messages` 参数
- 保留第一轮讨论的完整内容
- 后续轮次只保留关键信息（前200字）
- 控制总长度在 `max_summary_tokens` 内

### 2. 修改 `orchestrator.py`
- 修改 `_update_rolling_summary` 方法
- 获取第一轮消息并传递给 `build_rolling_summary`

### 3. 摘要结构
- `## 第一轮讨论（完整）` - 第一轮完整内容
- `## 历史讨论摘要` - 已有摘要
- `## 最新讨论` - 本轮新消息

## 实现细节

### `build_rolling_summary` 方法
```python
def build_rolling_summary(
    self,
    existing_summary: str,
    new_messages: List[Dict[str, Any]],
    first_round_messages: Optional[List[Dict[str, Any]]] = None,
) -> str:
    # 构建摘要结构
    sections = []
    
    # 第一轮讨论（完整）
    if first_round_messages:
        first_round_content = "\n".join(
            f"[{msg.get('sender_id', msg.get('sender_type', '未知'))}]: {msg.get('content', '')}"
            for msg in first_round_messages
        )
        sections.append(f"## 第一轮讨论（完整）\n{first_round_content}")
    
    # 历史讨论摘要
    if existing_summary:
        sections.append(f"## 历史讨论摘要\n{existing_summary}")
    
    # 最新讨论
    if new_messages:
        new_points = []
        for msg in new_messages:
            sender = msg.get("sender_id", msg.get("sender_type", "未知"))
            content = msg.get("content", "")
            if len(content) > 200:
                content = content[:200] + "..."
            new_points.append(f"[{sender}]: {content}")
        new_summary = "\n".join(new_points)
        sections.append(f"## 最新讨论\n{new_summary}")
    
    combined = "\n\n".join(sections)
    
    # 控制总长度
    max_chars = self.max_summary_tokens * self.chars_per_token
    if len(combined) > max_chars:
        # 优先保留第一轮和最新讨论，截断历史摘要
        # 计算第一轮和最新讨论的长度
        first_round_len = len(sections[0]) if first_round_messages else 0
        latest_len = len(sections[-1]) if new_messages else 0
        
        # 计算可用于历史摘要的空间
        available_for_history = max_chars - first_round_len - latest_len - 4  # 4 for separators
        
        if available_for_history > 0 and existing_summary:
            # 截断历史摘要
            truncated_history = existing_summary[:available_for_history] + "..."
            sections[1] = f"## 历史讨论摘要\n{truncated_history}"
        elif existing_summary:
            # 如果没有空间给历史摘要，移除它
            sections.pop(1)
        
        combined = "\n\n".join(sections)
        
        # 如果仍然超过限制，截断最新讨论
        if len(combined) > max_chars:
            available_for_latest = max_chars - first_round_len - 4
            if available_for_latest > 100 and new_messages:
                truncated_latest = ""
                for msg in new_messages:
                    sender = msg.get("sender_id", msg.get("sender_type", "未知"))
                    content = msg.get("content", "")
                    if len(content) > 200:
                        content = content[:200] + "..."
                    line = f"[{sender}]: {content}\n"
                    if len(truncated_latest) + len(line) <= available_for_latest:
                        truncated_latest += line
                    else:
                        break
                sections[-1] = f"## 最新讨论\n{truncated_latest.rstrip()}"
                combined = "\n\n".join(sections)
    
    return combined
```

### `_update_rolling_summary` 方法
```python
async def _update_rolling_summary(self) -> None:
    from app.services.message_service import message_service
    from app.services.context_builder import context_builder
    
    # 获取第一轮消息
    first_round_messages = await message_service.get_by_room(
        self.session,
        self.room_id,
        round=1,
    )
    
    # 获取当前轮次消息
    current_messages = await message_service.get_by_room(
        self.session,
        self.room_id,
        round=self.current_round,
    )
    
    # 转换为字典格式
    first_round_dicts = [
        {
            "sender_type": m.sender_type,
            "sender_id": m.sender_id,
            "content": m.content,
        }
        for m in first_round_messages
    ]
    
    current_dicts = [
        {
            "sender_type": m.sender_type,
            "sender_id": m.sender_id,
            "content": m.content,
        }
        for m in current_messages
    ]
    
    self.rolling_summary = context_builder.build_rolling_summary(
        existing_summary=self.rolling_summary,
        new_messages=current_dicts,
        first_round_messages=first_round_dicts,
    )
```

## 测试要求
- 测试第一轮消息完整保留
- 测试后续轮次消息截断为200字
- 测试总长度控制
- 测试摘要结构正确

## 验收标准
1. 第一轮讨论内容完整保留在摘要中
2. 后续轮次只保留前200字
3. 摘要总长度不超过`max_summary_tokens`
4. 摘要结构包含三个部分：第一轮讨论、历史摘要、最新讨论
5. 所有现有测试通过
6. 新增测试覆盖新功能