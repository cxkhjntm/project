"""Role card service for CRUD operations."""

import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.role_card import RoleCard
from app.schemas.role_card import RoleCardCreate, RoleCardGenerateResponse, RoleCardUpdate
from app.utils.logger import get_logger

logger = get_logger(__name__)

ROLE_CARD_GENERATION_SYSTEM_PROMPT = """你是一个专业的角色卡生成助手。用户会提供一段已有的提示词或角色描述文本，请你分析这段文本，从中提取并生成一个结构化的角色卡。

请严格按以下 JSON 格式输出（不要输出任何其他内容，不要使用 markdown 代码块包裹）：
{
  "name": "角色名称（简短，2-20字）",
  "description": "角色描述（一段话概述角色定位和背景）",
  "expertise": ["专业领域1", "专业领域2"],
  "responsibilities": ["职责1", "职责2"],
  "constraints": ["约束1", "约束2"],
  "system_prompt": "完整的系统提示词（基于原文优化和完善）",
  "output_style": "输出风格描述",
  "temperature": 0.7
}

注意：
1. name 应简洁明了，2-20个字
2. expertise 和 responsibilities 至少各有 1 项
3. system_prompt 应该基于原始提示词，但可以适当优化使其更加完整和专业
4. 如果原文没有明确提到约束条件，constraints 设为 null
5. 如果原文没有明确提到输出风格，output_style 设为 null
6. temperature 根据角色类型合理设置（创意类 0.8-1.0，严谨类 0.3-0.5，通用 0.7）
7. 只输出 JSON，不要有任何额外文字"""


