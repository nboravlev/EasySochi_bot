# session_timeout.py
import logging
from typing import Optional, Dict, Any
from telegram.ext import ContextTypes
from telegram import Update
from telegram.error import TelegramError

# Configuration
TIMEOUT_SECONDS = 90  # 5 minutes - more reasonable default
TIMEOUT_MESSAGE = "⏳ Время ожидания истекло. Сессия сброшена. Начните заново командой /start."
JOB_NAME_PREFIX = "timeout_"

# Set up logging
# Add this at the top of your file
#logging.basicConfig(
#    level=logging.INFO,
#    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
#)



class SessionTimeoutManager:
    """Manages user session timeouts for Telegram bot."""
    
    @staticmethod
    def get_job_name(user_id: int) -> str:
        """Generate consistent job name for user timeout."""
        return f"{JOB_NAME_PREFIX}{user_id}"
    
    @staticmethod
    async def set_timeout(
        context: ContextTypes.DEFAULT_TYPE, 
        user_id: int, 
        timeout_seconds: Optional[int] = None
    ) -> bool:
        """
        Set or reset timeout for a user session.
        
        Args:
            context: Bot context
            user_id: Telegram user ID
            timeout_seconds: Custom timeout duration (uses default if None)
            
        Returns:
            bool: True if timeout was set successfully, False otherwise
        """
        if not context.job_queue:
            logger.error("Job queue is not available")
            return False
            
        job_name = SessionTimeoutManager.get_job_name(user_id)
        timeout_duration = timeout_seconds or TIMEOUT_SECONDS
        
        try:
            # Remove existing timeout jobs for this user
            SessionTimeoutManager._remove_existing_jobs(context, job_name)
            
            # Create new timeout job
            context.job_queue.run_once(
                callback=SessionTimeoutManager._timeout_handler,
                when=timeout_duration,
                name=job_name,
                data={"user_id": user_id},
                user_id=user_id  # This helps with job filtering
            )
            
            logger.debug(f"Timeout set for user {user_id} ({timeout_duration}s)")
            return True
            
        except Exception as e:
            logger.error(f"Failed to set timeout for user {user_id}: {e}")
            return False
    
    @staticmethod
    def _remove_existing_jobs(context: ContextTypes.DEFAULT_TYPE, job_name: str) -> None:
        """Remove existing timeout jobs with the given name."""
        try:
            old_jobs = context.job_queue.get_jobs_by_name(job_name)
            for job in old_jobs:
                job.schedule_removal()
                logger.debug(f"Removed existing job: {job_name}")
        except Exception as e:
            logger.warning(f"Error removing existing jobs for {job_name}: {e}")
    
    @staticmethod
    async def _timeout_handler(context: ContextTypes.DEFAULT_TYPE) -> None:
        current_time = time.time()
        job_created_time = context.job.data.get("created_at", 0)

        if current_time - job_created_time < TIMEOUT_SECONDS - 10:  # 10 sec buffer
            logger.info(f"Ignoring premature timeout for user {user_id}")
            return
        """
        Handle user session timeout.
        
        Args:
            context: Bot context containing job data
        """
        try:
            user_id = context.job.data["user_id"]
            logger.info(f"Session timeout triggered for user {user_id}")
            
            # Send timeout notification
            await SessionTimeoutManager._send_timeout_message(context, user_id)
            
            # Clear user session data
            SessionTimeoutManager._clear_user_data(context, user_id)
            
        except KeyError:
            logger.error("Timeout handler called without user_id in job data")
        except Exception as e:
            logger.error(f"Unexpected error in timeout handler: {e}")
    
    @staticmethod
    async def _send_timeout_message(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> None:
        """Send timeout notification to user."""
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=TIMEOUT_MESSAGE
            )
            logger.debug(f"Timeout message sent to user {user_id}")
            
        except TelegramError as e:
            # Handle specific Telegram errors (user blocked bot, chat not found, etc.)
            logger.warning(f"Failed to send timeout message to user {user_id}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error sending timeout message to user {user_id}: {e}")
    
    @staticmethod
    def _clear_user_data(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> None:
        """Clear user session data."""
        try:
            user_data = context.application.user_data.get(user_id)
            if user_data:
                user_data.clear()
                logger.debug(f"Cleared session data for user {user_id}")
            else:
                logger.debug(f"No session data found for user {user_id}")
                
        except Exception as e:
            logger.error(f"Error clearing user data for user {user_id}: {e}")
    
    @staticmethod
    def cancel_timeout(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> bool:
        """
        Cancel existing timeout for a user.
        
        Args:
            context: Bot context
            user_id: Telegram user ID
            
        Returns:
            bool: True if timeout was cancelled, False if no timeout existed
        """
        job_name = SessionTimeoutManager.get_job_name(user_id)
        
        try:
            jobs = context.job_queue.get_jobs_by_name(job_name)
            if jobs:
                for job in jobs:
                    job.schedule_removal()
                logger.debug(f"Cancelled timeout for user {user_id}")
                return True
            else:
                logger.debug(f"No timeout job found for user {user_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error cancelling timeout for user {user_id}: {e}")
            return False


# Convenience functions for backward compatibility
async def set_timeout(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> bool:
    """Legacy function - use SessionTimeoutManager.set_timeout() instead."""
    return await SessionTimeoutManager.set_timeout(context, user_id)


async def timeout_handler(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Legacy function - use SessionTimeoutManager._timeout_handler() instead."""
    await SessionTimeoutManager._timeout_handler(context)


# Example usage in your bot handlers:
"""
# In your message handler:
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Reset timeout on user activity
    user_id = update.effective_user.id
    await SessionTimeoutManager.set_timeout(context, user_id)
    
    # Your message handling logic here...

# In your start command:
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # Cancel any existing timeout and set new one
    SessionTimeoutManager.cancel_timeout(context, user_id)
    await SessionTimeoutManager.set_timeout(context, user_id)
    
    # Your start command logic here...
"""