import os
from fastapi import APIRouter, Depends, HTTPException, Security, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.openapi.models import SecurityScheme
from typing import List
import json
from bson import ObjectId
from middleware import limiter, get_rate_limit
from database import (
    users_collection, courses_collection, enrollments_collection,
    lessons_collection, quizzes_collection, questions_collection,
    lesson_completions_collection, quiz_attempts_collection
)
from models import User, Course, Enrollment, Lesson, Quiz, Question, LessonCompletion, QuizAttempt
from schemas import (
    UserCreate, UserOut, Token, LoginRequest, CourseCreate, CourseOut, EnrollmentOut,
    LessonCreate, LessonOut, QuizCreate, QuizOut, QuestionCreate, QuestionOut,
    LessonCompletionOut, QuizAttemptCreate, QuizAttemptOut, CourseProgressOut,
    PaginationParams, PaginatedResponse
)
from auth import (
    get_password_hash, authenticate_user, create_access_token, 
    ACCESS_TOKEN_EXPIRE_MINUTES, timedelta, get_current_user, get_current_admin_user
)
from datetime import datetime

# Helper function to check if user is the course creator
async def get_course_creator_user(course_id: str, current_user: User) -> User:
    course = await courses_collection.find_one({"_id": ObjectId(course_id)})
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    # Handle courses that might not have created_by field (old data)
    if "created_by" not in course or course["created_by"] is None:
        raise HTTPException(status_code=403, detail="This course was created before ownership tracking was implemented. Only admins can modify it.")
    
    if course["created_by"] != ObjectId(current_user.id):
        raise HTTPException(status_code=403, detail="Only the course creator can modify this course")
    
    return current_user

# Create router
router = APIRouter()

# Helper function for pagination
async def paginate_collection(collection, query=None, page=1, size=10):
    """Helper function to paginate MongoDB collections"""
    if query is None:
        query = {}
    
    # Calculate skip value
    skip = (page - 1) * size
    
    # Get total count
    total = await collection.count_documents(query)
    
    # Get paginated results
    cursor = collection.find(query).skip(skip).limit(size)
    items = []
    async for item in cursor:
        item["_id"] = str(item["_id"])
        items.append(item)
    
    # Calculate pagination info
    pages = (total + size - 1) // size  # Ceiling division
    has_next = page < pages
    has_prev = page > 1
    
    return {
        "items": items,
        "total": total,
        "page": page,
        "size": size,
        "pages": pages,
        "has_next": has_next,
        "has_prev": has_prev
    }

# Authentication routes
@router.post("/signup", response_model=UserOut, tags=["Authentication"])
@limiter.limit("5/minute")
async def signup(request: Request, user: UserCreate):
    existing_user = await users_collection.find_one({"username": user.username})
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    hashed_password = get_password_hash(user.password)
    
    # Check if this is the first user (make them admin)
    user_count = await users_collection.count_documents({})
    is_first_user = user_count == 0
    
    # Determine admin status: first user is always admin, or if admin parameter is True
    is_admin = is_first_user or user.admin
    
    user_data = {
        "username": user.username,
        "hashed_password": hashed_password,
        "is_admin": is_admin
    }
    result = await users_collection.insert_one(user_data)
    user_data["_id"] = str(result.inserted_id)  # Convert ObjectId to string
    return UserOut(**user_data)



@router.post("/login", response_model=Token, tags=["Authentication"])
@limiter.limit("10/minute")
async def login(request: Request, login_data: LoginRequest):
    user = await authenticate_user(login_data.username, login_data.password)
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


# Course routes
@router.post("/create_course", response_model=CourseOut, dependencies=[Depends(get_current_admin_user)], tags=["Courses"])
async def create_course(course: CourseCreate, current_user: User = Depends(get_current_admin_user)):
    course_data = course.model_dump()
    course_data["created_by"] = ObjectId(current_user.id)  # Store the creator's ID
    result = await courses_collection.insert_one(course_data)
    course_data["_id"] = str(result.inserted_id)  # Convert ObjectId to string
    course_data["created_by"] = str(course_data["created_by"])  # Convert ObjectId to string
    return CourseOut(**course_data)

