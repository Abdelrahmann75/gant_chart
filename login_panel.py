import streamlit as st
from streamlit import session_state as state
import sqlite3
from typing import Optional, Tuple
from datetime import datetime, timedelta
import secrets

class AuthManager:
    """Handle user authentication and session management"""
    
    FIXED_PASSWORD = "ipr123"
    DB_PATH = r"Y:\IPR_App\update\my_pages/trial.db"
    SESSION_TIMEOUT_MINUTES = 90 # 8 hours - adjust as needed
    
    @staticmethod
    def get_connection():
        """Get database connection"""
        return sqlite3.connect(AuthManager.DB_PATH)
    
    
    
    @staticmethod
    def generate_session_token() -> str:
        """Generate a unique session token"""
        return secrets.token_urlsafe(32)
    
    @staticmethod
    def cleanup_expired_sessions():
        """
        Auto-logout sessions that have been inactive for too long
        """
        conn = AuthManager.get_connection()
        try:
            timeout_threshold = datetime.now() - timedelta(minutes=AuthManager.SESSION_TIMEOUT_MINUTES)
            
            conn.execute(
                """UPDATE login_history 
                   SET logout_time = CURRENT_TIMESTAMP 
                   WHERE logout_time IS NULL 
                   AND last_activity < ?""",
                (timeout_threshold.isoformat(),)
            )
            conn.commit()
        finally:
            conn.close()
    
    @staticmethod
    def update_activity(session_token: str):
        """Update last activity time for the session"""
        if not session_token:
            return
        
        conn = AuthManager.get_connection()
        try:
            conn.execute(
                """UPDATE login_history 
                   SET last_activity = CURRENT_TIMESTAMP 
                   WHERE session_token = ? AND logout_time IS NULL""",
                (session_token,)
            )
            conn.commit()
        finally:
            conn.close()
    
    @staticmethod
    def check_if_user_already_logged_in(user_id: int, username: str) -> Tuple[bool, str]:
        """
        Check if user has active session (not expired)
        Returns: (is_already_logged_in: bool, message: str)
        """
        # First cleanup expired sessions
        AuthManager.cleanup_expired_sessions()
        
        conn = AuthManager.get_connection()
        try:
            cursor = conn.execute(
                """SELECT login_id, login_time, last_activity
                   FROM login_history 
                   WHERE user_id = ? AND logout_time IS NULL
                   ORDER BY login_time DESC
                   LIMIT 1""",
                (user_id,)
            )
            result = cursor.fetchone()
            
            if result:
                login_id, login_time, last_activity = result
                
                # Check if session is still active (within timeout)
                last_act = datetime.fromisoformat(last_activity if last_activity else login_time)
                now = datetime.now()
                
                if (now - last_act).total_seconds() < (AuthManager.SESSION_TIMEOUT_MINUTES * 60):
                    # Session is still active
                    try:
                        time_str = last_act.strftime("%I:%M %p on %b %d, %Y")
                    except:
                        time_str = "recently"
                    
                    return True, f"❌ User '{username}' is already logged in (last active: {time_str}). Please wait or logout from the other session."
            
            return False, ""
        finally:
            conn.close()
    
    @staticmethod
    def log_login(user_id: int) -> Tuple[int, str]:
        """
        Log user login with session token
        Returns: (login_id, session_token)
        """
        session_token = AuthManager.generate_session_token()
        
        conn = AuthManager.get_connection()
        try:
            cursor = conn.execute(
                """INSERT INTO login_history (user_id, login_time, last_activity, session_token) 
                   VALUES (?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, ?)""",
                (user_id, session_token)
            )
            conn.commit()
            return cursor.lastrowid, session_token
        finally:
            conn.close()
    
    @staticmethod
    def log_logout(session_token: str):
        """Update logout time for the session"""
        if not session_token:
            return
        
        conn = AuthManager.get_connection()
        try:
            conn.execute(
                """UPDATE login_history 
                   SET logout_time = CURRENT_TIMESTAMP 
                   WHERE session_token = ? AND logout_time IS NULL""",
                (session_token,)
            )
            conn.commit()
        finally:
            conn.close()
    
    @staticmethod
    def verify_user(username: str, password: str) -> Tuple[bool, Optional[int], str]:
        """Verify username and password"""
        if password != AuthManager.FIXED_PASSWORD:
            return False, None, "❌ Incorrect password"
        
        conn = AuthManager.get_connection()
        try:
            cursor = conn.execute(
                "SELECT user_id, user_name FROM users WHERE user_name = ?",
                (username,)
            )
            result = cursor.fetchone()
            
            if result:
                user_id, user_name = result
                
                # Check if user already logged in
                is_logged_in, message = AuthManager.check_if_user_already_logged_in(user_id, user_name)
                
                if is_logged_in:
                    return False, None, message
                
                return True, user_id, f"✅ Welcome back, {user_name}!"
            else:
                return False, None, "❌ Username not found. Please register first."
        finally:
            conn.close()
    
    @staticmethod
    def create_user(username: str, password: str) -> Tuple[bool, Optional[int], str]:
        """Create a new user"""
        if password != AuthManager.FIXED_PASSWORD:
            return False, None, "❌ Incorrect password"
        
        if not username or len(username.strip()) == 0:
            return False, None, "❌ Username cannot be empty"
        
        username = username.strip()
        
        conn = AuthManager.get_connection()
        try:
            cursor = conn.execute(
                "INSERT INTO users (user_name) VALUES (?)",
                (username,)
            )
            conn.commit()
            user_id = cursor.lastrowid
            return True, user_id, f"✅ User '{username}' registered successfully!"
        except sqlite3.IntegrityError:
            return False, None, f"❌ Username '{username}' already exists."
        except Exception as e:
            return False, None, f"❌ Error: {str(e)}"
        finally:
            conn.close()
    
    @staticmethod
    def is_logged_in() -> bool:
        """Check if user is logged in in THIS session"""
        return 'user_id' in state and state.user_id is not None
    
    @staticmethod
    def get_current_user() -> Tuple[Optional[int], Optional[str]]:
        """Get current logged-in user from THIS session"""
        if AuthManager.is_logged_in():
            # Update activity on every page load
            if 'session_token' in state:
                AuthManager.update_activity(state.session_token)
            return state.user_id, state.username
        return None, None
    
    @staticmethod
    def logout():
        """Logout current user"""
        if 'session_token' in state:
            AuthManager.log_logout(state.session_token)
        
        # Clear session state
        for key in ['user_id', 'username', 'authenticated', 'login_id', 'session_token']:
            if key in state:
                del state[key]
        
        st.rerun()