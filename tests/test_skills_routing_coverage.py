"""Comprehensive tests for Skills-Based Routing (SBR) module."""

import sqlite3
from unittest.mock import MagicMock, patch

import pytest

from pbx.features.skills_routing import (
    AgentSkill,
    Skill,
    SkillRequirement,
    SkillsBasedRouter,
    get_skills_router,
)


@pytest.mark.unit
class TestSkill:
    """Tests for the Skill data class."""

    def test_init(self) -> None:
        skill = Skill("python", "Python Programming", "Python language expertise")
        assert skill.skill_id == "python"
        assert skill.name == "Python Programming"
        assert skill.description == "Python language expertise"

    def test_init_default_description(self) -> None:
        skill = Skill("python", "Python Programming")
        assert skill.description == ""

    def test_to_dict(self) -> None:
        skill = Skill("python", "Python Programming", "desc")
        result = skill.to_dict()
        assert result == {
            "skill_id": "python",
            "name": "Python Programming",
            "description": "desc",
        }


@pytest.mark.unit
class TestAgentSkill:
    """Tests for the AgentSkill data class."""

    def test_init_default_proficiency(self) -> None:
        agent_skill = AgentSkill("1001", "python")
        assert agent_skill.agent_extension == "1001"
        assert agent_skill.skill_id == "python"
        assert agent_skill.proficiency == 5
        assert agent_skill.assigned_at is not None

    def test_init_custom_proficiency(self) -> None:
        agent_skill = AgentSkill("1001", "python", proficiency=8)
        assert agent_skill.proficiency == 8

    def test_proficiency_clamped_min(self) -> None:
        agent_skill = AgentSkill("1001", "python", proficiency=-5)
        assert agent_skill.proficiency == 1

    def test_proficiency_clamped_max(self) -> None:
        agent_skill = AgentSkill("1001", "python", proficiency=15)
        assert agent_skill.proficiency == 10

    def test_to_dict(self) -> None:
        agent_skill = AgentSkill("1001", "python", proficiency=7)
        result = agent_skill.to_dict()
        assert result["agent_extension"] == "1001"
        assert result["skill_id"] == "python"
        assert result["proficiency"] == 7
        assert "assigned_at" in result


@pytest.mark.unit
class TestSkillRequirement:
    """Tests for the SkillRequirement data class."""

    def test_init_defaults(self) -> None:
        req = SkillRequirement("python")
        assert req.skill_id == "python"
        assert req.min_proficiency == 1
        assert req.required is True

    def test_init_custom(self) -> None:
        req = SkillRequirement("python", min_proficiency=7, required=False)
        assert req.min_proficiency == 7
        assert req.required is False

    def test_min_proficiency_clamped_min(self) -> None:
        req = SkillRequirement("python", min_proficiency=-1)
        assert req.min_proficiency == 1

    def test_min_proficiency_clamped_max(self) -> None:
        req = SkillRequirement("python", min_proficiency=20)
        assert req.min_proficiency == 10

    def test_to_dict(self) -> None:
        req = SkillRequirement("python", 5, False)
        result = req.to_dict()
        assert result == {
            "skill_id": "python",
            "min_proficiency": 5,
            "required": False,
        }


@pytest.mark.unit
class TestSkillsBasedRouterInit:
    """Tests for SkillsBasedRouter initialization."""

    @patch("pbx.features.skills_routing.get_logger")
    def test_init_no_database(self, mock_get_logger) -> None:
        router = SkillsBasedRouter()
        assert router.database is None
        assert router.config == {}
        assert router.enabled is False
        assert router.fallback_to_any_agent is True
        assert router.skills == {}
        assert router.agent_skills == {}
        assert router.queue_requirements == {}

    @patch("pbx.features.skills_routing.get_logger")
    def test_init_with_database(self, mock_get_logger) -> None:
        mock_db = MagicMock()
        mock_db.enabled = True
        mock_db.db_type = "sqlite"
        router = SkillsBasedRouter(database=mock_db)
        assert router.database is mock_db
        # _initialize_schema should have been called
        assert mock_db.execute.call_count == 3

    @patch("pbx.features.skills_routing.get_logger")
    def test_init_with_config_enabled(self, mock_get_logger) -> None:
        config = {
            "features": {
                "skills_routing": {
                    "enabled": True,
                    "fallback_to_any": False,
                    "proficiency_weight": 0.9,
                }
            }
        }
        router = SkillsBasedRouter(config=config)
        assert router.enabled is True
        assert router.fallback_to_any_agent is False
        assert router.proficiency_weight == 0.9

    @patch("pbx.features.skills_routing.get_logger")
    def test_init_database_disabled(self, mock_get_logger) -> None:
        mock_db = MagicMock()
        mock_db.enabled = False
        _router = SkillsBasedRouter(database=mock_db)
        mock_db.execute.assert_not_called()


