"""Tests for context builder."""

from app.services.context_builder import ContextBuilder


def test_build_expert_prompt():
    """Test building expert prompt with context."""
    # Arrange
    builder = ContextBuilder()
    role_data = {
        "name": "系统架构师",
        "description": "设计模块、技术边界和整体流程",
        "expertise": ["架构设计", "模块拆分"],
        "responsibilities": ["设计整体架构", "拆分模块边界"],
        "constraints": ["避免过度设计"],
    }

    # Act
    prompt = builder.build_expert_prompt(
        role=role_data,
        goal="设计登录模块",
        shared_sources=[],
        rolling_summary="",
        current_round=1,
        total_rounds=5,
    )

    # Assert
    assert "系统架构师" in prompt
    assert "设计登录模块" in prompt
    assert "架构设计" in prompt


def test_truncate_content():
    """Test content truncation."""
    # Arrange
    builder = ContextBuilder(max_file_tokens=100)
    long_content = "word " * 1000

    # Act
    truncated = builder.truncate_content(long_content)

    # Assert
    assert len(truncated) < len(long_content)
    assert truncated.endswith("...(内容已截断)")


def test_build_expert_prompt_with_sources():
    """Test building expert prompt with shared sources."""
    # Arrange
    builder = ContextBuilder()
    role_data = {
        "name": "产品经理",
        "description": "分析用户需求",
        "expertise": ["需求分析"],
        "responsibilities": ["定义产品需求"],
        "constraints": [],
    }
    shared_sources = [
        {
            "path": "需求文档.txt",
            "source_type": "text",
            "content": "用户需要一个登录功能",
        }
    ]

    # Act
    prompt = builder.build_expert_prompt(
        role=role_data,
        goal="设计登录模块",
        shared_sources=shared_sources,
        rolling_summary="",
        current_round=1,
        total_rounds=5,
    )

    # Assert
    assert "需求文档.txt" in prompt
    assert "用户需要一个登录功能" in prompt


def test_build_expert_prompt_with_rolling_summary():
    """Test building expert prompt with existing discussion summary."""
    # Arrange
    builder = ContextBuilder()
    role_data = {
        "name": "系统架构师",
        "description": "设计模块、技术边界和整体流程",
        "expertise": ["架构设计"],
        "responsibilities": ["设计整体架构"],
        "constraints": [],
    }
    rolling_summary = "[产品经理]: 建议使用JWT认证\n[系统架构师]: 同意JWT方案"

    # Act
    prompt = builder.build_expert_prompt(
        role=role_data,
        goal="设计登录模块",
        shared_sources=[],
        rolling_summary=rolling_summary,
        current_round=3,
        total_rounds=5,
    )

    # Assert
    assert "JWT认证" in prompt
    assert "3/5" in prompt


def test_build_expert_prompt_last_round():
    """Test building expert prompt for last round with convergence notice."""
    # Arrange
    builder = ContextBuilder()
    role_data = {
        "name": "系统架构师",
        "description": "设计模块",
        "expertise": ["架构设计"],
        "responsibilities": ["设计整体架构"],
        "constraints": [],
    }

    # Act
    prompt = builder.build_expert_prompt(
        role=role_data,
        goal="设计登录模块",
        shared_sources=[],
        rolling_summary="",
        current_round=5,
        total_rounds=5,
    )

    # Assert
    assert "最后几轮" in prompt
    assert "收敛观点" in prompt


def test_build_orchestrator_prompt():
    """Test building orchestrator prompt."""
    # Arrange
    builder = ContextBuilder()
    experts = [
        {"name": "系统架构师"},
        {"name": "产品经理"},
    ]

    # Act
    prompt = builder.build_orchestrator_prompt(
        goal="设计登录模块",
        shared_sources=[],
        rolling_summary="",
        current_round=1,
        total_rounds=5,
        experts=experts,
    )

    # Assert
    assert "系统架构师" in prompt
    assert "产品经理" in prompt
    assert "设计登录模块" in prompt


def test_orchestrator_prompt_contains_convergence_criteria():
    """Test that orchestrator prompt contains convergence judgment criteria."""
    # Arrange
    builder = ContextBuilder()
    experts = [{"name": "系统架构师"}, {"name": "产品经理"}]

    # Act
    prompt = builder.build_orchestrator_prompt(
        goal="设计登录模块",
        shared_sources=[],
        rolling_summary="",
        current_round=3,
        total_rounds=5,
        experts=experts,
    )

    # Assert - convergence criteria must be present
    assert "收敛" in prompt
    assert "观点" in prompt and "一致" in prompt
    assert "新" in prompt and ("信息" in prompt or "观点" in prompt)
    assert "决策" in prompt


def test_orchestrator_prompt_contains_action_directives():
    """Test that orchestrator prompt contains ACTION directive format."""
    # Arrange
    builder = ContextBuilder()
    experts = [{"name": "系统架构师"}, {"name": "产品经理"}]

    # Act
    prompt = builder.build_orchestrator_prompt(
        goal="设计登录模块",
        shared_sources=[],
        rolling_summary="",
        current_round=2,
        total_rounds=5,
        experts=experts,
    )

    # Assert - ACTION directives must be present
    assert "ACTION" in prompt
    assert "next:" in prompt
    assert "converge" in prompt
    assert "synthesize" in prompt


