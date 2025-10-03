import React, { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import axios from 'axios';
import './App.css';

// Import Shadcn UI components
import { Button } from './components/ui/button';
import { Input } from './components/ui/input';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './components/ui/tabs';
import { Badge } from './components/ui/badge';
import { Avatar, AvatarFallback } from './components/ui/avatar';
import { Progress } from './components/ui/progress';
import { Calendar } from './components/ui/calendar';
import { Textarea } from './components/ui/textarea';
import { Switch } from './components/ui/switch';
import { Separator } from './components/ui/separator';
import { Alert, AlertDescription } from './components/ui/alert';
import { toast } from 'sonner';

// Icons from lucide-react
import { 
  Plus, Calendar as CalendarIcon, Target, TrendingUp, 
  Clock, Zap, Moon, Sun, Settings, LogOut, 
  Play, Pause, CheckCircle2, Circle, BarChart3,
  Brain, Timer, Focus, Trophy, ChevronRight
} from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Authentication Context
const AuthContext = React.createContext();

// Auth Provider Component
function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem('focusflow_token'));
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (token) {
      // Verify token and get user data
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
      fetchUserTasks(); // This will verify the token
    }
    setLoading(false);
  }, [token]);

  const fetchUserTasks = async () => {
    try {
      await axios.get(`${API}/tasks`);
    } catch (error) {
      if (error.response?.status === 401) {
        logout();
      }
    }
  };

  const login = async (email, password) => {
    try {
      const response = await axios.post(`${API}/auth/login`, { email, password });
      const { access_token, user: userData } = response.data;
      
      setToken(access_token);
      setUser(userData);
      localStorage.setItem('focusflow_token', access_token);
      axios.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;
      
      toast.success('Welcome back!');
      return true;
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Login failed');
      return false;
    }
  };

  const register = async (name, email, password) => {
    try {
      const response = await axios.post(`${API}/auth/register`, { name, email, password });
      const { access_token, user: userData } = response.data;
      
      setToken(access_token);
      setUser(userData);
      localStorage.setItem('focusflow_token', access_token);
      axios.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;
      
      toast.success('Account created successfully!');
      return true;
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Registration failed');
      return false;
    }
  };

  const logout = () => {
    setUser(null);
    setToken(null);
    localStorage.removeItem('focusflow_token');
    delete axios.defaults.headers.common['Authorization'];
    toast.success('Logged out successfully');
  };

  return (
    <AuthContext.Provider value={{ user, token, login, register, logout, loading }}>
      {children}
    </AuthContext.Provider>
  );
}

