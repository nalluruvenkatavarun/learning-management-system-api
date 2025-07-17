from pydantic import BaseModel, Field, GetJsonSchemaHandler
from datetime import datetime
from typing import List, Optional, Any
from bson import ObjectId

# MongoDB ObjectId field
class PyObjectId(ObjectId):
    @classmethod
    def __get_pydantic_core_schema__(cls, _source_type: Any, _handler: Any) -> dict[str, Any]:
        return {
            'type': 'str',
            'validator': cls.validate,
        }

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)

    @classmethod
    def __get_pydantic_json_schema__(cls, _core_schema: Any, _handler: GetJsonSchemaHandler) -> dict[str, Any]:
        return {"type": "string"}

# Base model with MongoDB ObjectId
class MongoBaseModel(BaseModel):
    id: Optional[PyObjectId] = Field(default=None, alias="_id")

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {ObjectId: str}
    }

# User schemas
class UserCreate(BaseModel):
    username: str
    password: str
    admin: Optional[bool] = False

class UserOut(MongoBaseModel):
    username: str
    is_admin: bool

class Token(BaseModel):
    access_token: str
    token_type: str

class LoginRequest(BaseModel):
    username: str
    password: str

# Course schemas
class CourseCreate(BaseModel):
    title: str
    description: str
    instructor: str
    price: float

class CourseOut(MongoBaseModel):
    title: str
    description: str
    instructor: str
    price: float
    created_by: Optional[PyObjectId] = None

class EnrollmentOut(MongoBaseModel):
    user_id: PyObjectId
    course_id: PyObjectId

# Lesson schemas
class LessonCreate(BaseModel):
    title: str
    video_url: str
    resource_links: str = None

class LessonOut(MongoBaseModel):
    title: str
    video_url: str
    resource_links: str = None
    course_id: PyObjectId

# Quiz schemas
class QuizCreate(BaseModel):
    title: str

class QuizOut(MongoBaseModel):
    title: str
    course_id: PyObjectId

class QuestionCreate(BaseModel):
    text: str
    options: List[str]
    correct_answer: int

class QuestionOut(MongoBaseModel):
    text: str
    options: List[str]
    correct_answer: int
    quiz_id: PyObjectId

# Progress tracking schemas
class LessonCompletionOut(MongoBaseModel):
    user_id: PyObjectId
    lesson_id: PyObjectId
    timestamp: datetime

class QuizAttemptCreate(BaseModel):
    answers: List[int]

class QuizAttemptOut(MongoBaseModel):
    user_id: PyObjectId
    quiz_id: PyObjectId
    answers: List[int]
    score: int
    timestamp: datetime

class CourseProgressOut(BaseModel):
    lessons_completed: int
    total_lessons: int
    quizzes_attempted: int
    total_quizzes: int
    percent_completed: float

# Pagination schemas
class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1, description="Page number (starts from 1)")
    size: int = Field(default=10, ge=1, le=100, description="Number of items per page (max 100)")

class PaginatedResponse(BaseModel):
    items: List[Any]
    total: int
    page: int
    size: int
    pages: int
    has_next: bool
    has_prev: bool 