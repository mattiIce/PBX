"""
Skills-Based Routing (SBR) System
Routes calls to agents based on their skills and expertise
"""

import sqlite3
from datetime import UTC, datetime

from pbx.utils.logger import get_logger


class Skill:
    """Represents a skill that agents can have"""

    def __init__(self, skill_id: str, name: str, description: str = ""):
        """
        Initialize skill

        Args:
            skill_id: Unique skill identifier
            name: Skill name
            description: Skill description
        """
        self.skill_id = skill_id
        self.name = name
        self.description = description

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {"skill_id": self.skill_id, "name": self.name, "description": self.description}


class AgentSkill:
    """Represents an agent's proficiency in a skill"""

    def __init__(self, agent_extension: str, skill_id: str, proficiency: int = 5):
        """
        Initialize agent skill

        Args:
            agent_extension: Agent's extension number
            skill_id: Skill identifier
            proficiency: Skill level (1-10, where 10 is expert)
        """
        self.agent_extension = agent_extension
        self.skill_id = skill_id
        self.proficiency = max(1, min(10, proficiency))  # Clamp to 1-10
        self.assigned_at = datetime.now(UTC)

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "agent_extension": self.agent_extension,
            "skill_id": self.skill_id,
            "proficiency": self.proficiency,
            "assigned_at": self.assigned_at.isoformat(),
        }


class SkillRequirement:
    """Represents a skill requirement for a call or queue"""

    def __init__(self, skill_id: str, min_proficiency: int = 1, required: bool = True):
        """
        Initialize skill requirement

        Args:
            skill_id: Required skill identifier
            min_proficiency: Minimum proficiency level needed (1-10)
            required: Whether skill is mandatory or preferred
        """
        self.skill_id = skill_id
        self.min_proficiency = max(1, min(10, min_proficiency))
        self.required = required

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "skill_id": self.skill_id,
            "min_proficiency": self.min_proficiency,
            "required": self.required,
        }


