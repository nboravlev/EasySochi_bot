# bot/api/log_viewer.py
from fastapi import FastAPI, Request, Depends, HTTPException, Query
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, StreamingResponse
import json
import os
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Dict, Any
import re
from collections import Counter
import gzip

class LogReader:
    def __init__(self, log_dir: str = "/app/logs"):
        self.log_dir = Path(log_dir)
    
    def get_log_files(self) -> List[Dict[str, Any]]:
        """Get list of available log files"""
        log_files = []
        if self.log_dir.exists():
            for file_path in self.log_dir.glob("*.log*"):
                stat = file_path.stat()
                log_files.append({
                    'name': file_path.name,
                    'path': str(file_path),
                    'size': stat.st_size,
                    'modified': datetime.fromtimestamp(stat.st_mtime).isoformat()
                })
        return sorted(log_files, key=lambda x: x['modified'], reverse=True)
    
    def read_structured_logs(
        self,
        limit: int = 100,
        level: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        user_id: Optional[int] = None,
        action: Optional[str] = None,
        search_query: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Read and filter structured logs"""
        logs = []
        structured_log_file = self.log_dir / "bot_structured.log"
        
        if not structured_log_file.exists():
            return logs
        
        try:
            with open(structured_log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if not line.strip():
                        continue
                    
                    try:
                        log_entry = json.loads(line.strip())
                        
                        # Apply filters
                        if level and log_entry.get('level') != level:
                            continue
                        
                        if user_id and log_entry.get('user_id') != user_id:
                            continue
                        
                        if action and action.lower() not in log_entry.get('action', '').lower():
                            continue
                        
                        if search_query:
                            search_text = f"{log_entry.get('message', '')} {log_entry.get('action', '')}".lower()
                            if search_query.lower() not in search_text:
                                continue
                        
                        # Time filtering
                        if start_time or end_time:
                            log_time = datetime.fromisoformat(log_entry['timestamp'].replace('Z', '+00:00'))
                            if start_time and log_time < start_time:
                                continue
                            if end_time and log_time > end_time:
                                continue
                        
                        logs.append(log_entry)
                        
                        if len(logs) >= limit:
                            break
                    
                    except json.JSONDecodeError:
                        continue
        
        except Exception as e:
            print(f"Error reading logs: {e}")
        
        return list(reversed(logs))  # Most recent first
    
    def get_log_stats(self, hours: int = 24) -> Dict[str, Any]:
        """Get logging statistics for the last N hours"""
        start_time = datetime.utcnow() - timedelta(hours=hours)
        logs = self.read_structured_logs(limit=10000, start_time=start_time)
        
        if not logs:
            return {
                'total_logs': 0,
                'level_distribution': {},
                'top_actions': {},
                'error_count': 0,
                'unique_users': 0,
                'avg_execution_time': 0
            }
        
        # Calculate statistics
        level_counts = Counter(log.get('level') for log in logs)
        action_counts = Counter(log.get('action') for log in logs if log.get('action'))
        error_count = sum(1 for log in logs if log.get('level') == 'ERROR')
        unique_users = len(set(log.get('user_id') for log in logs if log.get('user_id')))
        
        # Calculate average execution time
        exec_times = [log.get('execution_time') for log in logs if log.get('execution_time')]
        avg_exec_time = sum(exec_times) / len(exec_times) if exec_times else 0
        
        return {
            'total_logs': len(logs),
            'level_distribution': dict(level_counts),
            'top_actions': dict(action_counts.most_common(10)),
            'error_count': error_count,
            'unique_users': unique_users,
            'avg_execution_time': round(avg_exec_time, 3),
            'timeframe_hours': hours
        }

# FastAPI app setup
app = FastAPI(title="Bot Log Viewer", description="Web interface for viewing bot logs")

# Mount static files and templates
templates = Jinja2Templates(directory="app/templates")
app.mount("/static", StaticFiles(directory="app/static"), name="static")

log_reader = LogReader()

@app.get("/")
async def dashboard(request: Request):
    """Main dashboard page"""
    stats = log_reader.get_log_stats()
    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "stats": stats}
    )

@app.get("/api/logs")
async def get_logs(
    limit: int = Query(100, ge=1, le=1000),
    level: Optional[str] = Query(None),
    hours: Optional[int] = Query(24, ge=1, le=168),
    user_id: Optional[int] = Query(None),
    action: Optional[str] = Query(None),
    search: Optional[str] = Query(None)
):
    """API endpoint to get filtered logs"""
    start_time = datetime.utcnow() - timedelta(hours=hours) if hours else None
    
    logs = log_reader.read_structured_logs(
        limit=limit,
        level=level,
        start_time=start_time,
        user_id=user_id,
        action=action,
        search_query=search
    )
    
    return {
        "logs": logs,
        "total": len(logs),
        "filters": {
            "limit": limit,
            "level": level,
            "hours": hours,
            "user_id": user_id,
            "action": action,
            "search": search
        }
    }

@app.get("/api/stats")
async def get_stats(hours: int = Query(24, ge=1, le=168)):
    """API endpoint to get logging statistics"""
    return log_reader.get_log_stats(hours=hours)

@app.get("/api/files")
async def get_log_files():
    """API endpoint to get list of log files"""
    return {"files": log_reader.get_log_files()}

@app.get("/api/download/{filename}")
async def download_log_file(filename: str):
    """Download a specific log file"""
    file_path = log_reader.log_dir / filename
    
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="Log file not found")
    
    # Security check - only allow log files
    if not filename.endswith(('.log', '.log.1', '.log.2', '.log.3', '.log.4', '.log.5')):
        raise HTTPException(status_code=403, detail="Access denied")
    
    def file_generator():
        with open(file_path, 'rb') as f:
            while True:
                chunk = f.read(8192)
                if not chunk:
                    break
                yield chunk
    
    return StreamingResponse(
        file_generator(),
        media_type='application/octet-stream',
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@app.get("/logs")
async def logs_page(request: Request):
    """Logs viewing page"""
    return templates.TemplateResponse("logs.html", {"request": request})

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "log_dir_exists": log_reader.log_dir.exists(),
        "log_files_count": len(log_reader.get_log_files())
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "log_viewer:app",
        host="0.0.0.0",
        port=8080,
        log_level="info",
        reload=False
    )