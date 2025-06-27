#!/usr/bin/env python3
"""
Script to set up Supabase database tables and initial data
"""

import asyncio
import sys
from pathlib import Path

# Add the parent directory to the path so we can import from app
sys.path.append(str(Path(__file__).parent.parent))

from app.database.supabase_client import supabase_client
from app.utils.logging import configure_logging, get_logger

configure_logging()
logger = get_logger(__name__)


async def create_tables():
    """Create the necessary database tables"""
    
    # SQL for creating tables
    tables_sql = """
    -- Enable UUID extension
    CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
    
    -- Profiles table (extends Supabase auth.users)
    CREATE TABLE IF NOT EXISTS profiles (
        id UUID REFERENCES auth.users PRIMARY KEY,
        email TEXT,
        full_name TEXT,
        role TEXT DEFAULT 'teacher',
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );
    
    -- Enable RLS on profiles
    ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
    
    -- Policy: Users can view and update their own profile
    CREATE POLICY "Users can view own profile" ON profiles
        FOR SELECT USING (auth.uid() = id);
        
    CREATE POLICY "Users can update own profile" ON profiles
        FOR UPDATE USING (auth.uid() = id);
    
    -- Lessons table
    CREATE TABLE IF NOT EXISTS lessons (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        user_id UUID REFERENCES profiles(id) ON DELETE CASCADE,
        title TEXT NOT NULL,
        topic TEXT NOT NULL,
        grade TEXT NOT NULL,
        subject TEXT NOT NULL,
        curriculum TEXT,
        difficulty REAL CHECK (difficulty >= 0.0 AND difficulty <= 1.0),
        blocks JSONB NOT NULL,
        metadata JSONB,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );
    
    -- Enable RLS on lessons
    ALTER TABLE lessons ENABLE ROW LEVEL SECURITY;
    
    -- Policy: Users can manage their own lessons
    CREATE POLICY "Users can view own lessons" ON lessons
        FOR SELECT USING (auth.uid() = user_id);
        
    CREATE POLICY "Users can insert own lessons" ON lessons
        FOR INSERT WITH CHECK (auth.uid() = user_id);
        
    CREATE POLICY "Users can update own lessons" ON lessons
        FOR UPDATE USING (auth.uid() = user_id);
        
    CREATE POLICY "Users can delete own lessons" ON lessons
        FOR DELETE USING (auth.uid() = user_id);
    
    -- Indexes for better performance
    CREATE INDEX IF NOT EXISTS idx_lessons_user_id ON lessons(user_id);
    CREATE INDEX IF NOT EXISTS idx_lessons_created_at ON lessons(created_at DESC);
    CREATE INDEX IF NOT EXISTS idx_lessons_subject ON lessons(subject);
    CREATE INDEX IF NOT EXISTS idx_lessons_grade ON lessons(grade);
    
    -- Function to automatically update updated_at timestamp
    CREATE OR REPLACE FUNCTION update_updated_at_column()
    RETURNS TRIGGER AS $$
    BEGIN
        NEW.updated_at = NOW();
        RETURN NEW;
    END;
    $$ language 'plpgsql';
    
    -- Trigger for lessons table
    DROP TRIGGER IF EXISTS update_lessons_updated_at ON lessons;
    CREATE TRIGGER update_lessons_updated_at
        BEFORE UPDATE ON lessons
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column();
    
    -- Trigger for profiles table
    DROP TRIGGER IF EXISTS update_profiles_updated_at ON profiles;
    CREATE TRIGGER update_profiles_updated_at
        BEFORE UPDATE ON profiles
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column();
    """
    
    try:
        # Execute the SQL
        client = supabase_client.service_client
        result = client.rpc('exec_sql', {'sql': tables_sql}).execute()
        
        logger.info("Database tables created successfully")
        return True
        
    except Exception as e:
        # Try alternative approach - execute statements individually
        logger.warning("Bulk SQL execution failed, trying individual statements", error=str(e))
        
        statements = [
            'CREATE EXTENSION IF NOT EXISTS "uuid-ossp"',
            '''CREATE TABLE IF NOT EXISTS profiles (
                id UUID REFERENCES auth.users PRIMARY KEY,
                email TEXT,
                full_name TEXT,
                role TEXT DEFAULT 'teacher',
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )''',
            'ALTER TABLE profiles ENABLE ROW LEVEL SECURITY',
            '''CREATE TABLE IF NOT EXISTS lessons (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
                title TEXT NOT NULL,
                topic TEXT NOT NULL,
                grade TEXT NOT NULL,
                subject TEXT NOT NULL,
                curriculum TEXT,
                difficulty REAL CHECK (difficulty >= 0.0 AND difficulty <= 1.0),
                blocks JSONB NOT NULL,
                metadata JSONB,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )''',
            'ALTER TABLE lessons ENABLE ROW LEVEL SECURITY',
            'CREATE INDEX IF NOT EXISTS idx_lessons_user_id ON lessons(user_id)',
            'CREATE INDEX IF NOT EXISTS idx_lessons_created_at ON lessons(created_at DESC)'
        ]
        
        success_count = 0
        for statement in statements:
            try:
                client.rpc('exec_sql', {'sql': statement}).execute()
                success_count += 1
            except Exception as stmt_error:
                logger.error("Failed to execute statement", statement=statement[:50], error=str(stmt_error))
        
        logger.info(f"Executed {success_count}/{len(statements)} SQL statements successfully")
        return success_count > 0


async def create_sample_profile():
    """Create a sample profile for MVP testing"""
    try:
        client = supabase_client.client
        
        # Check if sample profile already exists
        existing = client.table('profiles').select('id').eq('id', 'mvp-user-123').execute()
        
        if existing.data:
            logger.info("Sample profile already exists")
            return
        
        # Note: In a real app, this would be created when user signs up
        # For MVP, we'll create a direct entry (this may not work with RLS enabled)
        sample_profile = {
            'id': 'mvp-user-123',  # This would be a real UUID from auth.users
            'email': 'teacher@structural-learning.com',
            'full_name': 'Sample Teacher',
            'role': 'teacher'
        }
        
        result = client.table('profiles').insert(sample_profile).execute()
        logger.info("Sample profile created", profile_id=sample_profile['id'])
        
    except Exception as e:
        logger.warning("Could not create sample profile", error=str(e))
        logger.info("Sample profile creation skipped - will be created on first lesson generation")


async def verify_setup():
    """Verify that the database setup is working"""
    try:
        client = supabase_client.client
        
        # Test basic table access
        lessons_count = client.table('lessons').select('id', count='exact').execute()
        logger.info("Lessons table accessible", count=lessons_count.count)
        
        profiles_count = client.table('profiles').select('id', count='exact').execute()
        logger.info("Profiles table accessible", count=profiles_count.count)
        
        return True
        
    except Exception as e:
        logger.error("Database verification failed", error=str(e))
        return False


async def main():
    """Main setup function"""
    logger.info("Starting Supabase database setup")
    
    # Create tables
    tables_created = await create_tables()
    if not tables_created:
        logger.error("Failed to create database tables")
        return False
    
    # Create sample profile
    await create_sample_profile()
    
    # Verify setup
    setup_verified = await verify_setup()
    if not setup_verified:
        logger.error("Database setup verification failed")
        return False
    
    logger.info("Supabase database setup completed successfully")
    return True


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)