@pytest.mark.unit
class TestSkillsBasedRouterGetConfig:
    """Tests for _get_config method."""

    @patch("pbx.features.skills_routing.get_logger")
    def test_get_config_dot_notation(self, mock_get_logger) -> None:
        config = {"features": {"skills_routing": {"enabled": True}}}
        router = SkillsBasedRouter(config=config)
        result = router._get_config("features.skills_routing.enabled", False)
        assert result is True

    @patch("pbx.features.skills_routing.get_logger")
    def test_get_config_missing_key(self, mock_get_logger) -> None:
        config = {}
        router = SkillsBasedRouter(config=config)
        result = router._get_config("nonexistent.key", "default_val")
        assert result == "default_val"

    @patch("pbx.features.skills_routing.get_logger")
    def test_get_config_flat_get(self, mock_get_logger) -> None:
        """Test when config supports flat dot-notation get."""
        mock_config = MagicMock()
        mock_config.get.return_value = "flat_value"
        router = SkillsBasedRouter(config=mock_config)
        result = router._get_config("features.skills_routing.enabled", False)
        assert result == "flat_value"

    @patch("pbx.features.skills_routing.get_logger")
    def test_get_config_flat_get_returns_none(self, mock_get_logger) -> None:
        """Test fallback to nested dict when flat get returns None."""
        mock_config = MagicMock()
        mock_config.get.return_value = None
        router = SkillsBasedRouter(config=mock_config)
        # This should fall through to nested key traversal but mock isn't a dict
        result = router._get_config("features.skills_routing.enabled", "fallback")
        assert result == "fallback"


@pytest.mark.unit
class TestSkillsBasedRouterInitializeSchema:
    """Tests for database schema initialization."""

    @patch("pbx.features.skills_routing.get_logger")
    def test_initialize_schema_postgresql(self, mock_get_logger) -> None:
        mock_db = MagicMock()
        mock_db.enabled = True
        mock_db.db_type = "postgresql"
        _router = SkillsBasedRouter(database=mock_db)
        assert mock_db.execute.call_count == 3

    @patch("pbx.features.skills_routing.get_logger")
    def test_initialize_schema_sqlite(self, mock_get_logger) -> None:
        mock_db = MagicMock()
        mock_db.enabled = True
        mock_db.db_type = "sqlite"
        _router = SkillsBasedRouter(database=mock_db)
        assert mock_db.execute.call_count == 3

    @patch("pbx.features.skills_routing.get_logger")
    def test_initialize_schema_error(self, mock_get_logger) -> None:
        mock_db = MagicMock()
        mock_db.enabled = True
        mock_db.db_type = "sqlite"
        mock_db.execute.side_effect = sqlite3.Error("Schema error")
        # Should not raise
        router = SkillsBasedRouter(database=mock_db)
        assert router is not None


