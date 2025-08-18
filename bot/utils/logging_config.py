# bot/utils/logging_config.py
import logging
import logging.handlers
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any
import traceback
import asyncio

class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging"""
    
    def format(self, record):
        # Create base log entry
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
            'process_id': os.getpid(),
            'thread_id': record.thread,
        }
        
        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = {
                'type': record.exc_info[0].__name__ if record.exc_info[0] else None,
                'message': str(record.exc_info[1]) if record.exc_info[1] else None,
                'traceback': traceback.format_exception(*record.exc_info)
            }
        
        # Add extra fields if present
        if hasattr(record, 'user_id'):
            log_entry['user_id'] = record.user_id
        if hasattr(record, 'chat_id'):
            log_entry['chat_id'] = record.chat_id
        if hasattr(record, 'message_id'):
            log_entry['message_id'] = record.message_id
        if hasattr(record, 'action'):
            log_entry['action'] = record.action
        if hasattr(record, 'execution_time'):
            log_entry['execution_time'] = record.execution_time
        if hasattr(record, 'request_id'):
            log_entry['request_id'] = record.request_id
            
        return json.dumps(log_entry, ensure_ascii=False)

class TelegramLogFilter(logging.Filter):
    """Filter to add Telegram-specific context to log records"""
    
    def filter(self, record):
        # Add default values if not present
        if not hasattr(record, 'user_id'):
            record.user_id = None
        if not hasattr(record, 'chat_id'):
            record.chat_id = None
        if not hasattr(record, 'action'):
            record.action = 'unknown'
        return True

def setup_logging(
    log_level: str = "INFO",
    log_dir: str = "/app/logs",
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
    enable_console: bool = True,
    enable_file: bool = True
):
    """
    Setup comprehensive logging configuration
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: Directory to store log files
        max_bytes: Maximum size of each log file before rotation
        backup_count: Number of backup files to keep
        enable_console: Whether to enable console logging
        enable_file: Whether to enable file logging
    """
    
    # Create log directory
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Add Telegram filter
    telegram_filter = TelegramLogFilter()
    
    # Console handler with colored output
    if enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)-20s | %(funcName)-15s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
        console_handler.addFilter(telegram_filter)
        root_logger.addHandler(console_handler)
    
    if enable_file:
        # JSON file handler for structured logs
        json_handler = logging.handlers.RotatingFileHandler(
            filename=os.path.join(log_dir, 'bot_structured.log'),
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        json_handler.setFormatter(JSONFormatter())
        json_handler.addFilter(telegram_filter)
        root_logger.addHandler(json_handler)
        
        # Separate error log
        error_handler = logging.handlers.RotatingFileHandler(
            filename=os.path.join(log_dir, 'bot_errors.log'),
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)s | %(name)s | %(funcName)s:%(lineno)d | %(message)s\n%(exc_text)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        error_handler.setFormatter(error_formatter)
        root_logger.addHandler(error_handler)
        
        # Performance log for tracking execution times
        perf_handler = logging.handlers.RotatingFileHandler(
            filename=os.path.join(log_dir, 'bot_performance.log'),
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        perf_handler.addFilter(lambda record: hasattr(record, 'execution_time'))
        perf_handler.setFormatter(JSONFormatter())
        root_logger.addHandler(perf_handler)
    
    # Configure specific loggers
    loggers_config = {
        'telegram': logging.WARNING,  # Reduce telegram library noise
        'httpx': logging.WARNING,     # Reduce HTTP client noise
        'urllib3': logging.WARNING,   # Reduce urllib3 noise
        'asyncio': logging.WARNING,   # Reduce asyncio noise
    }
    
    for logger_name, level in loggers_config.items():
        logger = logging.getLogger(logger_name)
        logger.setLevel(level)
    
    logging.info("Logging system initialized", extra={'action': 'logging_init'})

# Context manager for logging function execution time
class LogExecutionTime:
    def __init__(self, action: str, logger: logging.Logger = None, user_id: int = None, chat_id: int = None):
        self.action = action
        self.logger = logger or logging.getLogger(__name__)
        self.user_id = user_id
        self.chat_id = chat_id
        self.start_time = None
    
    def __enter__(self):
        self.start_time = datetime.utcnow()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        end_time = datetime.utcnow()
        execution_time = (end_time - self.start_time).total_seconds()
        
        extra = {
            'action': self.action,
            'execution_time': execution_time,
            'user_id': self.user_id,
            'chat_id': self.chat_id
        }
        
        if exc_type:
            self.logger.error(
                f"Action '{self.action}' failed after {execution_time:.3f}s",
                exc_info=(exc_type, exc_val, exc_tb),
                extra=extra
            )
        else:
            self.logger.info(
                f"Action '{self.action}' completed in {execution_time:.3f}s",
                extra=extra
            )

# Decorator for automatic function logging
def log_function_call(action: str = None, log_args: bool = False):
    """Decorator to automatically log function calls with execution time"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            func_action = action or f"{func.__module__}.{func.__name__}"
            logger = logging.getLogger(func.__module__)
            
            # Extract Telegram context if available
            user_id = kwargs.get('user_id')
            chat_id = kwargs.get('chat_id')
            
            # Try to extract from Update object if present
            if args and hasattr(args[0], 'effective_user'):
                user_id = args[0].effective_user.id if args[0].effective_user else None
                chat_id = args[0].effective_chat.id if args[0].effective_chat else None
            
            extra = {
                'action': func_action,
                'user_id': user_id,
                'chat_id': chat_id
            }
            
            if log_args:
                extra['function_args'] = str(args)
                extra['function_kwargs'] = str(kwargs)
            
            with LogExecutionTime(func_action, logger, user_id, chat_id):
                logger.info(f"Starting {func_action}", extra=extra)
                try:
                    result = func(*args, **kwargs)
                    logger.debug(f"Completed {func_action}", extra=extra)
                    return result
                except Exception as e:
                    logger.error(f"Error in {func_action}: {str(e)}", extra=extra, exc_info=True)
                    raise
        
        # Handle async functions
        if asyncio.iscoroutinefunction(func):
            async def async_wrapper(*args, **kwargs):
                func_action = action or f"{func.__module__}.{func.__name__}"
                logger = logging.getLogger(func.__module__)
                
                # Extract Telegram context if available
                user_id = kwargs.get('user_id')
                chat_id = kwargs.get('chat_id')
                
                # Try to extract from Update object if present
                if args and hasattr(args[0], 'effective_user'):
                    user_id = args[0].effective_user.id if args[0].effective_user else None
                    chat_id = args[0].effective_chat.id if args[0].effective_chat else None
                
                extra = {
                    'action': func_action,
                    'user_id': user_id,
                    'chat_id': chat_id
                }
                
                if log_args:
                    extra['function_args'] = str(args)
                    extra['function_kwargs'] = str(kwargs)
                
                with LogExecutionTime(func_action, logger, user_id, chat_id):
                    logger.info(f"Starting {func_action}", extra=extra)
                    try:
                        result = await func(*args, **kwargs)
                        logger.debug(f"Completed {func_action}", extra=extra)
                        return result
                    except Exception as e:
                        logger.error(f"Error in {func_action}: {str(e)}", extra=extra, exc_info=True)
                        raise
            
            return async_wrapper
        
        return wrapper
    return decorator

# Helper function to create logger with extra context
def get_logger(name: str, user_id: int = None, chat_id: int = None, request_id: str = None):
    """Get logger with pre-configured extra context"""
    logger = logging.getLogger(name)
    
    class ContextAdapter(logging.LoggerAdapter):
        def process(self, msg, kwargs):
            extra = kwargs.get('extra', {})
            extra.update({
                'user_id': user_id,
                'chat_id': chat_id,
                'request_id': request_id
            })
            kwargs['extra'] = extra
            return msg, kwargs
    
    return ContextAdapter(logger, {})