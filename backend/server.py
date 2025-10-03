from fastapi import FastAPI, APIRouter, HTTPException, Depends, status, Request, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone, timedelta
import jwt
from passlib.context import CryptContext
from emergentintegrations.llm.chat import LlmChat, UserMessage
import json
import asyncio
import requests

# Load environment variables
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# AI Chat setup
AI_API_KEY = os.environ.get('EMERGENT_LLM_KEY')

# Security setup
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()
JWT_SECRET = "focusflow_secret_key_2025"
JWT_ALGORITHM = "HS256"
TOKEN_EXPIRE_HOURS = 24

# Create the main app
app = FastAPI(title="FocusFlow API", version="1.0.0")
api_router = APIRouter(prefix="/api")

# Pydantic Models
class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: str
    name: str
    picture: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    focus_patterns: Dict[str, Any] = Field(default_factory=dict)
    preferences: Dict[str, Any] = Field(default_factory=dict)

class UserSession(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    session_token: str
    expires_at: datetime
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class UserCreate(BaseModel):
    email: EmailStr
    name: str
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Task(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    title: str
    description: str = ""
    priority: str = "medium"  # low, medium, high, urgent
    task_type: str = "shallow"  # deep, shallow
    estimated_duration: int = 30  # minutes
    actual_duration: Optional[int] = None
    status: str = "pending"  # pending, in_progress, completed
    due_date: Optional[datetime] = None
    scheduled_start: Optional[datetime] = None
    focus_score: float = 0.5  # 0-1, AI predicted focus requirement
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class TaskCreate(BaseModel):
    title: str
    description: str = ""
    due_date: Optional[datetime] = None
    estimated_duration: int = 30

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    due_date: Optional[datetime] = None
    estimated_duration: Optional[int] = None
    actual_duration: Optional[int] = None

class FocusSession(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    task_id: Optional[str] = None
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    focus_level: float = 0.5  # 0-1 scale
    productivity_score: float = 0.5  # 0-1 scale
    energy_level: str = "medium"  # low, medium, high
    session_type: str = "work"  # work, break, deep_work
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ScheduleRequest(BaseModel):
    date: str  # YYYY-MM-DD format

# Utility Functions
def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(hours=TOKEN_EXPIRE_HOURS)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return encoded_jwt

async def get_current_user_from_token(token: str) -> Optional[User]:
    """Helper function to get user from token (JWT or session token)"""
    # First try session token (Google OAuth)
    session = await db.user_sessions.find_one({
        "session_token": token,
        "expires_at": {"$gt": datetime.now(timezone.utc)}
    })
    if session:
        user = await db.users.find_one({"id": session["user_id"]})
        if user:
            return User(**user)
    
    # Fallback to JWT token (email/password auth)
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id:
            user = await db.users.find_one({"id": user_id})
            if user:
                return User(**user)
    except jwt.PyJWTError:
        pass
    
    return None

async def get_current_user(request: Request):
    """Get current user from either cookie or Authorization header"""
    # First check session token from cookie (Google OAuth)
    session_token = request.cookies.get("session_token")
    if session_token:
        user = await get_current_user_from_token(session_token)
        if user:
            return user
    
    # Fallback to Authorization header (JWT)
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        user = await get_current_user_from_token(token)
        if user:
            return user
    
    raise HTTPException(status_code=401, detail="Authentication required")

# AI Functions
async def parse_task_with_ai(task_input: str) -> Dict[str, Any]:
    """Parse natural language task input using AI"""
    try:
        chat = LlmChat(
            api_key=AI_API_KEY,
            session_id=f"task_parser_{datetime.now().timestamp()}",
            system_message="""You are an expert task parsing assistant for FocusFlow productivity app. Parse user input into structured task data.

            CRITICAL REQUIREMENTS:
            - Return ONLY a valid JSON object, no additional text
            - Accurately identify priority keywords: "urgent", "asap", "critical", "high priority" = urgent
            - Look for time pressure indicators: "tomorrow", "today", "deadline", "due" = higher priority
            - Pay special attention to explicit priority words in the input
            
            JSON Format:
            {
                "title": "concise task title (remove priority words)",
                "description": "detailed description if context provided",
                "priority": "urgent|high|medium|low",
                "task_type": "deep|shallow",
                "estimated_duration": minutes_as_integer,
                "due_date": "ISO_datetime_string_or_null",
                "focus_score": float_0_to_1
            }
            
            Classification Rules:
            PRIORITY:
            - urgent: contains "urgent", "asap", "critical", "emergency", time pressure words
            - high: "important", "priority", "deadline" with near dates
            - medium: general tasks without urgency indicators  
            - low: "when possible", "eventually", "someday"
            
            TASK_TYPE:
            - deep: coding, writing, analysis, research, design, complex problem solving
            - shallow: emails, meetings, calls, administrative tasks, data entry
            
            FOCUS_SCORE:
            - 0.8-1.0: deep work requiring high concentration
            - 0.5-0.7: moderate concentration tasks
            - 0.2-0.4: routine/administrative tasks
            
            DURATION ESTIMATION:
            - Simple tasks: 15-30 min
            - Moderate tasks: 30-120 min  
            - Complex projects: 120-480 min
            """
        ).with_model("openai", "gpt-4o")
        
        user_message = UserMessage(text=f"Parse this task input: {task_input}")
        response = await chat.send_message(user_message)
        
        # Clean the response to ensure it's valid JSON
        cleaned_response = response.strip()
        if cleaned_response.startswith('```json'):
            cleaned_response = cleaned_response.replace('```json', '').replace('```', '').strip()
        
        # Parse AI response as JSON
        parsed_data = json.loads(cleaned_response)
        
        # Validate required fields and apply defaults if missing
        validated_data = {
            "title": parsed_data.get("title", task_input),
            "description": parsed_data.get("description", ""),
            "priority": parsed_data.get("priority", "medium"),
            "task_type": parsed_data.get("task_type", "shallow"),
            "estimated_duration": int(parsed_data.get("estimated_duration", 30)),
            "due_date": parsed_data.get("due_date"),
            "focus_score": float(parsed_data.get("focus_score", 0.5))
        }
        
        return validated_data
        
    except Exception as e:
        logging.error(f"AI task parsing failed: {e}")
        # Enhanced fallback parsing with basic keyword detection
        priority = "medium"
        task_type = "shallow"
        focus_score = 0.5
        duration = 30
        
        # Basic keyword detection for fallback
        task_lower = task_input.lower()
        if any(word in task_lower for word in ['urgent', 'asap', 'critical', 'emergency']):
            priority = "urgent"
        elif any(word in task_lower for word in ['important', 'high', 'priority']):
            priority = "high"
        
        if any(word in task_lower for word in ['code', 'develop', 'write', 'analyze', 'design']):
            task_type = "deep"
            focus_score = 0.8
            duration = 120
        
        return {
            "title": task_input,
            "description": "",
            "priority": priority,
            "task_type": task_type,
            "estimated_duration": duration,
            "due_date": None,
            "focus_score": focus_score
        }

async def analyze_focus_patterns(user_id: str) -> Dict[str, float]:
    """Analyze user's focus patterns from completed sessions"""
    sessions = await db.focus_sessions.find({
        "user_id": user_id,
        "end_time": {"$ne": None}
    }).to_list(100)
    
    if not sessions:
        return {"morning": 0.7, "afternoon": 0.5, "evening": 0.3}
    
    # Analyze by time of day
    morning_scores = []
    afternoon_scores = []
    evening_scores = []
    
    for session in sessions:
        hour = session["start_time"].hour
        score = session.get("productivity_score", 0.5)
        
        if 6 <= hour < 12:
            morning_scores.append(score)
        elif 12 <= hour < 18:
            afternoon_scores.append(score)
        else:
            evening_scores.append(score)
    
    patterns = {
        "morning": sum(morning_scores) / len(morning_scores) if morning_scores else 0.7,
        "afternoon": sum(afternoon_scores) / len(afternoon_scores) if afternoon_scores else 0.5,
        "evening": sum(evening_scores) / len(evening_scores) if evening_scores else 0.3
    }
    
    return patterns

async def smart_schedule_tasks(user_id: str, tasks: List[Dict]) -> List[Dict]:
    """AI-powered task scheduling based on focus patterns"""
    patterns = await analyze_focus_patterns(user_id)
    current_hour = datetime.now().hour
    
    # Determine current time period
    if 6 <= current_hour < 12:
        current_focus = patterns["morning"]
    elif 12 <= current_hour < 18:
        current_focus = patterns["afternoon"]  
    else:
        current_focus = patterns["evening"]
    
    # Sort tasks by priority and focus match
    def task_priority_score(task):
        priority_weights = {"urgent": 4, "high": 3, "medium": 2, "low": 1}
        task_focus_score = task.get("focus_score", 0.5)
        
        # Match high-focus tasks with high-focus time periods
        focus_match = 1 - abs(task_focus_score - current_focus)
        
        return (priority_weights.get(task.get("priority", "medium"), 2) * 10) + (focus_match * 5)
    
    # Convert tasks to proper dict format if they contain MongoDB ObjectId
    clean_tasks = []
    for task in tasks:
        if isinstance(task, dict):
            # Remove MongoDB-specific fields that cause serialization issues
            clean_task = {k: v for k, v in task.items() if k != '_id'}
            clean_tasks.append(clean_task)
        else:
            # If it's a Pydantic model, convert to dict
            clean_tasks.append(task.dict() if hasattr(task, 'dict') else dict(task))
    
    sorted_tasks = sorted(clean_tasks, key=task_priority_score, reverse=True)
    return sorted_tasks

# Authentication Routes
@api_router.post("/auth/register")
async def register(user_data: UserCreate):
    # Check if user exists
    existing_user = await db.users.find_one({"email": user_data.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create user
    user_dict = user_data.dict()
    user_dict["password"] = hash_password(user_data.password)
    user = User(email=user_data.email, name=user_data.name)
    user_doc = user.dict()
    user_doc["password"] = user_dict["password"]
    
    await db.users.insert_one(user_doc)
    
    # Create access token
    access_token = create_access_token(data={"sub": user.id})
    return {"access_token": access_token, "token_type": "bearer", "user": user}

@api_router.post("/auth/login")
async def login(user_data: UserLogin):
    user_doc = await db.users.find_one({"email": user_data.email})
    if not user_doc or not verify_password(user_data.password, user_doc["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    user = User(**user_doc)
    access_token = create_access_token(data={"sub": user.id})
    return {"access_token": access_token, "token_type": "bearer", "user": user}

@api_router.get("/auth/me")
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current authenticated user info"""
    return current_user

@api_router.post("/auth/google/session")
async def process_google_session(request: Request, response: Response):
    """Process Google OAuth session ID and create user session"""
    session_id = request.headers.get("X-Session-ID")
    if not session_id:
        raise HTTPException(status_code=400, detail="Session ID required")
    
    try:
        # Get user data from Emergent auth service
        auth_response = requests.get(
            "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data",
            headers={"X-Session-ID": session_id},
            timeout=10
        )
        
        if auth_response.status_code != 200:
            raise HTTPException(status_code=401, detail="Invalid session ID")
        
        auth_data = auth_response.json()
        user_id = auth_data["id"]
        email = auth_data["email"]
        name = auth_data["name"]
        picture = auth_data.get("picture")
        session_token = auth_data["session_token"]
        
        # Check if user exists, create if not
        existing_user = await db.users.find_one({"email": email})
        if existing_user:
            user = User(**existing_user)
        else:
            # Create new user
            user = User(
                id=user_id,
                email=email,
                name=name,
                picture=picture
            )
            await db.users.insert_one(user.dict())
        
        # Create session in database
        session = UserSession(
            user_id=user.id,
            session_token=session_token,
            expires_at=datetime.now(timezone.utc) + timedelta(days=7)
        )
        await db.user_sessions.insert_one(session.dict())
        
        # Set httpOnly cookie
        response.set_cookie(
            key="session_token",
            value=session_token,
            max_age=7 * 24 * 60 * 60,  # 7 days
            path="/",
            secure=True,
            httponly=True,
            samesite="none"
        )
        
        return {"user": user, "session_token": session_token}
        
    except requests.RequestException:
        raise HTTPException(status_code=500, detail="Authentication service unavailable")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Authentication failed: {str(e)}")

@api_router.post("/auth/logout")
async def logout(request: Request, response: Response):
    """Logout user and clear session"""
    session_token = request.cookies.get("session_token")
    if session_token:
        # Delete session from database
        await db.user_sessions.delete_one({"session_token": session_token})
    
    # Clear cookie
    response.delete_cookie(
        key="session_token",
        path="/",
        secure=True,
        httponly=True,
        samesite="none"
    )
    
    return {"message": "Logged out successfully"}

# Task Routes
@api_router.post("/tasks", response_model=Task)
async def create_task(task_data: TaskCreate, current_user: User = Depends(get_current_user)):
    # Parse task using AI if it looks like natural language
    if len(task_data.title.split()) > 5 or any(word in task_data.title.lower() for word in ['by', 'tomorrow', 'today', 'next', 'urgent', 'asap']):
        ai_parsed = await parse_task_with_ai(task_data.title)
        
        task = Task(
            user_id=current_user.id,
            title=ai_parsed.get("title", task_data.title),
            description=ai_parsed.get("description", task_data.description),
            priority=ai_parsed.get("priority", "medium"),
            task_type=ai_parsed.get("task_type", "shallow"),
            estimated_duration=ai_parsed.get("estimated_duration", task_data.estimated_duration),
            focus_score=ai_parsed.get("focus_score", 0.5),
            due_date=datetime.fromisoformat(ai_parsed["due_date"]) if ai_parsed.get("due_date") else task_data.due_date
        )
    else:
        task = Task(user_id=current_user.id, **task_data.dict())
    
    await db.tasks.insert_one(task.dict())
    return task

@api_router.get("/tasks", response_model=List[Task])
async def get_tasks(current_user: User = Depends(get_current_user)):
    tasks = await db.tasks.find({"user_id": current_user.id}).to_list(100)
    task_objects = [Task(**task) for task in tasks]
    
    # Apply smart scheduling
    scheduled_tasks = await smart_schedule_tasks(current_user.id, [task.dict() for task in task_objects])
    return [Task(**task) for task in scheduled_tasks]

@api_router.get("/tasks/{task_id}", response_model=Task)
async def get_task(task_id: str, current_user: User = Depends(get_current_user)):
    task = await db.tasks.find_one({"id": task_id, "user_id": current_user.id})
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return Task(**task)

@api_router.put("/tasks/{task_id}", response_model=Task)
async def update_task(task_id: str, task_data: TaskUpdate, current_user: User = Depends(get_current_user)):
    task = await db.tasks.find_one({"id": task_id, "user_id": current_user.id})
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    update_data = {k: v for k, v in task_data.dict(exclude_unset=True).items() if v is not None}
    update_data["updated_at"] = datetime.now(timezone.utc)
    
    await db.tasks.update_one({"id": task_id}, {"$set": update_data})
    updated_task = await db.tasks.find_one({"id": task_id})
    return Task(**updated_task)

@api_router.delete("/tasks/{task_id}")
async def delete_task(task_id: str, current_user: User = Depends(get_current_user)):
    result = await db.tasks.delete_one({"id": task_id, "user_id": current_user.id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"message": "Task deleted"}

# Focus Session Routes
@api_router.post("/focus-sessions", response_model=FocusSession)
async def start_focus_session(task_id: Optional[str] = None, current_user: User = Depends(get_current_user)):
    session = FocusSession(
        user_id=current_user.id,
        task_id=task_id,
        start_time=datetime.now(timezone.utc)
    )
    await db.focus_sessions.insert_one(session.dict())
    return session

@api_router.put("/focus-sessions/{session_id}/complete")
async def complete_focus_session(
    session_id: str,
    duration_minutes: int,
    productivity_score: float,
    current_user: User = Depends(get_current_user)
):
    session = await db.focus_sessions.find_one({"id": session_id, "user_id": current_user.id})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    update_data = {
        "end_time": datetime.now(timezone.utc),
        "duration_minutes": duration_minutes,
        "productivity_score": productivity_score,
        "focus_level": productivity_score  # Simple mapping for now
    }
    
    await db.focus_sessions.update_one({"id": session_id}, {"$set": update_data})
    
    # If session had a task, mark task as completed if productivity was high
    if session.get("task_id") and productivity_score > 0.7:
        await db.tasks.update_one(
            {"id": session["task_id"]},
            {"$set": {"status": "completed", "actual_duration": duration_minutes}}
        )
    
    return {"message": "Session completed"}

# Analytics Routes
@api_router.get("/analytics/focus-patterns")
async def get_focus_patterns(current_user: User = Depends(get_current_user)):
    patterns = await analyze_focus_patterns(current_user.id)
    return patterns

@api_router.get("/analytics/productivity")
async def get_productivity_stats(current_user: User = Depends(get_current_user)):
    # Get last 7 days of sessions
    week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    sessions = await db.focus_sessions.find({
        "user_id": current_user.id,
        "start_time": {"$gte": week_ago},
        "end_time": {"$ne": None}
    }).to_list(100)
    
    total_focus_time = sum(session.get("duration_minutes", 0) for session in sessions)
    avg_productivity = sum(session.get("productivity_score", 0) for session in sessions) / len(sessions) if sessions else 0
    
    completed_tasks = await db.tasks.count_documents({
        "user_id": current_user.id,
        "status": "completed",
        "updated_at": {"$gte": week_ago}
    })
    
    return {
        "total_focus_minutes_7d": total_focus_time,
        "average_productivity_score": round(avg_productivity, 2),
        "completed_tasks_7d": completed_tasks,
        "focus_sessions_count": len(sessions)
    }

# Schedule Routes
@api_router.post("/schedule/optimize")
async def optimize_schedule(schedule_data: ScheduleRequest, current_user: User = Depends(get_current_user)):
    """Get AI-optimized schedule for a specific date"""
    # Get pending tasks
    task_docs = await db.tasks.find({
        "user_id": current_user.id,
        "status": "pending"
    }).to_list(100)
    
    if not task_docs:
        return {"scheduled_tasks": [], "recommendations": []}
    
    # Convert MongoDB documents to Task objects to handle ObjectId properly
    tasks = []
    for task_doc in task_docs:
        try:
            # Remove MongoDB's _id field to avoid ObjectId serialization issues
            if '_id' in task_doc:
                del task_doc['_id']
            task = Task(**task_doc)
            tasks.append(task.dict())
        except Exception as e:
            # Skip problematic tasks and log the error
            print(f"Error converting task: {e}")
            continue
    
    if not tasks:
        return {"scheduled_tasks": [], "recommendations": []}
    
    # Get optimized order
    optimized_tasks = await smart_schedule_tasks(current_user.id, tasks)
    patterns = await analyze_focus_patterns(current_user.id)
    
    recommendations = [
        f"Your peak focus time appears to be in the morning (score: {patterns['morning']:.1f})",
        f"Schedule deep work tasks between 9-11 AM for best results",
        f"Afternoon focus: {patterns['afternoon']:.1f} - good for moderate complexity tasks",
        f"Evening focus: {patterns['evening']:.1f} - ideal for shallow work and planning"
    ]
    
    return {
        "scheduled_tasks": optimized_tasks[:10],  # Limit to top 10
        "focus_patterns": patterns,
        "recommendations": recommendations
    }

# Health check
@api_router.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc)}

# Include router in the main app
app.include_router(api_router)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)