@pytest.mark.unit
class TestSkillsBasedRouterAddSkill:
    """Tests for adding skills."""

    @patch("pbx.features.skills_routing.get_logger")
    def test_add_skill_success(self, mock_get_logger) -> None:
        router = SkillsBasedRouter()
        result = router.add_skill("python", "Python Programming", "desc")
        assert result is True
        assert "python" in router.skills
        assert router.skills["python"].name == "Python Programming"

    @patch("pbx.features.skills_routing.get_logger")
    def test_add_skill_duplicate(self, mock_get_logger) -> None:
        router = SkillsBasedRouter()
        router.add_skill("python", "Python")
        result = router.add_skill("python", "Python Again")
        assert result is False

    @patch("pbx.features.skills_routing.get_logger")
    def test_add_skill_with_db_postgresql(self, mock_get_logger) -> None:
        mock_db = MagicMock()
        mock_db.enabled = True
        mock_db.db_type = "postgresql"
        router = SkillsBasedRouter(database=mock_db)
        mock_db.execute.reset_mock()
        router.add_skill("python", "Python")
        mock_db.execute.assert_called_once()

    @patch("pbx.features.skills_routing.get_logger")
    def test_add_skill_with_db_sqlite(self, mock_get_logger) -> None:
        mock_db = MagicMock()
        mock_db.enabled = True
        mock_db.db_type = "sqlite"
        router = SkillsBasedRouter(database=mock_db)
        mock_db.execute.reset_mock()
        router.add_skill("python", "Python")
        mock_db.execute.assert_called_once()

    @patch("pbx.features.skills_routing.get_logger")
    def test_add_skill_db_error(self, mock_get_logger) -> None:
        mock_db = MagicMock()
        mock_db.enabled = True
        mock_db.db_type = "sqlite"
        router = SkillsBasedRouter(database=mock_db)
        mock_db.execute.reset_mock()
        mock_db.execute.side_effect = sqlite3.Error("Insert error")
        result = router.add_skill("python", "Python")
        assert result is True  # Skill still added in-memory


@pytest.mark.unit
class TestSkillsBasedRouterAssignSkill:
    """Tests for assigning skills to agents."""

    @patch("pbx.features.skills_routing.get_logger")
    def test_assign_skill_success(self, mock_get_logger) -> None:
        router = SkillsBasedRouter()
        router.add_skill("python", "Python")
        result = router.assign_skill_to_agent("1001", "python", 7)
        assert result is True
        assert "1001" in router.agent_skills
        assert "python" in router.agent_skills["1001"]

    @patch("pbx.features.skills_routing.get_logger")
    def test_assign_nonexistent_skill(self, mock_get_logger) -> None:
        router = SkillsBasedRouter()
        result = router.assign_skill_to_agent("1001", "nonexistent", 5)
        assert result is False

    @patch("pbx.features.skills_routing.get_logger")
    def test_assign_multiple_skills(self, mock_get_logger) -> None:
        router = SkillsBasedRouter()
        router.add_skill("python", "Python")
        router.add_skill("java", "Java")
        router.assign_skill_to_agent("1001", "python", 8)
        router.assign_skill_to_agent("1001", "java", 6)
        assert len(router.agent_skills["1001"]) == 2

    @patch("pbx.features.skills_routing.get_logger")
    def test_assign_skill_with_db_postgresql(self, mock_get_logger) -> None:
        mock_db = MagicMock()
        mock_db.enabled = True
        mock_db.db_type = "postgresql"
        router = SkillsBasedRouter(database=mock_db)
        router.add_skill("python", "Python")
        mock_db.execute.reset_mock()
        router.assign_skill_to_agent("1001", "python", 7)
        mock_db.execute.assert_called_once()

    @patch("pbx.features.skills_routing.get_logger")
    def test_assign_skill_with_db_sqlite(self, mock_get_logger) -> None:
        mock_db = MagicMock()
        mock_db.enabled = True
        mock_db.db_type = "sqlite"
        router = SkillsBasedRouter(database=mock_db)
        router.add_skill("python", "Python")
        mock_db.execute.reset_mock()
        router.assign_skill_to_agent("1001", "python", 7)
        mock_db.execute.assert_called_once()

    @patch("pbx.features.skills_routing.get_logger")
    def test_assign_skill_db_error(self, mock_get_logger) -> None:
        mock_db = MagicMock()
        mock_db.enabled = True
        mock_db.db_type = "sqlite"
        router = SkillsBasedRouter(database=mock_db)
        router.add_skill("python", "Python")
        mock_db.execute.reset_mock()
        mock_db.execute.side_effect = sqlite3.Error("DB error")
        result = router.assign_skill_to_agent("1001", "python", 7)
        assert result is True  # Still added in-memory


