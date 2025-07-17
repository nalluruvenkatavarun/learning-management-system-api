# Learning Management System (LMS) API

A comprehensive Learning Management System built with FastAPI, MongoDB, and JWT authentication.

## Features

- 🔐 JWT-based authentication
- 👥 User management with admin roles
- 📚 Course creation and management
- 📖 Lesson management
- 🧠 Quiz system with questions
- 📊 Progress tracking
- 🎯 Admin-only content creation

## Tech Stack

- **Backend**: FastAPI
- **Database**: MongoDB
- **Authentication**: JWT with python-jose
- **Password Hashing**: bcrypt
- **Async Database**: Motor (MongoDB async driver)

## Local Development

### Prerequisites

- Python 3.11+
- MongoDB (local or cloud)

### Installation

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd Learning_management_system
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   # Copy the example environment file
   cp .env.example .env
   
   # Edit .env file with your configuration
   # The file contains:
   # MONGODB_URL=mongodb://localhost:27017
   # DATABASE_NAME=lms_db
   # SECRET_KEY=your_secret_key_here_change_in_production
   # ACCESS_TOKEN_EXPIRE_MINUTES=30
   ```

5. **Run the application**
   ```bash
   python main.py
   ```

6. **Access the API**
   - API: http://localhost:8864
   - Swagger Docs: http://localhost:8864/docs
   - ReDoc: http://localhost:8864/redoc

## Deployment

### Railway (Recommended)

1. **Fork/Clone your repository to GitHub**

2. **Go to [Railway](https://railway.app/)**
   - Sign up with GitHub
   - Click "New Project"
   - Select "Deploy from GitHub repo"

3. **Configure Environment Variables**
   ```
   MONGODB_URL=mongodb+srv://username:password@cluster.mongodb.net/lms_db
   DATABASE_NAME=lms_db
   SECRET_KEY=your-super-secret-key-here
   ACCESS_TOKEN_EXPIRE_MINUTES=30
   ```

4. **Deploy**
   - Railway will automatically detect FastAPI
   - Build and deploy automatically

### Render

1. **Connect your GitHub repository**
2. **Set build command**: `pip install -r requirements.txt`
3. **Set start command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
4. **Add environment variables** (same as Railway)

### Heroku

1. **Install Heroku CLI**
2. **Login and create app**
   ```bash
   heroku login
   heroku create your-lms-app
   ```

3. **Set environment variables**
   ```bash
   heroku config:set MONGODB_URL="your-mongodb-url"
   heroku config:set SECRET_KEY="your-secret-key"
   ```

4. **Deploy**
   ```bash
   git push heroku main
   ```

## API Endpoints

### Authentication
- `POST /signup` - Register new user
- `POST /login` - Login and get JWT token
- `GET /me` - Get current user profile (🔒)

### Admin Management
- `POST /admin/promote` - Promote user to admin (🔒 Admin only)

### Courses
- `POST /courses` - Create course (🔒 Admin only)
- `GET /courses` - List all courses
- `GET /courses/{id}` - Get course details
- `POST /courses/{id}/enroll` - Enroll in course (🔒)

### Lessons
- `POST /courses/{id}/lessons` - Create lesson (🔒 Admin only)
- `GET /courses/{id}/lessons` - List course lessons
- `GET /lessons/{id}` - Get lesson details

### Quizzes
- `POST /courses/{id}/quizzes` - Create quiz (🔒 Admin only)
- `GET /courses/{id}/quizzes` - List course quizzes
- `POST /quizzes/{id}/questions` - Add question (🔒 Admin only)
- `GET /quizzes/{id}/questions` - List quiz questions

### Progress Tracking
- `POST /lessons/{id}/complete` - Mark lesson complete (🔒)
- `POST /quizzes/{id}/attempt` - Attempt quiz (🔒)
- `GET /quizzes/{id}/attempts` - View quiz attempts (🔒)
- `GET /courses/{id}/progress` - View course progress (🔒)

## Usage Examples

### 1. Create Admin User
```bash
# First user automatically becomes admin
curl -X POST "https://your-app.railway.app/signup" \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "adminpass"}'
```

### 2. Login and Get Token
```bash
curl -X POST "https://your-app.railway.app/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "adminpass"}'
```

### 3. Create Course (with token)
```bash
curl -X POST "https://your-app.railway.app/courses" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Python Programming",
    "description": "Learn Python from scratch",
    "instructor": "John Doe",
    "price": 99.99
  }'
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `MONGODB_URL` | MongoDB connection string | `mongodb://localhost:27017` |
| `DATABASE_NAME` | Database name | `lms_db` |
| `SECRET_KEY` | JWT secret key | `your_secret_key_here_change_in_production` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | JWT token expiry | `30` |

## Security Notes

- Change `SECRET_KEY` in production
- Use strong passwords
- Enable HTTPS in production
- Regularly rotate JWT secrets
- Use environment variables for sensitive data
- Configure CORS properly for production
- Use MongoDB Atlas for production database
- Enable rate limiting
- Monitor application logs

## Production Deployment

For production deployment instructions, see [DEPLOYMENT.md](DEPLOYMENT.md)

### Quick Production Setup

1. **Generate a strong secret key:**
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

2. **Set up environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env with production values
   ```

3. **Deploy to Railway (recommended):**
   - Fork this repository
   - Connect to Railway
   - Set environment variables
   - Deploy automatically

### Health Check

Monitor your application health:
```bash
curl https://yourdomain.com/health
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

MIT License 