@router.get("/courses", response_model=PaginatedResponse, tags=["Courses"])
@limiter.limit(get_rate_limit())
async def list_courses(
    request: Request,
    pagination: PaginationParams = Depends()
):
    """List courses with pagination"""
    result = await paginate_collection(
        courses_collection, 
        page=pagination.page, 
        size=pagination.size
    )
    
    # Convert items to CourseOut format
    courses = []
    for course in result["items"]:
        # Handle courses that might not have created_by field (old data)
        if "created_by" in course:
            course["created_by"] = str(course["created_by"])  # Convert ObjectId to string
        else:
            course["created_by"] = None  # Set default for old courses
        courses.append(CourseOut(**course))
    
    result["items"] = courses
    return PaginatedResponse(**result)

@router.get("/courses/{course_id}", response_model=CourseOut, tags=["Courses"])
async def get_course(course_id: str):
    try:
        course = await courses_collection.find_one({"_id": ObjectId(course_id)})
        if not course:
            raise HTTPException(status_code=404, detail="Course not found")
        course["_id"] = str(course["_id"])  # Convert ObjectId to string
        # Handle courses that might not have created_by field (old data)
        if "created_by" in course:
            course["created_by"] = str(course["created_by"])  # Convert ObjectId to string
        else:
            course["created_by"] = None  # Set default for old courses
        return CourseOut(**course)
    except Exception as e:
        if "invalid ObjectId" in str(e) or not ObjectId.is_valid(course_id):
            raise HTTPException(status_code=400, detail="Invalid course ID format")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/courses/{course_id}/enroll", response_model=EnrollmentOut, dependencies=[Depends(get_current_user)], tags=["Courses"])
async def enroll_course(course_id: str, current_user: User = Depends(get_current_user)):
    course = await courses_collection.find_one({"_id": ObjectId(course_id)})
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    # Check if already enrolled
    existing_enrollment = await enrollments_collection.find_one({
        "user_id": ObjectId(current_user.id),
        "course_id": ObjectId(course_id)
    })
    if existing_enrollment:
        raise HTTPException(status_code=400, detail="Already enrolled in this course")
    
    enrollment_data = {
        "user_id": ObjectId(current_user.id),
        "course_id": ObjectId(course_id)
    }
    result = await enrollments_collection.insert_one(enrollment_data)
    enrollment_data["_id"] = str(result.inserted_id)  # Convert ObjectId to string
    enrollment_data["user_id"] = str(enrollment_data["user_id"])  # Convert ObjectId to string
    enrollment_data["course_id"] = str(enrollment_data["course_id"])  # Convert ObjectId to string
    return EnrollmentOut(**enrollment_data)

# Lesson routes
@router.post("/courses/{course_id}/lessons", response_model=LessonOut, dependencies=[Depends(get_current_admin_user)])
async def create_lesson(course_id: str, lesson: LessonCreate, current_user: User = Depends(get_current_admin_user)):
    # Check if current user is the course creator
    await get_course_creator_user(course_id, current_user)
    
    lesson_data = lesson.model_dump()
    lesson_data["course_id"] = ObjectId(course_id)
    result = await lessons_collection.insert_one(lesson_data)
    lesson_data["_id"] = str(result.inserted_id)  # Convert ObjectId to string
    lesson_data["course_id"] = str(lesson_data["course_id"])  # Convert ObjectId to string
    return LessonOut(**lesson_data)

@router.get("/courses/{course_id}/lessons", response_model=PaginatedResponse)
@limiter.limit(get_rate_limit())
async def list_lessons(
    request: Request,
    course_id: str,
    pagination: PaginationParams = Depends()
):
    """List lessons for a course with pagination"""
    try:
        result = await paginate_collection(
            lessons_collection,
            query={"course_id": ObjectId(course_id)},
            page=pagination.page,
            size=pagination.size
        )
        
        # Convert items to LessonOut format
        lessons = []
        for lesson in result["items"]:
            lesson["course_id"] = str(lesson["course_id"])  # Convert ObjectId to string
            lessons.append(LessonOut(**lesson))
        
        result["items"] = lessons
        return PaginatedResponse(**result)
    except Exception as e:
        if "invalid ObjectId" in str(e) or not ObjectId.is_valid(course_id):
            raise HTTPException(status_code=400, detail="Invalid course ID format")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/lessons/{lesson_id}", response_model=LessonOut)
async def get_lesson(lesson_id: str):
    lesson = await lessons_collection.find_one({"_id": ObjectId(lesson_id)})
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    lesson["_id"] = str(lesson["_id"])  # Convert ObjectId to string
    lesson["course_id"] = str(lesson["course_id"])  # Convert ObjectId to string
    return LessonOut(**lesson)