@pytest.mark.unit
class TestSkillsBasedRouterRemoveSkill:
    """Tests for removing skills from agents."""

    @patch("pbx.features.skills_routing.get_logger")
    def test_remove_skill_success(self, mock_get_logger) -> None:
        router = SkillsBasedRouter()
        router.add_skill("python", "Python")
        router.assign_skill_to_agent("1001", "python", 7)
        result = router.remove_skill_from_agent("1001", "python")
        assert result is True
        assert "python" not in router.agent_skills["1001"]

    @patch("pbx.features.skills_routing.get_logger")
    def test_remove_nonexistent_agent(self, mock_get_logger) -> None:
        router = SkillsBasedRouter()
        result = router.remove_skill_from_agent("9999", "python")
        assert result is False

    @patch("pbx.features.skills_routing.get_logger")
    def test_remove_nonexistent_skill(self, mock_get_logger) -> None:
        router = SkillsBasedRouter()
        router.add_skill("python", "Python")
        router.assign_skill_to_agent("1001", "python", 7)
        result = router.remove_skill_from_agent("1001", "java")
        assert result is False

    @patch("pbx.features.skills_routing.get_logger")
    def test_remove_skill_with_db_postgresql(self, mock_get_logger) -> None:
        mock_db = MagicMock()
        mock_db.enabled = True
        mock_db.db_type = "postgresql"
        router = SkillsBasedRouter(database=mock_db)
        router.add_skill("python", "Python")
        router.assign_skill_to_agent("1001", "python", 7)
        mock_db.execute.reset_mock()
        router.remove_skill_from_agent("1001", "python")
        mock_db.execute.assert_called_once()

    @patch("pbx.features.skills_routing.get_logger")
    def test_remove_skill_with_db_sqlite(self, mock_get_logger) -> None:
        mock_db = MagicMock()
        mock_db.enabled = True
        mock_db.db_type = "sqlite"
        router = SkillsBasedRouter(database=mock_db)
        router.add_skill("python", "Python")
        router.assign_skill_to_agent("1001", "python", 7)
        mock_db.execute.reset_mock()
        router.remove_skill_from_agent("1001", "python")
        mock_db.execute.assert_called_once()

    @patch("pbx.features.skills_routing.get_logger")
    def test_remove_skill_db_error(self, mock_get_logger) -> None:
        mock_db = MagicMock()
        mock_db.enabled = True
        mock_db.db_type = "sqlite"
        router = SkillsBasedRouter(database=mock_db)
        router.add_skill("python", "Python")
        router.assign_skill_to_agent("1001", "python", 7)
        mock_db.execute.reset_mock()
        mock_db.execute.side_effect = sqlite3.Error("Delete error")
        result = router.remove_skill_from_agent("1001", "python")
        assert result is True  # Still removed in-memory


