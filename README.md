# 🌟 HabitHub
HabitHub is a web-based habit tracker and productivity app built with Streamlit, Python, and Supabase. It helps users create habits, track daily progress, and monitor weekly performance with minimal manual input. HabitHub automatically logs the current date for each completed habit and provides visual feedback with streaks and stars, turning habit tracking into a motivating and gamified experience.

## ✨ Features

**🔐 User Authentication**: Secure login/signup via Supabase Auth.

**📝 Custom Habit Creation**: Add habits with optional descriptions.

**📅 Daily Habit Logging**: Automatically records today’s date when marking habits complete.

**📊 Weekly Progress Tracking**: Calculates performance and streaks for the week.

**🏆 Visual Feedback**: Stars and badges to motivate consistency.

**⏰ Optional Alerts/Reminders**: Notify users if a habit is missed.

## Project Structure

HABITHUB/
|
|---src/             #core application logic
|    |__logic.py     #Business logic and task
operations
|    |__db.py        #For database operations
|
|---api/             #Backend API
|    |__main.py      # FatsAPI endpoints
|
|---Frontend/        #Frontend application
|     |__app.py      #Streamlit web interface
|
|____requirements.txt   #Python dependencies
|
|______README.md      # Project Documentation
|
|______.env            #Python Variables
     

## Quick Start


### Prerequisties

- Python 3.8 or higher
- A superbase Account
- Git(Push,Cloning)

### 1.Clone or Dowload the project
# Option1: Clone with Git
git clone <repository-url>

# Option2: Dowload and extract the ZIP file

### 2.Install Dependencies
pip install -r requirements.txt

### 3.Set Up Supabase Database
1.Create a Supabase Project:

2.Create the Table:
- Go to the SQL  Editor in your Supabase dashboard
- Run this SQL command:
``` sql

1️⃣ Habits Table

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Habits table
CREATE TABLE public.habits (
    habit_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL DEFAULT gen_random_uuid(),
    name text NOT NULL,
    description text,
    created_at timestamp with time zone DEFAULT now()
);

-- Habit logs table
CREATE TABLE public.habit_logs (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    habit_id uuid REFERENCES public.habits(habit_id),
    date date DEFAULT CURRENT_DATE,
    completed boolean DEFAULT false
);

-- Weekly performance table
CREATE TABLE public.weekly_performance (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL DEFAULT gen_random_uuid(),
    week_start date DEFAULT CURRENT_DATE,
    completion_pct numeric(5,2) DEFAULT 0,
    stars int DEFAULT 0
);

```

3. **Get Your Credentials:

#### 4.Configure R-Environment Varaibales
1.Create a `.env` file in the project root
2.Add your Superbase credentials to `.env`:
 SUPABASE_URL=project_url
SUPABASE_KEY=project_key

### 5.Run the Application

## Streamlit Frontend

streamlit run Frontend/app.py

## FastAPI Backend

cd api
python main.py

the api will be available at :

## How to use

## Technical Details

## Technologies used

- **Frontend**: Streamlit (interactive Python web app)

- **Backend**: Python (handles logic and API calls)

- **Database**: Supabase (PostgreSQL + Auth)

- **Tables**: habits, habit_logs, weekly_performance

### Key Components

1. **`src/db.py`**:Database operations 
    -Handles all CRUD operations with Supabse

2.**`src/logic.py`**:Business logic 
    -Task validation and processing

## Troubleshooting

## Common Issues
  ## write errors here and solutions


## Future enhancements

## Support

if you encounter any issues or have questions:
email-toshithavennapusa@gmail.com
phno:xxxxxxxxxx