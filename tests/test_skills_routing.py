#!/usr/bin/env python3
"""
Tests for Skills-Based Routing
"""
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pbx.features.skills_routing import (
    AgentSkill,
    Skill,
    SkillRequirement,
    SkillsBasedRouter,
)


def test_skill_creation():
    """Test creating a skill"""
    print("Testing skill creation...")

    skill = Skill("python", "Python Programming", "Python development expertise")

    assert skill.skill_id == "python"
    assert skill.name == "Python Programming"
    assert skill.description == "Python development expertise"
    print("  ✓ Skill created successfully")

    return True


def test_agent_skill():
    """Test agent skill with proficiency"""
    print("Testing agent skill...")

    agent_skill = AgentSkill("1001", "python", 8)

    assert agent_skill.agent_extension == "1001"
    assert agent_skill.skill_id == "python"
    assert agent_skill.proficiency == 8
    print("  ✓ Agent skill created with proficiency 8")

    # Test proficiency clamping
    agent_skill_high = AgentSkill("1002", "python", 15)
    assert agent_skill_high.proficiency == 10, "Proficiency should be clamped to 10"
    print("  ✓ Proficiency correctly clamped to max 10")

    agent_skill_low = AgentSkill("1003", "python", -5)
    assert agent_skill_low.proficiency == 1, "Proficiency should be clamped to 1"
    print("  ✓ Proficiency correctly clamped to min 1")

    return True


def test_skill_requirement():
    """Test skill requirement"""
    print("Testing skill requirement...")

    req = SkillRequirement("python", min_proficiency=5, required=True)

    assert req.skill_id == "python"
    assert req.min_proficiency == 5
    assert req.required
    print("  ✓ Skill requirement created")

    return True


def test_router_initialization():
    """Test router initialization"""
    print("Testing router initialization...")

    config = {"features": {"skills_routing": {"enabled": True}}}
    router = SkillsBasedRouter(database=None, config=config)

    assert router.enabled, "Router should be enabled"
    print("  ✓ Skills router initialized")

    return True


def test_add_skill():
    """Test adding skills"""
    print("Testing add skill...")

    config = {"features": {"skills_routing": {"enabled": True}}}
    router = SkillsBasedRouter(database=None, config=config)

    success = router.add_skill("python", "Python Programming", "Python development")
    assert success, "Skill should be added successfully"
    print("  ✓ Skill added")

    # Try adding duplicate
    success = router.add_skill("python", "Python Programming", "Python development")
    assert not success, "Duplicate skill should not be added"
    print("  ✓ Duplicate skill rejected")

    return True


def test_assign_skill_to_agent():
    """Test assigning skills to agents"""
    print("Testing assign skill to agent...")

    config = {"features": {"skills_routing": {"enabled": True}}}
    router = SkillsBasedRouter(database=None, config=config)

    # Add skill first
    router.add_skill("python", "Python Programming")
    router.add_skill("javascript", "JavaScript Programming")

    # Assign to agent
    success = router.assign_skill_to_agent("1001", "python", 7)
    assert success, "Skill should be assigned"
    print("  ✓ Skill assigned to agent")

    # Assign another skill
    success = router.assign_skill_to_agent("1001", "javascript", 5)
    assert success, "Second skill should be assigned"
    print("  ✓ Multiple skills assigned")

    # Get agent skills
    skills = router.get_agent_skills("1001")
    assert len(skills) == 2, "Agent should have 2 skills"
    print(f"  ✓ Agent has {len(skills)} skills")

    return True


def test_remove_skill_from_agent():
    """Test removing skill from agent"""
    print("Testing remove skill from agent...")

    config = {"features": {"skills_routing": {"enabled": True}}}
    router = SkillsBasedRouter(database=None, config=config)

    # Setup
    router.add_skill("python", "Python Programming")
    router.assign_skill_to_agent("1001", "python", 7)

    # Remove skill
    success = router.remove_skill_from_agent("1001", "python")
    assert success, "Skill should be removed"
    print("  ✓ Skill removed from agent")

    # Verify removal
    skills = router.get_agent_skills("1001")
    assert len(skills) == 0, "Agent should have no skills"
    print("  ✓ Skill removal verified")

    return True


def test_queue_requirements():
    """Test setting queue requirements"""
    print("Testing queue requirements...")

    config = {"features": {"skills_routing": {"enabled": True}}}
    router = SkillsBasedRouter(database=None, config=config)

    # Add skills
    router.add_skill("python", "Python Programming")
    router.add_skill("sql", "SQL Database")

    # Set requirements
    requirements = [
        {"skill_id": "python", "min_proficiency": 5, "required": True},
        {"skill_id": "sql", "min_proficiency": 3, "required": False},
    ]

    success = router.set_queue_requirements("5000", requirements)
    assert success, "Requirements should be set"
    print("  ✓ Queue requirements set")

    # Get requirements
    reqs = router.get_queue_requirements("5000")
    assert len(reqs) == 2, "Should have 2 requirements"
    print(f"  ✓ Queue has {len(reqs)} skill requirements")

    return True