@pytest.mark.unit
class TestSkillsBasedRouterSetQueueRequirements:
    """Tests for setting queue skill requirements."""

    @patch("pbx.features.skills_routing.get_logger")
    def test_set_queue_requirements(self, mock_get_logger) -> None:
        router = SkillsBasedRouter()
        router.add_skill("python", "Python")
        router.add_skill("java", "Java")
        reqs = [
            {"skill_id": "python", "min_proficiency": 5, "required": True},
            {"skill_id": "java", "min_proficiency": 3, "required": False},
        ]
        result = router.set_queue_requirements("Q100", reqs)
        assert result is True
        assert "Q100" in router.queue_requirements
        assert len(router.queue_requirements["Q100"]) == 2

    @patch("pbx.features.skills_routing.get_logger")
    def test_set_queue_requirements_nonexistent_skill(self, mock_get_logger) -> None:
        router = SkillsBasedRouter()
        router.add_skill("python", "Python")
        reqs = [
            {"skill_id": "python", "min_proficiency": 5},
            {"skill_id": "nonexistent", "min_proficiency": 3},
        ]
        result = router.set_queue_requirements("Q100", reqs)
        assert result is True
        assert len(router.queue_requirements["Q100"]) == 1

    @patch("pbx.features.skills_routing.get_logger")
    def test_set_queue_requirements_with_db_postgresql(self, mock_get_logger) -> None:
        mock_db = MagicMock()
        mock_db.enabled = True
        mock_db.db_type = "postgresql"
        router = SkillsBasedRouter(database=mock_db)
        router.add_skill("python", "Python")
        mock_db.execute.reset_mock()
        reqs = [{"skill_id": "python", "min_proficiency": 5}]
        router.set_queue_requirements("Q100", reqs)
        # 1 delete + 1 insert
        assert mock_db.execute.call_count == 2

    @patch("pbx.features.skills_routing.get_logger")
    def test_set_queue_requirements_with_db_sqlite(self, mock_get_logger) -> None:
        mock_db = MagicMock()
        mock_db.enabled = True
        mock_db.db_type = "sqlite"
        router = SkillsBasedRouter(database=mock_db)
        router.add_skill("python", "Python")
        mock_db.execute.reset_mock()
        reqs = [{"skill_id": "python", "min_proficiency": 5}]
        router.set_queue_requirements("Q100", reqs)
        assert mock_db.execute.call_count == 2

    @patch("pbx.features.skills_routing.get_logger")
    def test_set_queue_requirements_db_error(self, mock_get_logger) -> None:
        mock_db = MagicMock()
        mock_db.enabled = True
        mock_db.db_type = "sqlite"
        router = SkillsBasedRouter(database=mock_db)
        router.add_skill("python", "Python")
        mock_db.execute.reset_mock()
        mock_db.execute.side_effect = sqlite3.Error("DB error")
        result = router.set_queue_requirements("Q100", [{"skill_id": "python"}])
        assert result is True  # Still set in-memory

    @patch("pbx.features.skills_routing.get_logger")
    def test_set_queue_requirements_defaults(self, mock_get_logger) -> None:
        """Test that default min_proficiency and required values are used."""
        router = SkillsBasedRouter()
        router.add_skill("python", "Python")
        reqs = [{"skill_id": "python"}]
        router.set_queue_requirements("Q100", reqs)
        req = router.queue_requirements["Q100"][0]
        assert req.min_proficiency == 1
        assert req.required is True