# Quiz routes
@router.post("/courses/{course_id}/quizzes", response_model=QuizOut, dependencies=[Depends(get_current_admin_user)])
async def create_quiz(course_id: str, quiz: QuizCreate, current_user: User = Depends(get_current_admin_user)):
    # Check if current user is the course creator
    await get_course_creator_user(course_id, current_user)
    
    quiz_data = quiz.model_dump()
    quiz_data["course_id"] = ObjectId(course_id)
    result = await quizzes_collection.insert_one(quiz_data)
    quiz_data["_id"] = str(result.inserted_id)  # Convert ObjectId to string
    quiz_data["course_id"] = str(quiz_data["course_id"])  # Convert ObjectId to string
    return QuizOut(**quiz_data)

@router.get("/courses/{course_id}/quizzes", response_model=PaginatedResponse)
@limiter.limit(get_rate_limit())
async def list_quizzes(
    request: Request,
    course_id: str,
    pagination: PaginationParams = Depends()
):
    """List quizzes for a course with pagination"""
    try:
        result = await paginate_collection(
            quizzes_collection,
            query={"course_id": ObjectId(course_id)},
            page=pagination.page,
            size=pagination.size
        )
        
        # Convert items to QuizOut format
        quizzes = []
        for quiz in result["items"]:
            quiz["course_id"] = str(quiz["course_id"])  # Convert ObjectId to string
            quizzes.append(QuizOut(**quiz))
        
        result["items"] = quizzes
        return PaginatedResponse(**result)
    except Exception as e:
        if "invalid ObjectId" in str(e) or not ObjectId.is_valid(course_id):
            raise HTTPException(status_code=400, detail="Invalid course ID format")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/quizzes/{quiz_id}/questions", response_model=QuestionOut, dependencies=[Depends(get_current_admin_user)])
async def create_question(quiz_id: str, question: QuestionCreate, current_user: User = Depends(get_current_admin_user)):
    quiz = await quizzes_collection.find_one({"_id": ObjectId(quiz_id)})
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    
    # Check if current user is the course creator (quiz belongs to a course)
    await get_course_creator_user(str(quiz["course_id"]), current_user)
    
    question_data = question.model_dump()
    question_data["quiz_id"] = ObjectId(quiz_id)
    result = await questions_collection.insert_one(question_data)
    question_data["_id"] = str(result.inserted_id)  # Convert ObjectId to string
    question_data["quiz_id"] = str(question_data["quiz_id"])  # Convert ObjectId to string
    return QuestionOut(**question_data)

@router.get("/quizzes/{quiz_id}/questions", response_model=PaginatedResponse)
@limiter.limit(get_rate_limit())
async def list_questions(
    request: Request,
    quiz_id: str,
    pagination: PaginationParams = Depends()
):
    """List questions for a quiz with pagination"""
    try:
        result = await paginate_collection(
            questions_collection,
            query={"quiz_id": ObjectId(quiz_id)},
            page=pagination.page,
            size=pagination.size
        )
        
        # Convert items to QuestionOut format
        questions = []
        for question in result["items"]:
            question["quiz_id"] = str(question["quiz_id"])  # Convert ObjectId to string
            questions.append(QuestionOut(**question))
        
        result["items"] = questions
        return PaginatedResponse(**result)
    except Exception as e:
        if "invalid ObjectId" in str(e) or not ObjectId.is_valid(quiz_id):
            raise HTTPException(status_code=400, detail="Invalid quiz ID format")
        raise HTTPException(status_code=500, detail="Internal server error")

# Progress tracking routes
@router.post("/lessons/{lesson_id}/complete", response_model=LessonCompletionOut, dependencies=[Depends(get_current_user)])
async def complete_lesson(lesson_id: str, current_user: User = Depends(get_current_user)):
    lesson = await lessons_collection.find_one({"_id": ObjectId(lesson_id)})
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    
    # Check if already completed
    existing_completion = await lesson_completions_collection.find_one({
        "user_id": ObjectId(current_user.id),
        "lesson_id": ObjectId(lesson_id)
    })
    if existing_completion:
        raise HTTPException(status_code=400, detail="Lesson already marked as completed")
    
    completion_data = {
        "user_id": ObjectId(current_user.id),
        "lesson_id": ObjectId(lesson_id),
        "timestamp": datetime.utcnow()
    }
    result = await lesson_completions_collection.insert_one(completion_data)
    completion_data["_id"] = str(result.inserted_id)  # Convert ObjectId to string
    completion_data["user_id"] = str(completion_data["user_id"])  # Convert ObjectId to string
    completion_data["lesson_id"] = str(completion_data["lesson_id"])  # Convert ObjectId to string
    return LessonCompletionOut(**completion_data)

