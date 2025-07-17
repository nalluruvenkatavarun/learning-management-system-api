from pydantic import BaseModel, Field, GetJsonSchemaHandler
from datetime import datetime
from typing import Optional, List, Any, Annotated
from bson import ObjectId
import json

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

# User model
class User(MongoBaseModel):
    username: str
    hashed_password: str
    is_admin: bool = False

# Course model
class Course(MongoBaseModel):
    title: str
    description: str
    instructor: str
    price: float
    created_by: PyObjectId  # Track which admin created the course

# Enrollment model
class Enrollment(MongoBaseModel):
    user_id: PyObjectId
    course_id: PyObjectId

# Lesson model
class Lesson(MongoBaseModel):
    title: str
    video_url: str
    resource_links: Optional[str] = None
    course_id: PyObjectId

# Quiz model
class Quiz(MongoBaseModel):
    title: str
    course_id: PyObjectId

# Question model
class Question(MongoBaseModel):
    text: str
    options: List[str]
    correct_answer: int
    quiz_id: PyObjectId

# LessonCompletion model
class LessonCompletion(MongoBaseModel):
    user_id: PyObjectId
    lesson_id: PyObjectId
    timestamp: datetime = Field(default_factory=datetime.utcnow)

# QuizAttempt model
class QuizAttempt(MongoBaseModel):
    user_id: PyObjectId
    quiz_id: PyObjectId
    answers: List[int]
    score: int
    timestamp: datetime = Field(default_factory=datetime.utcnow) 