@pytest.mark.unit
class TestSkillsBasedRouterFindBestAgents:
    """Tests for finding best agents."""

    @patch("pbx.features.skills_routing.get_logger")
    def test_find_best_agents_no_requirements(self, mock_get_logger) -> None:
        router = SkillsBasedRouter()
        result = router.find_best_agents("Q100", ["1001", "1002", "1003"])
        assert len(result) == 3
        assert all(a["score"] == 1.0 for a in result)

    @patch("pbx.features.skills_routing.get_logger")
    def test_find_best_agents_with_matching_skills(self, mock_get_logger) -> None:
        router = SkillsBasedRouter()
        router.add_skill("python", "Python")
        router.assign_skill_to_agent("1001", "python", 8)
        router.assign_skill_to_agent("1002", "python", 5)
        router.set_queue_requirements("Q100", [{"skill_id": "python", "min_proficiency": 3}])

        result = router.find_best_agents("Q100", ["1001", "1002"])
        assert len(result) == 2
        # Agent 1001 should score higher
        assert result[0]["extension"] == "1001"

    @patch("pbx.features.skills_routing.get_logger")
    def test_find_best_agents_no_match_with_fallback(self, mock_get_logger) -> None:
        router = SkillsBasedRouter()
        router.fallback_to_any_agent = True
        router.add_skill("python", "Python")
        router.set_queue_requirements("Q100", [{"skill_id": "python", "min_proficiency": 5}])

        result = router.find_best_agents("Q100", ["1001", "1002"])
        assert len(result) == 2
        assert all(a["score"] == 0.0 for a in result)

    @patch("pbx.features.skills_routing.get_logger")
    def test_find_best_agents_no_match_no_fallback(self, mock_get_logger) -> None:
        router = SkillsBasedRouter()
        router.fallback_to_any_agent = False
        router.add_skill("python", "Python")
        router.set_queue_requirements("Q100", [{"skill_id": "python", "min_proficiency": 5}])

        result = router.find_best_agents("Q100", ["1001", "1002"])
        assert len(result) == 0

    @patch("pbx.features.skills_routing.get_logger")
    def test_find_best_agents_max_results(self, mock_get_logger) -> None:
        router = SkillsBasedRouter()
        router.add_skill("python", "Python")
        for i in range(10):
            ext = f"100{i}"
            router.assign_skill_to_agent(ext, "python", 5)
        router.set_queue_requirements("Q100", [{"skill_id": "python", "min_proficiency": 1}])

        agents = [f"100{i}" for i in range(10)]
        result = router.find_best_agents("Q100", agents, max_results=3)
        assert len(result) == 3

    @patch("pbx.features.skills_routing.get_logger")
    def test_find_best_agents_agent_below_proficiency(self, mock_get_logger) -> None:
        router = SkillsBasedRouter()
        router.fallback_to_any_agent = False
        router.add_skill("python", "Python")
        router.assign_skill_to_agent("1001", "python", 2)
        router.set_queue_requirements(
            "Q100", [{"skill_id": "python", "min_proficiency": 5, "required": True}]
        )

        result = router.find_best_agents("Q100", ["1001"])
        assert len(result) == 0

    @patch("pbx.features.skills_routing.get_logger")
    def test_find_best_agents_missing_required_skill(self, mock_get_logger) -> None:
        router = SkillsBasedRouter()
        router.fallback_to_any_agent = False
        router.add_skill("python", "Python")
        router.add_skill("java", "Java")
        router.assign_skill_to_agent("1001", "python", 8)
        # Agent 1001 has python but NOT java (required)
        router.set_queue_requirements(
            "Q100",
            [
                {"skill_id": "python", "min_proficiency": 3, "required": True},
                {"skill_id": "java", "min_proficiency": 3, "required": True},
            ],
        )

        result = router.find_best_agents("Q100", ["1001"])
        assert len(result) == 0

    @patch("pbx.features.skills_routing.get_logger")
    def test_find_best_agents_optional_skill_bonus(self, mock_get_logger) -> None:
        router = SkillsBasedRouter()
        router.add_skill("python", "Python")
        router.add_skill("java", "Java")
        router.assign_skill_to_agent("1001", "python", 8)
        router.assign_skill_to_agent("1001", "java", 6)
        router.assign_skill_to_agent("1002", "python", 8)
        router.set_queue_requirements(
            "Q100",
            [
                {"skill_id": "python", "min_proficiency": 3, "required": True},
                {"skill_id": "java", "min_proficiency": 3, "required": False},
            ],
        )

        result = router.find_best_agents("Q100", ["1001", "1002"])
        # Agent 1001 should score higher due to optional java skill
        assert result[0]["extension"] == "1001"


@pytest.mark.unit
class TestSkillsBasedRouterCalculateAgentScore:
    """Tests for agent score calculation."""

    @patch("pbx.features.skills_routing.get_logger")
    def test_calculate_score_no_skills(self, mock_get_logger) -> None:
        router = SkillsBasedRouter()
        router.add_skill("python", "Python")
        requirements = [SkillRequirement("python", 5, True)]
        score, skills = router._calculate_agent_score("unknown_agent", requirements)
        assert score == 0.0
        assert skills == []

    @patch("pbx.features.skills_routing.get_logger")
    def test_calculate_score_perfect_match(self, mock_get_logger) -> None:
        router = SkillsBasedRouter()
        router.add_skill("python", "Python")
        router.assign_skill_to_agent("1001", "python", 10)
        requirements = [SkillRequirement("python", 5, True)]
        score, skills = router._calculate_agent_score("1001", requirements)
        assert score > 0.0
        assert len(skills) == 1

    @patch("pbx.features.skills_routing.get_logger")
    def test_calculate_score_empty_requirements(self, mock_get_logger) -> None:
        router = SkillsBasedRouter()
        score, skills = router._calculate_agent_score("1001", [])
        assert score == 0.0
        assert skills == []