def test_find_best_agents():
    """Test finding best agents for queue"""
    print("Testing find best agents...")

    config = {"features": {"skills_routing": {"enabled": True, "fallback_to_any": False}}}
    router = SkillsBasedRouter(database=None, config=config)

    # Add skills
    router.add_skill("python", "Python")
    router.add_skill("javascript", "JavaScript")

    # Add agents with skills
    router.assign_skill_to_agent("1001", "python", 8)
    router.assign_skill_to_agent("1001", "javascript", 6)

    router.assign_skill_to_agent("1002", "python", 5)

    router.assign_skill_to_agent("1003", "javascript", 9)

    # Set queue requirements
    requirements = [{"skill_id": "python", "min_proficiency": 4, "required": True}]
    router.set_queue_requirements("5000", requirements)

    # Find best agents
    available_agents = ["1001", "1002", "1003"]
    best_agents = router.find_best_agents("5000", available_agents, max_results=3)

    assert len(best_agents) == 2, "Should find 2 agents with Python skill"
    assert best_agents[0]["extension"] == "1001", "Agent 1001 should be first (highest proficiency)"
    print("  ✓ Best agents found and ranked correctly")
    print(
        f"    Top agent: {best_agents[0]['extension']} (score: {best_agents[0]['score']:.2f})"
    )

    return True


def test_fallback_to_any_agent():
    """Test fallback when no agents match"""
    print("Testing fallback to any agent...")

    config = {"features": {"skills_routing": {"enabled": True, "fallback_to_any": True}}}
    router = SkillsBasedRouter(database=None, config=config)

    # Add skill but no agents have it
    router.add_skill("python", "Python")

    # Set queue requirements
    requirements = [{"skill_id": "python", "min_proficiency": 5, "required": True}]
    router.set_queue_requirements("5000", requirements)

    # Try to find agents (none match)
    available_agents = ["1001", "1002"]
    best_agents = router.find_best_agents("5000", available_agents, max_results=2)

    assert len(best_agents) == 2, "Should fallback to all available agents"
    assert best_agents[0]["score"] == 0.0, "Fallback agents should have score 0"
    print("  ✓ Fallback to any agent works")

    return True


def test_scoring_algorithm():
    """Test agent scoring algorithm"""
    print("Testing scoring algorithm...")

    config = {"features": {"skills_routing": {"enabled": True}}}
    router = SkillsBasedRouter(database=None, config=config)

    # Add skills
    router.add_skill("python", "Python")
    router.add_skill("sql", "SQL")

    # Agent 1: Both skills, high proficiency
    router.assign_skill_to_agent("1001", "python", 9)
    router.assign_skill_to_agent("1001", "sql", 8)

    # Agent 2: Only required skill, medium proficiency
    router.assign_skill_to_agent("1002", "python", 6)

    # Agent 3: Both skills, medium proficiency
    router.assign_skill_to_agent("1003", "python", 7)
    router.assign_skill_to_agent("1003", "sql", 7)

    # Set requirements (Python required, SQL preferred)
    requirements = [
        {"skill_id": "python", "min_proficiency": 5, "required": True},
        {"skill_id": "sql", "min_proficiency": 5, "required": False},
    ]
    router.set_queue_requirements("5000", requirements)

    # Find best agents
    available_agents = ["1001", "1002", "1003"]
    best_agents = router.find_best_agents("5000", available_agents, max_results=3)

    assert len(best_agents) == 3, "All agents meet minimum requirements"
    assert best_agents[0]["extension"] == "1001", "Agent 1001 should rank highest"

    print("  ✓ Scoring algorithm ranks agents correctly")
    for i, agent in enumerate(best_agents, 1):
        print(
            f"    {i}. Agent {agent['extension']}: score {agent['score']:.3f}, {len(agent['matching_skills'])} skills"
        )

    return True


def test_get_all_skills():
    """Test getting all skills"""
    print("Testing get all skills...")

    config = {"features": {"skills_routing": {"enabled": True}}}
    router = SkillsBasedRouter(database=None, config=config)

    # Add skills
    router.add_skill("python", "Python")
    router.add_skill("javascript", "JavaScript")
    router.add_skill("sql", "SQL")

    # Get all skills
    all_skills = router.get_all_skills()

    assert len(all_skills) == 3, "Should have 3 skills"
    print(f"  ✓ Retrieved {len(all_skills)} skills")

    return True


def run_all_tests():
    """Run all skills routing tests"""
    print("=" * 60)
    print("Skills-Based Routing Tests")
    print("=" * 60)
    print()

    tests = [
        test_skill_creation,
        test_agent_skill,
        test_skill_requirement,
        test_router_initialization,
        test_add_skill,
        test_assign_skill_to_agent,
        test_remove_skill_from_agent,
        test_queue_requirements,
        test_find_best_agents,
        test_fallback_to_any_agent,
        test_scoring_algorithm,
        test_get_all_skills,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
                print(f"  ✗ {test.__name__} failed")
        except Exception as e:
            failed += 1
            print(f"  ✗ {test.__name__} failed with exception: {e}")
            import traceback

            traceback.print_exc()
        print()

    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