class RoleCardService:
    """Service for role card CRUD operations."""

    async def create(self, session: AsyncSession, data: RoleCardCreate) -> RoleCard:
        """Create a new role card.

        Args:
            session: Database session
            data: Role card creation data

        Returns:
            Created role card
        """
        import uuid

        role_card = RoleCard(
            id=str(uuid.uuid4()),
            name=data.name,
            description=data.description,
            expertise=data.expertise,
            responsibilities=data.responsibilities,
            constraints=data.constraints,
            system_prompt=data.system_prompt,
            output_style=data.output_style,
            default_provider_id=data.default_provider_id,
            default_model=data.default_model,
            temperature=data.temperature,
            is_builtin=False,
        )

        session.add(role_card)
        await session.flush()

        logger.info("Created role card", role_card_id=role_card.id, name=role_card.name)
        return role_card

    async def get_all(self, session: AsyncSession, builtin_only: bool = False) -> list[RoleCard]:
        """Get all role cards.

        Args:
            session: Database session
            builtin_only: If True, return only built-in role cards

        Returns:
            List of role cards
        """
        query = select(RoleCard).order_by(RoleCard.name)

        if builtin_only:
            query = query.where(RoleCard.is_builtin.is_(True))

        result = await session.execute(query)
        return list(result.scalars().all())

    async def get_by_id(self, session: AsyncSession, role_card_id: str) -> RoleCard | None:
        """Get role card by ID.

        Args:
            session: Database session
            role_card_id: Role card ID

        Returns:
            Role card or None
        """
        result = await session.execute(select(RoleCard).where(RoleCard.id == role_card_id))
        return result.scalar_one_or_none()

    async def update(
        self, session: AsyncSession, role_card_id: str, data: RoleCardUpdate
    ) -> RoleCard | None:
        """Update a role card.

        Args:
            session: Database session
            role_card_id: Role card ID
            data: Update data

        Returns:
            Updated role card or None

        Raises:
            ValueError: If trying to update a built-in role card
        """
        role_card = await self.get_by_id(session, role_card_id)
        if not role_card:
            return None

        if role_card.is_builtin:
            raise ValueError("Cannot modify built-in role cards")

        update_data = data.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            setattr(role_card, field, value)

        await session.flush()

        logger.info("Updated role card", role_card_id=role_card.id)
        return role_card

    async def delete(self, session: AsyncSession, role_card_id: str) -> bool:
        """Delete a role card.

        Args:
            session: Database session
            role_card_id: Role card ID

        Returns:
            True if deleted, False if not found

        Raises:
            ValueError: If trying to delete a built-in role card
        """
        role_card = await self.get_by_id(session, role_card_id)
        if not role_card:
            return False

        if role_card.is_builtin:
            raise ValueError("Cannot delete built-in role cards")

        await session.delete(role_card)
        await session.flush()

        logger.info("Deleted role card", role_card_id=role_card_id)
        return True

    async def copy(
        self, session: AsyncSession, role_card_id: str, new_name: str
    ) -> RoleCard | None:
        """Copy a role card.

        Args:
            session: Database session
            role_card_id: Source role card ID
            new_name: Name for the copy

        Returns:
            Copied role card or None
        """
        import uuid

        source = await self.get_by_id(session, role_card_id)
        if not source:
            return None

        copy = RoleCard(
            id=str(uuid.uuid4()),
            name=new_name,
            description=source.description,
            expertise=source.expertise,
            responsibilities=source.responsibilities,
            constraints=source.constraints,
            system_prompt=source.system_prompt,
            output_style=source.output_style,
            default_provider_id=source.default_provider_id,
            default_model=source.default_model,
            temperature=source.temperature,
            is_builtin=False,
        )

        session.add(copy)
        await session.flush()

        logger.info("Copied role card", source_id=role_card_id, copy_id=copy.id)
        return copy

    async def generate_from_prompt(
        self,
        session: AsyncSession,
        provider_id: str,
        prompt_text: str,
        model_override: str | None = None,
    ) -> RoleCardGenerateResponse:
        """Generate a role card from prompt text using LLM.

        Args:
            session: Database session
            provider_id: Provider ID to use for generation
            prompt_text: Raw prompt text to analyze
            model_override: Optional model name override

        Returns:
            Generated role card data

        Raises:
            ValueError: If provider not found or LLM response is invalid
        """
        from app.services.crypto import crypto_service
        from app.services.model_client import ModelClient
        from app.services.provider_service import provider_service

        # Get provider config
        provider = await provider_service.get_by_id(session, provider_id)
        if not provider:
            raise ValueError("Provider not found")

        if not provider.enabled:
            raise ValueError("Provider is disabled")

        # Decrypt API key
        api_key = crypto_service.decrypt(provider.api_key_encrypted)
        model = model_override or provider.default_model

        # Create model client
        client = ModelClient(
            base_url=provider.base_url,
            api_key=api_key,
            model=model,
            temperature=0.3,  # Low temperature for structured output
            max_tokens=4096,
        )

        # Call LLM
        messages = [
            {"role": "system", "content": ROLE_CARD_GENERATION_SYSTEM_PROMPT},
            {"role": "user", "content": f"请分析以下提示词并生成角色卡：\n\n{prompt_text}"},
        ]

        logger.info(
            "Generating role card from prompt",
            provider_id=provider_id,
            model=model,
            prompt_length=len(prompt_text),
        )

        try:
            response = await client.chat_completion(messages)
        except Exception as e:
            logger.error("LLM call failed during role card generation", error=str(e))
            raise ValueError(f"LLM 调用失败: {str(e)}") from e

        # Parse JSON from response
        content = response.content.strip()

        # Handle case where LLM wraps JSON in markdown code block
        if content.startswith("```"):
            lines = content.split("\n")
            # Remove first line (```json or ```) and last line (```)
            lines = [l for l in lines if not l.strip().startswith("```")]
            content = "\n".join(lines).strip()

        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(
                "Failed to parse LLM response as JSON",
                content_preview=content[:500],
                error=str(e),
            )
            raise ValueError(
                "LLM 返回的内容无法解析为 JSON，请尝试重新生成"
            ) from e

        # Validate required fields
        required_fields = ["name", "description", "expertise", "responsibilities", "system_prompt"]
        for field in required_fields:
            if field not in data or not data[field]:
                raise ValueError(f"生成的角色卡缺少必要字段: {field}")

        # Ensure list fields
        if isinstance(data.get("expertise"), str):
            data["expertise"] = [data["expertise"]]
        if isinstance(data.get("responsibilities"), str):
            data["responsibilities"] = [data["responsibilities"]]
        if isinstance(data.get("constraints"), str):
            data["constraints"] = [data["constraints"]]

        # Clamp temperature
        temp = data.get("temperature", 0.7)
        if not isinstance(temp, (int, float)):
            temp = 0.7
        data["temperature"] = max(0.0, min(2.0, float(temp)))

        result = RoleCardGenerateResponse(**data)
        logger.info("Successfully generated role card", name=result.name)
        return result


# Singleton instance
role_card_service = RoleCardService()