@pytest.mark.unit
class TestSkillsBasedRouterGetAgentSkills:
    """Tests for getting agent skills."""

    @patch("pbx.features.skills_routing.get_logger")
    def test_get_agent_skills_existing(self, mock_get_logger) -> None:
        router = SkillsBasedRouter()
        router.add_skill("python", "Python", "desc")
        router.assign_skill_to_agent("1001", "python", 7)
        result = router.get_agent_skills("1001")
        assert len(result) == 1
        assert result[0]["skill_id"] == "python"
        assert result[0]["name"] == "Python"
        assert result[0]["description"] == "desc"

    @patch("pbx.features.skills_routing.get_logger")
    def test_get_agent_skills_nonexistent(self, mock_get_logger) -> None:
        router = SkillsBasedRouter()
        result = router.get_agent_skills("9999")
        assert result == []

    @patch("pbx.features.skills_routing.get_logger")
    def test_get_agent_skills_missing_skill_definition(self, mock_get_logger) -> None:
        """Agent has skill_id but skill definition was removed from router.skills."""
        router = SkillsBasedRouter()
        router.add_skill("python", "Python")
        router.assign_skill_to_agent("1001", "python", 7)
        # Remove skill from definitions
        del router.skills["python"]
        result = router.get_agent_skills("1001")
        assert len(result) == 1
        assert "name" not in result[0]


@pytest.mark.unit
class TestSkillsBasedRouterGetAllSkills:
    """Tests for getting all skills."""

    @patch("pbx.features.skills_routing.get_logger")
    def test_get_all_skills_empty(self, mock_get_logger) -> None:
        router = SkillsBasedRouter()
        assert router.get_all_skills() == []

    @patch("pbx.features.skills_routing.get_logger")
    def test_get_all_skills_multiple(self, mock_get_logger) -> None:
        router = SkillsBasedRouter()
        router.add_skill("python", "Python")
        router.add_skill("java", "Java")
        result = router.get_all_skills()
        assert len(result) == 2


@pytest.mark.unit
class TestSkillsBasedRouterGetQueueRequirements:
    """Tests for getting queue requirements."""

    @patch("pbx.features.skills_routing.get_logger")
    def test_get_queue_requirements_existing(self, mock_get_logger) -> None:
        router = SkillsBasedRouter()
        router.add_skill("python", "Python")
        router.set_queue_requirements("Q100", [{"skill_id": "python", "min_proficiency": 5}])
        result = router.get_queue_requirements("Q100")
        assert len(result) == 1
        assert result[0]["skill_name"] == "Python"

    @patch("pbx.features.skills_routing.get_logger")
    def test_get_queue_requirements_nonexistent(self, mock_get_logger) -> None:
        router = SkillsBasedRouter()
        result = router.get_queue_requirements("Q999")
        assert result == []

    @patch("pbx.features.skills_routing.get_logger")
    def test_get_queue_requirements_missing_skill_definition(self, mock_get_logger) -> None:
        """Queue has requirement for skill_id that was removed from router.skills."""
        router = SkillsBasedRouter()
        router.add_skill("python", "Python")
        router.set_queue_requirements("Q100", [{"skill_id": "python"}])
        del router.skills["python"]
        result = router.get_queue_requirements("Q100")
        assert len(result) == 1
        assert "skill_name" not in result[0]


@pytest.mark.unit
class TestGetSkillsRouter:
    """Tests for the factory function."""

    @patch("pbx.features.skills_routing.get_logger")
    def test_get_skills_router(self, mock_get_logger) -> None:
        router = get_skills_router()
        assert isinstance(router, SkillsBasedRouter)

    @patch("pbx.features.skills_routing.get_logger")
    def test_get_skills_router_with_args(self, mock_get_logger) -> None:
        mock_db = MagicMock()
        mock_db.enabled = False
        config = {"features": {"skills_routing": {"enabled": True}}}
        router = get_skills_router(database=mock_db, config=config)
        assert isinstance(router, SkillsBasedRouter)
        assert router.database is mock_db