@router.post("/quizzes/{quiz_id}/attempt", response_model=QuizAttemptOut, dependencies=[Depends(get_current_user)])
async def attempt_quiz(quiz_id: str, attempt: QuizAttemptCreate, current_user: User = Depends(get_current_user)):
    quiz = await quizzes_collection.find_one({"_id": ObjectId(quiz_id)})
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    
    questions = []
    async for question in questions_collection.find({"quiz_id": ObjectId(quiz_id)}):
        question["_id"] = str(question["_id"])  # Convert ObjectId to string
        question["quiz_id"] = str(question["quiz_id"])  # Convert ObjectId to string
        questions.append(Question(**question))
    
    if len(attempt.answers) != len(questions):
        raise HTTPException(status_code=400, detail="Number of answers does not match number of questions")
    
    score = 0
    for i, q in enumerate(questions):
        if i < len(attempt.answers) and attempt.answers[i] == q.correct_answer:
            score += 1
    
    attempt_data = {
        "user_id": ObjectId(current_user.id),
        "quiz_id": ObjectId(quiz_id),
        "answers": attempt.answers,
        "score": score,
        "timestamp": datetime.utcnow()
    }
    result = await quiz_attempts_collection.insert_one(attempt_data)
    attempt_data["_id"] = str(result.inserted_id)  # Convert ObjectId to string
    attempt_data["user_id"] = str(attempt_data["user_id"])  # Convert ObjectId to string
    attempt_data["quiz_id"] = str(attempt_data["quiz_id"])  # Convert ObjectId to string
    return QuizAttemptOut(**attempt_data)

@router.get("/quizzes/{quiz_id}/attempts", response_model=PaginatedResponse, dependencies=[Depends(get_current_user)])
@limiter.limit(get_rate_limit())
async def list_quiz_attempts(
    request: Request,
    quiz_id: str,
    current_user: User = Depends(get_current_user),
    pagination: PaginationParams = Depends()
):
    """List quiz attempts for a user with pagination"""
    try:
        result = await paginate_collection(
            quiz_attempts_collection,
            query={
                "quiz_id": ObjectId(quiz_id),
                "user_id": ObjectId(current_user.id)
            },
            page=pagination.page,
            size=pagination.size
        )
        
        # Convert items to QuizAttemptOut format
        attempts = []
        for attempt in result["items"]:
            attempt["user_id"] = str(attempt["user_id"])  # Convert ObjectId to string
            attempt["quiz_id"] = str(attempt["quiz_id"])  # Convert ObjectId to string
            attempts.append(QuizAttemptOut(**attempt))
        
        result["items"] = attempts
        return PaginatedResponse(**result)
    except Exception as e:
        if "invalid ObjectId" in str(e) or not ObjectId.is_valid(quiz_id):
            raise HTTPException(status_code=400, detail="Invalid quiz ID format")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/courses/{course_id}/progress", response_model=CourseProgressOut, dependencies=[Depends(get_current_user)])
async def get_course_progress(course_id: str, current_user: User = Depends(get_current_user)):
    # Count total lessons
    total_lessons = await lessons_collection.count_documents({"course_id": ObjectId(course_id)})
    
    # Count completed lessons
    lesson_ids = []
    async for lesson in lessons_collection.find({"course_id": ObjectId(course_id)}):
        lesson_ids.append(lesson["_id"])
    
    lessons_completed = await lesson_completions_collection.count_documents({
        "user_id": ObjectId(current_user.id),
        "lesson_id": {"$in": lesson_ids}
    })
    
    # Count total quizzes
    total_quizzes = await quizzes_collection.count_documents({"course_id": ObjectId(course_id)})
    
    # Count attempted quizzes
    quiz_ids = []
    async for quiz in quizzes_collection.find({"course_id": ObjectId(course_id)}):
        quiz_ids.append(quiz["_id"])
    
    quizzes_attempted = await quiz_attempts_collection.count_documents({
        "user_id": ObjectId(current_user.id),
        "quiz_id": {"$in": quiz_ids}
    })
    
    percent_completed = 0.0
    if total_lessons > 0:
        percent_completed = (lessons_completed / total_lessons) * 100
    
    return CourseProgressOut(
        lessons_completed=lessons_completed,
        total_lessons=total_lessons,
        quizzes_attempted=quizzes_attempted,
        total_quizzes=total_quizzes,
        percent_completed=percent_completed
    ) 