def test_orchestrator_prompt_near_end_round():
    """Test orchestrator prompt indicates near-end rounds."""
    # Arrange
    builder = ContextBuilder()
    experts = [{"name": "系统架构师"}, {"name": "产品经理"}]

    # Act - last round
    prompt = builder.build_orchestrator_prompt(
        goal="设计登录模块",
        shared_sources=[],
        rolling_summary="",
        current_round=5,
        total_rounds=5,
        experts=experts,
    )

    # Assert - should indicate this is the final round
    assert "最后" in prompt or "收敛" in prompt


def test_orchestrator_prompt_early_round():
    """Test orchestrator prompt for early round does not force convergence."""
    # Arrange
    builder = ContextBuilder()
    experts = [{"name": "系统架构师"}, {"name": "产品经理"}]

    # Act - first round
    prompt = builder.build_orchestrator_prompt(
        goal="设计登录模块",
        shared_sources=[],
        rolling_summary="",
        current_round=1,
        total_rounds=5,
        experts=experts,
    )

    # Assert - should still have ACTION directives but not force convergence
    assert "ACTION" in prompt
    assert "第 1/5" in prompt


def test_build_synthesizer_prompt():
    """Test building synthesizer prompt."""
    # Arrange
    builder = ContextBuilder()
    full_discussion = "[系统架构师]: 建议使用JWT\n[产品经理]: 同意"

    # Act
    prompt = builder.build_synthesizer_prompt(
        goal="设计登录模块",
        full_discussion=full_discussion,
    )

    # Assert
    assert "设计登录模块" in prompt
    assert "JWT" in prompt
    assert "Markdown" in prompt


def test_build_rolling_summary():
    """Test building rolling summary from messages."""
    # Arrange
    builder = ContextBuilder()
    new_messages = [
        {"sender_id": "架构师", "content": "建议使用JWT认证方案"},
        {"sender_id": "产品经理", "content": "同意JWT方案，但需要考虑刷新机制"},
    ]

    # Act
    summary = builder.build_rolling_summary(
        existing_summary="",
        new_messages=new_messages,
    )

    # Assert
    assert "JWT认证方案" in summary
    assert "刷新机制" in summary
    assert "架构师" in summary


def test_build_rolling_summary_with_existing():
    """Test building rolling summary with existing summary."""
    # Arrange
    builder = ContextBuilder()
    existing = "讨论开始：\n[架构师]: 需要设计登录模块"
    new_messages = [
        {"sender_id": "产品经理", "content": "建议使用OAuth2"},
    ]

    # Act
    summary = builder.build_rolling_summary(
        existing_summary=existing,
        new_messages=new_messages,
    )

    # Assert
    assert "OAuth2" in summary
    assert "登录模块" in summary


def test_build_file_contents_empty():
    """Test building file contents with no sources."""
    # Arrange
    builder = ContextBuilder()

    # Act
    result = builder._build_file_contents([])

    # Assert
    assert result == ""


def test_build_file_contents_with_sources():
    """Test building file contents with sources."""
    # Arrange
    builder = ContextBuilder()
    sources = [
        {
            "path": "config.yaml",
            "source_type": "file",
            "content": "database: sqlite",
        },
        {
            "path": "notes.txt",
            "source_type": "text",
            "content": "用户需要登录功能",
        },
    ]

    # Act
    result = builder._build_file_contents(sources)

    # Assert
    assert "config.yaml" in result
    assert "database: sqlite" in result
    assert "notes.txt" in result
    assert "用户需要登录功能" in result


def test_build_file_contents_truncation():
    """Test file contents truncation when exceeding limit."""
    builder = ContextBuilder(max_file_tokens=100)
    sources = [
        {
            "path": "large.txt",
            "source_type": "text",
            "content": "x" * 1000,
        }
    ]

    result = builder._build_file_contents(sources)

    assert "截断" in result
    assert len(result) < 1000 + 100


def test_truncate_content_short():
    """Test truncation with content under limit."""
    # Arrange
    builder = ContextBuilder(max_file_tokens=1000)
    short_content = "short content"

    # Act
    result = builder.truncate_content(short_content)

    # Assert
    assert result == short_content


def test_truncate_content_custom_limit():
    """Test truncation with custom token limit."""
    # Arrange
    builder = ContextBuilder(max_file_tokens=1000)
    content = "word " * 100

    # Act
    result = builder.truncate_content(content, max_tokens=10)

    # Assert
    assert len(result) < len(content)
    assert "截断" in result


def test_build_expert_prompt_with_additional_context():
    """Test building expert prompt with additional context."""
    # Arrange
    builder = ContextBuilder()
    role_data = {
        "name": "系统架构师",
        "description": "设计模块",
        "expertise": ["架构设计"],
        "responsibilities": ["设计整体架构"],
        "constraints": [],
    }

    # Act
    prompt = builder.build_expert_prompt(
        role=role_data,
        goal="设计登录模块",
        shared_sources=[],
        rolling_summary="",
        current_round=1,
        total_rounds=5,
        additional_context="请参考公司安全规范v2.0",
    )

    # Assert
    assert "公司安全规范v2.0" in prompt
    assert "补充信息" in prompt
