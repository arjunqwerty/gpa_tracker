"""MongoDB documents. Every collection the app uses is listed in ALL_DOCUMENTS."""
from app.models.audit_log import AuditLog
from app.models.auth_token import AuthToken
from app.models.configuration import CourseType, CurriculumVersion, GradingScheme, Programme, University
from app.models.course import Course
from app.models.import_job import ImportJob
from app.models.semester import Semester
from app.models.user import User

ALL_DOCUMENTS = [User, University, Programme, CurriculumVersion, CourseType, GradingScheme, Semester, Course, AuditLog, ImportJob, AuthToken]