// Auth Hook
function useAuth() {
  const context = React.useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

// Landing Page Component
function LandingPage() {
  const { login, register } = useAuth();
  const [showAuth, setShowAuth] = useState(false);
  const [authMode, setAuthMode] = useState('login');
  const [darkMode, setDarkMode] = useState(false);
  const [formData, setFormData] = useState({ name: '', email: '', password: '' });

  const handleAuth = async (e) => {
    e.preventDefault();
    if (authMode === 'login') {
      await login(formData.email, formData.password);
    } else {
      await register(formData.name, formData.email, formData.password);
    }
  };

  return (
    <div className={`min-h-screen transition-all duration-300 ${darkMode ? 'dark bg-slate-900 text-white' : 'bg-gradient-to-br from-blue-50 via-white to-purple-50'}`}>
      {/* Header */}
      <header className="container mx-auto px-4 py-6 flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 bg-gradient-to-r from-blue-600 to-purple-600 rounded-xl flex items-center justify-center">
            <Focus className="w-6 h-6 text-white" />
          </div>
          <h1 className="text-2xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
            FocusFlow
          </h1>
        </div>
        <div className="flex items-center space-x-4">
          <Button
            variant="ghost" 
            size="sm"
            onClick={() => setDarkMode(!darkMode)}
            data-testid="theme-toggle"
          >
            {darkMode ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
          </Button>
          <Button 
            onClick={() => setShowAuth(true)}
            data-testid="get-started-btn"
            className="bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700"
          >
            Get Started
          </Button>
        </div>
      </header>

      {/* Hero Section */}
      <section className="container mx-auto px-4 py-20 text-center">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-5xl md:text-6xl font-bold mb-6 bg-gradient-to-r from-slate-800 to-slate-600 bg-clip-text text-transparent dark:from-white dark:to-slate-300">
            AI-Powered Focus<br />Scheduling Revolution
          </h2>
          <p className="text-xl text-slate-600 dark:text-slate-300 mb-8 max-w-2xl mx-auto leading-relaxed">
            Transform your productivity with intelligent task scheduling that learns your focus patterns and optimizes your daily workflow automatically.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center mb-12">
            <Button 
              size="lg" 
              onClick={() => setShowAuth(true)}
              data-testid="hero-cta-btn"
              className="bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-lg px-8 py-3"
            >
              Start Scheduling Smarter
              <ChevronRight className="w-5 h-5 ml-2" />
            </Button>
            <Button variant="outline" size="lg" className="text-lg px-8 py-3">
              Watch Demo
            </Button>
          </div>
          
          {/* Hero Image */}
          <div className="relative">
            <img 
              src="https://images.unsplash.com/photo-1622086674545-1346776dfef5" 
              alt="Modern workspace with dual monitors showing productivity interface"
              className="rounded-2xl shadow-2xl mx-auto max-w-4xl w-full"
            />
            <div className="absolute inset-0 bg-gradient-to-t from-slate-900/20 to-transparent rounded-2xl"></div>
          </div>
        </div>
      </section>

      {/* Features Grid */}
      <section className="container mx-auto px-4 py-20">
        <div className="text-center mb-16">
          <h3 className="text-3xl font-bold mb-4 text-slate-800 dark:text-white">
            Intelligent Features That Adapt to You
          </h3>
          <p className="text-slate-600 dark:text-slate-300 max-w-2xl mx-auto">
            FocusFlow uses advanced AI to understand your productivity patterns and optimize your schedule in real-time.
          </p>
        </div>
        
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
          {[
            {
              icon: <Brain className="w-8 h-8" />,
              title: "AI Task Parsing",
              description: "Speak naturally: 'Finish report by tomorrow 2pm' and watch AI structure it perfectly.",
              image: "https://images.unsplash.com/photo-1680309915319-d46a0e40a153"
            },
            {
              icon: <Target className="w-8 h-8" />,
              title: "Focus Pattern Learning", 
              description: "Learns when you're most productive and schedules deep work during peak hours.",
              image: "https://images.unsplash.com/photo-1751200065697-4461cc2b43cb"
            },
            {
              icon: <Zap className="w-8 h-8" />,
              title: "Dynamic Reordering",
              description: "Tasks automatically reorder based on your current energy levels and deadlines.",
              image: "https://images.unsplash.com/photo-1514905507308-d4d7832e90cd"
            },
            {
              icon: <BarChart3 className="w-8 h-8" />,
              title: "Smart Analytics",
              description: "Visual insights into your productivity patterns with actionable recommendations.",
              image: "https://images.unsplash.com/photo-1758876201901-68f8f413bf4c"
            },
            {
              icon: <Timer className="w-8 h-8" />,
              title: "Focus Sessions",
              description: "Track work sessions and build better focus habits with AI coaching.",
              image: "https://images.pexels.com/photos/8062358/pexels-photo-8062358.jpeg"
            },
            {
              icon: <Trophy className="w-8 h-8" />,
              title: "Productivity Optimization",
              description: "Get personalized suggestions to improve your workflow and achieve more.",
              image: "https://images.unsplash.com/photo-1622086674545-1346776dfef5"
            }
          ].map((feature, index) => (
            <Card key={index} className="group hover:shadow-xl transition-all duration-300 border-0 bg-white/60 backdrop-blur-sm dark:bg-slate-800/60">
              <CardHeader>
                <div className="w-16 h-16 bg-gradient-to-r from-blue-500 to-purple-500 rounded-xl flex items-center justify-center text-white mb-4 group-hover:scale-110 transition-transform duration-300">
                  {feature.icon}
                </div>
                <CardTitle className="text-xl">{feature.title}</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-slate-600 dark:text-slate-300 mb-4">{feature.description}</p>
                <img 
                  src={feature.image} 
                  alt={feature.title}
                  className="rounded-lg w-full h-32 object-cover opacity-80 group-hover:opacity-100 transition-opacity duration-300"
                />
              </CardContent>
            </Card>
          ))}
        </div>
      </section>

      {/* CTA Section */}
      <section className="container mx-auto px-4 py-20">
        <Card className="text-center p-12 bg-gradient-to-r from-blue-600 to-purple-600 text-white border-0">
          <CardContent>
            <h3 className="text-3xl font-bold mb-4">Ready to Transform Your Productivity?</h3>
            <p className="text-blue-100 mb-8 max-w-2xl mx-auto">
              Join thousands of professionals who've revolutionized their workflow with AI-powered scheduling.
            </p>
            <Button 
              size="lg" 
              variant="secondary"
              onClick={() => setShowAuth(true)}
              data-testid="final-cta-btn"
              className="bg-white text-blue-600 hover:bg-blue-50 text-lg px-8 py-3"
            >
              Start Your Free Trial
              <ChevronRight className="w-5 h-5 ml-2" />
            </Button>
          </CardContent>
        </Card>
      </section>

      {/* Auth Modal */}
      {showAuth && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50" onClick={() => setShowAuth(false)}>
          <Card className="w-full max-w-md mx-4" onClick={(e) => e.stopPropagation()}>
            <CardHeader>
              <CardTitle className="text-center">
                {authMode === 'login' ? 'Welcome Back' : 'Create Account'}
              </CardTitle>
              <CardDescription className="text-center">
                {authMode === 'login' ? 'Sign in to continue to FocusFlow' : 'Start your productivity journey'}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleAuth} className="space-y-4">
                {authMode === 'register' && (
                  <div>
                    <Input
                      type="text"
                      placeholder="Full Name"
                      value={formData.name}
                      onChange={(e) => setFormData({...formData, name: e.target.value})}
                      required
                      data-testid="name-input"
                    />
                  </div>
                )}
                <div>
                  <Input
                    type="email"
                    placeholder="Email"
                    value={formData.email}
                    onChange={(e) => setFormData({...formData, email: e.target.value})}
                    required
                    data-testid="email-input"
                  />
                </div>
                <div>
                  <Input
                    type="password"
                    placeholder="Password"
                    value={formData.password}
                    onChange={(e) => setFormData({...formData, password: e.target.value})}
                    required
                    data-testid="password-input"
                  />
                </div>
                <Button type="submit" className="w-full" data-testid="auth-submit-btn">
                  {authMode === 'login' ? 'Sign In' : 'Create Account'}
                </Button>
              </form>
              <div className="text-center mt-4">
                <button
                  type="button"
                  onClick={() => setAuthMode(authMode === 'login' ? 'register' : 'login')}
                  className="text-blue-600 hover:underline text-sm"
                  data-testid="auth-switch-btn"
                >
                  {authMode === 'login' ? "Don't have an account? Sign up" : "Already have an account? Sign in"}
                </button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}

// Dashboard Component
function Dashboard() {
  const { user, logout } = useAuth();
  const [tasks, setTasks] = useState([]);
  const [analytics, setAnalytics] = useState(null);
  const [focusPatterns, setFocusPatterns] = useState(null);
  const [activeTab, setActiveTab] = useState('today');
  const [darkMode, setDarkMode] = useState(false);
  const [newTask, setNewTask] = useState('');
  const [activeFocusSession, setActiveFocusSession] = useState(null);
  const [selectedDate, setSelectedDate] = useState(new Date());

  useEffect(() => {
    fetchTasks();
    fetchAnalytics();
    fetchFocusPatterns();
  }, []);

  const fetchTasks = async () => {
    try {
      const response = await axios.get(`${API}/tasks`);
      setTasks(response.data);
    } catch (error) {
      toast.error('Failed to fetch tasks');
    }
  };

  const fetchAnalytics = async () => {
    try {
      const response = await axios.get(`${API}/analytics/productivity`);
      setAnalytics(response.data);
    } catch (error) {
      console.error('Failed to fetch analytics:', error);
    }
  };

  const fetchFocusPatterns = async () => {
    try {
      const response = await axios.get(`${API}/analytics/focus-patterns`);
      setFocusPatterns(response.data);
    } catch (error) {
      console.error('Failed to fetch focus patterns:', error);
    }
  };

  const addTask = async (e) => {
    e.preventDefault();
    if (!newTask.trim()) return;

    try {
      const response = await axios.post(`${API}/tasks`, {
        title: newTask,
        description: ''
      });
      setTasks([response.data, ...tasks]);
      setNewTask('');
      toast.success('Task added successfully!');
    } catch (error) {
      toast.error('Failed to add task');
    }
  };

  const updateTask = async (taskId, updates) => {
    try {
      const response = await axios.put(`${API}/tasks/${taskId}`, updates);
      setTasks(tasks.map(task => task.id === taskId ? response.data : task));
      if (updates.status === 'completed') {
        toast.success('Task completed! 🎉');
      }
    } catch (error) {
      toast.error('Failed to update task');
    }
  };

  const getPriorityColor = (priority) => {
    const colors = {
      urgent: 'bg-red-100 text-red-800 border-red-200',
      high: 'bg-orange-100 text-orange-800 border-orange-200',
      medium: 'bg-yellow-100 text-yellow-800 border-yellow-200',
      low: 'bg-green-100 text-green-800 border-green-200'
    };
    return colors[priority] || colors.medium;
  };

  const getTaskTypeIcon = (taskType) => {
    return taskType === 'deep' ? <Brain className="w-4 h-4" /> : <Zap className="w-4 h-4" />;
  };

  const pendingTasks = tasks.filter(task => task.status === 'pending');
  const completedTasks = tasks.filter(task => task.status === 'completed');

  return (
    <div className={`min-h-screen transition-all duration-300 ${darkMode ? 'dark bg-slate-900 text-white' : 'bg-slate-50'}`}>
      {/* Header */}
      <header className="bg-white dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700 sticky top-0 z-40">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 bg-gradient-to-r from-blue-600 to-purple-600 rounded-xl flex items-center justify-center">
              <Focus className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-slate-800 dark:text-white">FocusFlow</h1>
              <p className="text-sm text-slate-500 dark:text-slate-400">Welcome back, {user?.name}</p>
            </div>
          </div>
          
          <div className="flex items-center space-x-4">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setDarkMode(!darkMode)}
              data-testid="dashboard-theme-toggle"
            >
              {darkMode ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
            </Button>
            <Button variant="ghost" size="sm" onClick={logout} data-testid="logout-btn">
              <LogOut className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </header>

      <div className="container mx-auto px-4 py-8">
        <div className="grid lg:grid-cols-4 gap-8">
          {/* Main Content */}
          <div className="lg:col-span-3">
            {/* Quick Stats */}
            <div className="grid md:grid-cols-3 gap-6 mb-8">
              <Card data-testid="tasks-stats-card">
                <CardContent className="p-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm text-slate-500 dark:text-slate-400">Pending Tasks</p>
                      <p className="text-2xl font-bold text-slate-800 dark:text-white">{pendingTasks.length}</p>
                    </div>
                    <Circle className="w-8 h-8 text-blue-500" />
                  </div>
                </CardContent>
              </Card>
              
              <Card data-testid="completed-stats-card">
                <CardContent className="p-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm text-slate-500 dark:text-slate-400">Completed Today</p>
                      <p className="text-2xl font-bold text-slate-800 dark:text-white">{completedTasks.length}</p>
                    </div>
                    <CheckCircle2 className="w-8 h-8 text-green-500" />
                  </div>
                </CardContent>
              </Card>
              
              <Card data-testid="focus-time-card">
                <CardContent className="p-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm text-slate-500 dark:text-slate-400">Focus Time (7d)</p>
                      <p className="text-2xl font-bold text-slate-800 dark:text-white">
                        {analytics?.total_focus_minutes_7d || 0}m
                      </p>
                    </div>
                    <Timer className="w-8 h-8 text-purple-500" />
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Task Input */}
            <Card className="mb-8">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Plus className="w-5 h-5" />
                  Add New Task
                </CardTitle>
                <CardDescription>
                  Type naturally: "Finish report by tomorrow 2pm" or "Call client - urgent"
                </CardDescription>
              </CardHeader>
              <CardContent>
                <form onSubmit={addTask} className="flex gap-3">
                  <Input
                    placeholder="What would you like to focus on?"
                    value={newTask}
                    onChange={(e) => setNewTask(e.target.value)}
                    className="flex-1"
                    data-testid="new-task-input"
                  />
                  <Button type="submit" data-testid="add-task-btn">
                    <Plus className="w-4 h-4" />
                  </Button>
                </form>
              </CardContent>
            </Card>

            {/* Task Lists */}
            <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
              <TabsList className="grid w-full grid-cols-3">
                <TabsTrigger value="today" data-testid="today-tab">Today's Focus</TabsTrigger>
                <TabsTrigger value="calendar" data-testid="calendar-tab">Calendar</TabsTrigger>
                <TabsTrigger value="analytics" data-testid="analytics-tab">Analytics</TabsTrigger>
              </TabsList>

              <TabsContent value="today" className="space-y-4">
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <Target className="w-5 h-5" />
                      Smart Scheduled Tasks
                    </CardTitle>
                    <CardDescription>
                      AI-optimized based on your focus patterns
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-3" data-testid="task-list">
                      {pendingTasks.slice(0, 8).map((task) => (
                        <div key={task.id} className="flex items-center gap-3 p-3 rounded-lg border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors">
                          <button
                            onClick={() => updateTask(task.id, { status: 'completed' })}
                            className="text-slate-400 hover:text-green-500 transition-colors"
                            data-testid={`complete-task-${task.id}`}
                          >
                            <Circle className="w-5 h-5" />
                          </button>
                          
                          <div className="flex-1">
                            <div className="flex items-center gap-2 mb-1">
                              <h4 className="font-medium text-slate-800 dark:text-white">{task.title}</h4>
                              {getTaskTypeIcon(task.task_type)}
                            </div>
                            {task.description && (
                              <p className="text-sm text-slate-500 dark:text-slate-400">{task.description}</p>
                            )}
                            <div className="flex items-center gap-2 mt-2">
                              <Badge className={getPriorityColor(task.priority)}>
                                {task.priority}
                              </Badge>
                              <span className="text-xs text-slate-500">{task.estimated_duration}m</span>
                              <div className="w-16 bg-slate-200 dark:bg-slate-700 rounded-full h-1">
                                <div 
                                  className="bg-gradient-to-r from-blue-500 to-purple-500 h-1 rounded-full"
                                  style={{ width: `${task.focus_score * 100}%` }}
                                ></div>
                              </div>
                            </div>
                          </div>
                          
                          <Button size="sm" variant="outline" data-testid={`start-focus-${task.id}`}>
                            <Play className="w-4 h-4" />
                          </Button>
                        </div>
                      ))}
                      
                      {pendingTasks.length === 0 && (
                        <div className="text-center py-8 text-slate-500 dark:text-slate-400">
                          <Target className="w-12 h-12 mx-auto mb-3 opacity-50" />
                          <p>No tasks yet. Add your first task above!</p>
                        </div>
                      )}
                    </div>
                  </CardContent>
                </Card>
              </TabsContent>

              <TabsContent value="calendar">
                <Card>
                  <CardHeader>
                    <CardTitle>Schedule Overview</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <Calendar
                      mode="single"
                      selected={selectedDate}
                      onSelect={setSelectedDate}
                      className="rounded-md border"
                      data-testid="calendar-widget"
                    />
                  </CardContent>
                </Card>
              </TabsContent>

              <TabsContent value="analytics">
                <div className="grid md:grid-cols-2 gap-6">
                  <Card>
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2">
                        <BarChart3 className="w-5 h-5" />
                        Focus Patterns
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      {focusPatterns && (
                        <div className="space-y-4">
                          <div className="flex justify-between items-center">
                            <span className="text-sm">Morning Focus</span>
                            <div className="flex items-center gap-2">
                              <Progress value={focusPatterns.morning * 100} className="w-20" />
                              <span className="text-sm font-medium">{(focusPatterns.morning * 100).toFixed(0)}%</span>
                            </div>
                          </div>
                          <div className="flex justify-between items-center">
                            <span className="text-sm">Afternoon Focus</span>
                            <div className="flex items-center gap-2">
                              <Progress value={focusPatterns.afternoon * 100} className="w-20" />
                              <span className="text-sm font-medium">{(focusPatterns.afternoon * 100).toFixed(0)}%</span>
                            </div>
                          </div>
                          <div className="flex justify-between items-center">
                            <span className="text-sm">Evening Focus</span>
                            <div className="flex items-center gap-2">
                              <Progress value={focusPatterns.evening * 100} className="w-20" />
                              <span className="text-sm font-medium">{(focusPatterns.evening * 100).toFixed(0)}%</span>
                            </div>
                          </div>
                        </div>
                      )}
                    </CardContent>
                  </Card>
                  
                  <Card>
                    <CardHeader>
                      <CardTitle>Productivity Stats</CardTitle>
                    </CardHeader>
                    <CardContent>
                      {analytics && (
                        <div className="space-y-4">
                          <div className="flex justify-between">
                            <span className="text-sm text-slate-500">Avg Productivity</span>
                            <span className="font-medium">{(analytics.average_productivity_score * 100).toFixed(0)}%</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-sm text-slate-500">Focus Sessions</span>
                            <span className="font-medium">{analytics.focus_sessions_count}</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-sm text-slate-500">Tasks Completed</span>
                            <span className="font-medium">{analytics.completed_tasks_7d}</span>
                          </div>
                        </div>
                      )}
                    </CardContent>
                  </Card>
                </div>
              </TabsContent>
            </Tabs>
          </div>

          {/* Sidebar */}
          <div className="lg:col-span-1">
            <div className="space-y-6">
              {/* Current Focus */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Zap className="w-5 h-5" />
                    Focus Level
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-center">
                    <div className="w-16 h-16 mx-auto mb-3 rounded-full bg-gradient-to-r from-green-400 to-blue-500 flex items-center justify-center">
                      <span className="text-white font-bold text-lg">85%</span>
                    </div>
                    <p className="text-sm text-slate-500">Peak Focus Time</p>
                    <p className="text-xs text-slate-400 mt-1">Great for deep work!</p>
                  </div>
                </CardContent>
              </Card>

              {/* Quick Actions */}
              <Card>
                <CardHeader>
                  <CardTitle>Quick Actions</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <Button className="w-full justify-start" variant="outline" data-testid="start-focus-session">
                    <Play className="w-4 h-4 mr-2" />
                    Start Focus Session
                  </Button>
                  <Button className="w-full justify-start" variant="outline" data-testid="optimize-schedule">
                    <Target className="w-4 h-4 mr-2" />
                    Optimize Schedule
                  </Button>
                  <Button className="w-full justify-start" variant="outline" data-testid="view-insights">
                    <TrendingUp className="w-4 h-4 mr-2" />
                    View Insights
                  </Button>
                </CardContent>
              </Card>

              {/* Recent Achievements */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Trophy className="w-5 h-5" />
                    Recent Wins
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2 text-sm">
                    <div className="flex items-center gap-2">
                      <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                      <span>5 tasks completed today</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
                      <span>3h focus session streak</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="w-2 h-2 bg-purple-500 rounded-full"></div>
                      <span>95% productivity score</span>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// Main App Component
function App() {
  const { token, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="App">
      <Routes>
        <Route 
          path="/" 
          element={token ? <Navigate to="/dashboard" /> : <LandingPage />} 
        />
        <Route 
          path="/dashboard" 
          element={token ? <Dashboard /> : <Navigate to="/" />} 
        />
      </Routes>
    </div>
  );
}

// Root App with Providers
function RootApp() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <App />
      </AuthProvider>
    </BrowserRouter>
  );
}

export default RootApp;