class SkillsBasedRouter:
    """
    Manages skills-based call routing
    Routes calls to agents based on required skills and agent proficiency
    """

    def __init__(self, database=None, config: dict | None = None):
        """
        Initialize skills-based router

        Args:
            database: Database backend for persistent storage
            config: Configuration dictionary
        """
        self.logger = get_logger()
        self.database = database
        self.config = config or {}

        # Configuration
        self.enabled = self._get_config("features.skills_routing.enabled", False)
        self.fallback_to_any_agent = self._get_config(
            "features.skills_routing.fallback_to_any", True
        )
        self.proficiency_weight = self._get_config(
            "features.skills_routing.proficiency_weight", 0.7
        )

        # In-memory storage
        self.skills = {}  # skill_id -> Skill
        self.agent_skills = {}  # agent_extension -> {skill_id -> AgentSkill}
        self.queue_requirements = {}  # queue_number -> list[SkillRequirement]

        # Initialize database schema
        if self.database and self.database.enabled:
            self._initialize_schema()

        if self.enabled:
            self.logger.info("Skills-Based Routing initialized")

    def _get_config(self, key: str, default=None):
        """Get config value supporting both dot notation and nested dicts"""
        if hasattr(self.config, "get") and "." in key:
            value = self.config.get(key, None)
            if value is not None:
                return value

        keys = key.split(".")
        value = self.config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value if value is not None else default

    def _initialize_schema(self):
        """Initialize skills routing database tables"""
        # Skills table
        skills_table = (
            """
        CREATE TABLE IF NOT EXISTS skills (
            skill_id VARCHAR(50) PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
            if self.database.db_type == "postgresql"
            else """
        CREATE TABLE IF NOT EXISTS skills (
            skill_id VARCHAR(50) PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        )

        # Agent skills table
        agent_skills_table = (
            """
        CREATE TABLE IF NOT EXISTS agent_skills (
            id SERIAL PRIMARY KEY,
            agent_extension VARCHAR(20) NOT NULL,
            skill_id VARCHAR(50) NOT NULL,
            proficiency INTEGER NOT NULL CHECK (proficiency >= 1 AND proficiency <= 10),
            assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(agent_extension, skill_id)
        )
        """
            if self.database.db_type == "postgresql"
            else """
        CREATE TABLE IF NOT EXISTS agent_skills (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_extension VARCHAR(20) NOT NULL,
            skill_id VARCHAR(50) NOT NULL,
            proficiency INTEGER NOT NULL CHECK (proficiency >= 1 AND proficiency <= 10),
            assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(agent_extension, skill_id)
        )
        """
        )

        # Queue skill requirements table
        queue_requirements_table = (
            """
        CREATE TABLE IF NOT EXISTS queue_skill_requirements (
            id SERIAL PRIMARY KEY,
            queue_number VARCHAR(20) NOT NULL,
            skill_id VARCHAR(50) NOT NULL,
            min_proficiency INTEGER NOT NULL CHECK (min_proficiency >= 1 AND min_proficiency <= 10),
            required BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
            if self.database.db_type == "postgresql"
            else """
        CREATE TABLE IF NOT EXISTS queue_skill_requirements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            queue_number VARCHAR(20) NOT NULL,
            skill_id VARCHAR(50) NOT NULL,
            min_proficiency INTEGER NOT NULL CHECK (min_proficiency >= 1 AND min_proficiency <= 10),
            required BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        )

        try:
            self.database.execute(skills_table)
            self.database.execute(agent_skills_table)
            self.database.execute(queue_requirements_table)
            self.logger.info("Skills-based routing database schema initialized")
        except sqlite3.Error as e:
            self.logger.error(f"Failed to initialize skills routing schema: {e}")

    def add_skill(self, skill_id: str, name: str, description: str = "") -> bool:
        """
        Add a new skill

        Args:
            skill_id: Unique skill identifier
            name: Skill name
            description: Skill description

        Returns:
            True if skill was added
        """
        if skill_id in self.skills:
            self.logger.warning(f"Skill {skill_id} already exists")
            return False

        skill = Skill(skill_id, name, description)
        self.skills[skill_id] = skill

        # Store in database
        if self.database and self.database.enabled:
            try:
                insert_query = (
                    """
                INSERT INTO skills (skill_id, name, description)
                VALUES (%s, %s, %s)
                """
                    if self.database.db_type == "postgresql"
                    else """
                INSERT INTO skills (skill_id, name, description)
                VALUES (?, ?, ?)
                """
                )
                self.database.execute(insert_query, (skill_id, name, description))
            except sqlite3.Error as e:
                self.logger.error(f"Failed to store skill in database: {e}")

        self.logger.info(f"Added skill: {name} ({skill_id})")
        return True

    def assign_skill_to_agent(
        self, agent_extension: str, skill_id: str, proficiency: int = 5
    ) -> bool:
        """
        Assign skill to agent

        Args:
            agent_extension: Agent's extension number
            skill_id: Skill identifier
            proficiency: Skill level (1-10)

        Returns:
            True if skill was assigned
        """
        if skill_id not in self.skills:
            self.logger.error(f"Skill {skill_id} does not exist")
            return False

        # Initialize agent skills dict if needed
        if agent_extension not in self.agent_skills:
            self.agent_skills[agent_extension] = {}

        # Create agent skill
        agent_skill = AgentSkill(agent_extension, skill_id, proficiency)
        self.agent_skills[agent_extension][skill_id] = agent_skill

        # Store in database
        if self.database and self.database.enabled:
            try:
                # Try insert first, update if exists
                insert_query = (
                    """
                INSERT INTO agent_skills (agent_extension, skill_id, proficiency)
                VALUES (%s, %s, %s)
                ON CONFLICT (agent_extension, skill_id)
                DO UPDATE SET proficiency = EXCLUDED.proficiency, assigned_at = CURRENT_TIMESTAMP
                """
                    if self.database.db_type == "postgresql"
                    else """
                INSERT OR REPLACE INTO agent_skills (agent_extension, skill_id, proficiency)
                VALUES (?, ?, ?)
                """
                )
                self.database.execute(insert_query, (agent_extension, skill_id, proficiency))
            except sqlite3.Error as e:
                self.logger.error(f"Failed to store agent skill in database: {e}")

        self.logger.info(
            f"Assigned skill {skill_id} to agent {agent_extension} (proficiency: {proficiency})"
        )
        return True

    def remove_skill_from_agent(self, agent_extension: str, skill_id: str) -> bool:
        """
        Remove skill from agent

        Args:
            agent_extension: Agent's extension number
            skill_id: Skill identifier

        Returns:
            True if skill was removed
        """
        if agent_extension in self.agent_skills and skill_id in self.agent_skills[agent_extension]:
            del self.agent_skills[agent_extension][skill_id]

            # Remove from database
            if self.database and self.database.enabled:
                try:
                    delete_query = (
                        """
                    DELETE FROM agent_skills
                    WHERE agent_extension = %s AND skill_id = %s
                    """
                        if self.database.db_type == "postgresql"
                        else """
                    DELETE FROM agent_skills
                    WHERE agent_extension = ? AND skill_id = ?
                    """
                    )
                    self.database.execute(delete_query, (agent_extension, skill_id))
                except sqlite3.Error as e:
                    self.logger.error(f"Failed to remove agent skill from database: {e}")

            self.logger.info(f"Removed skill {skill_id} from agent {agent_extension}")
            return True

        return False

    def set_queue_requirements(self, queue_number: str, requirements: list[dict]) -> bool:
        """
        set skill requirements for a queue

        Args:
            queue_number: Queue number
            requirements: list of skill requirement dicts with 'skill_id', 'min_proficiency', 'required'

        Returns:
            True if requirements were set
        """
        skill_reqs = []
        for req in requirements:
            skill_id = req.get("skill_id")
            min_prof = req.get("min_proficiency", 1)
            required = req.get("required", True)

            if skill_id not in self.skills:
                self.logger.error(f"Skill {skill_id} does not exist")
                continue

            skill_reqs.append(SkillRequirement(skill_id, min_prof, required))

        self.queue_requirements[queue_number] = skill_reqs

        # Store in database
        if self.database and self.database.enabled:
            try:
                # Clear existing requirements
                delete_query = (
                    """
                DELETE FROM queue_skill_requirements WHERE queue_number = %s
                """
                    if self.database.db_type == "postgresql"
                    else """
                DELETE FROM queue_skill_requirements WHERE queue_number = ?
                """
                )
                self.database.execute(delete_query, (queue_number,))

                # Insert new requirements
                for req in skill_reqs:
                    insert_query = (
                        """
                    INSERT INTO queue_skill_requirements (queue_number, skill_id, min_proficiency, required)
                    VALUES (%s, %s, %s, %s)
                    """
                        if self.database.db_type == "postgresql"
                        else """
                    INSERT INTO queue_skill_requirements (queue_number, skill_id, min_proficiency, required)
                    VALUES (?, ?, ?, ?)
                    """
                    )
                    self.database.execute(
                        insert_query,
                        (queue_number, req.skill_id, req.min_proficiency, req.required),
                    )
            except sqlite3.Error as e:
                self.logger.error(f"Failed to store queue requirements in database: {e}")

        self.logger.info(f"set {len(skill_reqs)} skill requirements for queue {queue_number}")
        return True

    def find_best_agents(
        self, queue_number: str, available_agents: list[str], max_results: int = 5
    ) -> list[dict]:
        """
        Find best agents for a queue based on skill requirements

        Args:
            queue_number: Queue number
            available_agents: list of available agent extensions
            max_results: Maximum number of agents to return

        Returns:
            list of agent dicts with 'extension', 'score', 'matching_skills'
        """
        if queue_number not in self.queue_requirements:
            # No requirements, return all available agents
            return [
                {"extension": ext, "score": 1.0, "matching_skills": []}
                for ext in available_agents[:max_results]
            ]

        requirements = self.queue_requirements[queue_number]
        scored_agents = []

        for agent_ext in available_agents:
            score, matching_skills = self._calculate_agent_score(agent_ext, requirements)

            # Filter out agents who don't meet required skills
            if score > 0:
                scored_agents.append(
                    {"extension": agent_ext, "score": score, "matching_skills": matching_skills}
                )

        # Sort by score descending
        scored_agents.sort(key=lambda x: x["score"], reverse=True)

        # If no agents match and fallback is enabled, return any available
        if not scored_agents and self.fallback_to_any_agent:
            self.logger.warning(
                f"No agents match requirements for queue {queue_number}, falling back to any available"
            )
            return [
                {"extension": ext, "score": 0.0, "matching_skills": []}
                for ext in available_agents[:max_results]
            ]

        return scored_agents[:max_results]

    def _calculate_agent_score(
        self, agent_extension: str, requirements: list[SkillRequirement]
    ) -> tuple:
        """
        Calculate agent score based on skill requirements

        Returns:
            tuple of (score, matching_skills)
        """
        if agent_extension not in self.agent_skills:
            return (0.0, [])

        agent_skills = self.agent_skills[agent_extension]
        total_score = 0.0
        required_count = 0
        matched_required = 0
        matching_skills = []

        for req in requirements:
            if req.required:
                required_count += 1

            if req.skill_id in agent_skills:
                agent_skill = agent_skills[req.skill_id]

                # Check if agent meets minimum proficiency
                if agent_skill.proficiency >= req.min_proficiency:
                    # Calculate score based on proficiency (higher is better)
                    skill_score = agent_skill.proficiency / 10.0

                    # Weight required skills more heavily
                    weight = 1.0 if req.required else 0.5
                    total_score += skill_score * weight

                    matching_skills.append(
                        {
                            "skill_id": req.skill_id,
                            "proficiency": agent_skill.proficiency,
                            "required": req.required,
                        }
                    )

                    if req.required:
                        matched_required += 1
            elif req.required:
                # Missing required skill, agent doesn't qualify
                return (0.0, [])

        # Normalize score
        if len(requirements) > 0:
            total_score = total_score / len(requirements)

        return (total_score, matching_skills)

    def get_agent_skills(self, agent_extension: str) -> list[dict]:
        """
        Get all skills for an agent

        Args:
            agent_extension: Agent's extension number

        Returns:
            list of skill dicts
        """
        if agent_extension not in self.agent_skills:
            return []

        skills = []
        for skill_id, agent_skill in self.agent_skills[agent_extension].items():
            skill_info = agent_skill.to_dict()
            if skill_id in self.skills:
                skill_info["name"] = self.skills[skill_id].name
                skill_info["description"] = self.skills[skill_id].description
            skills.append(skill_info)

        return skills

    def get_all_skills(self) -> list[dict]:
        """Get all available skills"""
        return [skill.to_dict() for skill in self.skills.values()]

    def get_queue_requirements(self, queue_number: str) -> list[dict]:
        """
        Get skill requirements for a queue

        Args:
            queue_number: Queue number

        Returns:
            list of requirement dicts
        """
        if queue_number not in self.queue_requirements:
            return []

        reqs = []
        for req in self.queue_requirements[queue_number]:
            req_dict = req.to_dict()
            if req.skill_id in self.skills:
                req_dict["skill_name"] = self.skills[req.skill_id].name
            reqs.append(req_dict)

        return reqs


def get_skills_router(database=None, config: dict | None = None) -> SkillsBasedRouter:
    """Get skills-based router instance"""
    return SkillsBasedRouter(database, config)
