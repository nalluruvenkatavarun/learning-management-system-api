from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import MongoClient
import os
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)

# MongoDB configuration with environment variables
MONGODB_URL = os.getenv("MONGODB_URI", os.getenv("MONGODB_URL", "mongodb://localhost:27017"))
DATABASE_NAME = os.getenv("DATABASE_NAME", "lms_db")

# Validate MongoDB URL
if not MONGODB_URL:
    raise ValueError("MONGODB_URI or MONGODB_URL environment variable is required")

logger.info(f"Connecting to MongoDB: {MONGODB_URL}")
logger.info(f"Using database: {DATABASE_NAME}")

try:
    # Async client for FastAPI
    async_client = AsyncIOMotorClient(
        MONGODB_URL,
        serverSelectionTimeoutMS=5000,  # 5 second timeout
        connectTimeoutMS=5000,
        socketTimeoutMS=5000
    )
    database = async_client[DATABASE_NAME]

    # Sync client for operations that need it
    sync_client = MongoClient(
        MONGODB_URL,
        serverSelectionTimeoutMS=5000,
        connectTimeoutMS=5000,
        socketTimeoutMS=5000
    )
    sync_database = sync_client[DATABASE_NAME]
    
    logger.info("MongoDB connection established successfully")
except Exception as e:
    logger.error(f"Failed to connect to MongoDB: {e}")
    raise

# Collections
users_collection = database.users
courses_collection = database.courses
enrollments_collection = database.enrollments
lessons_collection = database.lessons
quizzes_collection = database.quizzes
questions_collection = database.questions
lesson_completions_collection = database.lesson_completions
quiz_attempts_collection = database.quiz_attempts

# Sync collections
sync_users_collection = sync_database.users
sync_courses_collection = sync_database.courses
sync_enrollments_collection = sync_database.enrollments
sync_lessons_collection = sync_database.lessons
sync_quizzes_collection = sync_database.quizzes
sync_questions_collection = sync_database.questions
sync_lesson_completions_collection = sync_database.lesson_completions
sync_quiz_attempts_collection = sync_database.quiz_attempts

def get_database():
    return database 