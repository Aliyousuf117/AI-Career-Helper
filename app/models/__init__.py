"""ORM models. Import everything here so `Base.metadata` knows all tables."""

from app.models.agent import ApprovalRequest, AuditLog, OptOutContact, OutreachMessage
from app.models.assessment import Quiz, QuizAttempt
from app.models.base import (
    ApprovalStatus,
    Base,
    Budget,
    DocumentKind,
    ExperienceKind,
    ExtractionStatus,
    JobMatchStatus,
    OutreachStatus,
    QuizKind,
    RegistrationStatus,
    ResourceStatus,
    SkillLevel,
    SkillSource,
    StageStatus,
    UserStatus,
)
from app.models.document import Document
from app.models.jobs import JobMatch, JobPosting
from app.models.profile import Certificate, Experience, Profile, Project
from app.models.roadmap import CalendarEvent, Registration, Resource, Roadmap, Stage
from app.models.skill import Role, RoleSkillRequirement, Skill, UserSkill
from app.models.user import OAuthAccount, User

__all__ = [
    "ApprovalRequest",
    "ApprovalStatus",
    "AuditLog",
    "Base",
    "Budget",
    "CalendarEvent",
    "Certificate",
    "Document",
    "DocumentKind",
    "Experience",
    "ExperienceKind",
    "ExtractionStatus",
    "JobMatch",
    "JobMatchStatus",
    "JobPosting",
    "OAuthAccount",
    "OptOutContact",
    "OutreachMessage",
    "OutreachStatus",
    "Profile",
    "Project",
    "Quiz",
    "QuizAttempt",
    "QuizKind",
    "Registration",
    "RegistrationStatus",
    "Resource",
    "ResourceStatus",
    "Roadmap",
    "Role",
    "RoleSkillRequirement",
    "Skill",
    "SkillLevel",
    "SkillSource",
    "Stage",
    "StageStatus",
    "User",
    "UserSkill",
    "UserStatus",
]
