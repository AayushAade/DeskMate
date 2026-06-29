import sqlite3
from datetime import datetime, timedelta
from database import db_manager
from events import event_bus
from config.settings import log_info, log_error

def initialize():
    """Initializes the scheduler, counting and logging active pending reminders."""
    conn = db_manager.get_connection()
    count = 0
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM reminders WHERE status = 'pending'")
        count = cursor.fetchone()["count"]
        log_info(f"Scheduler initialized. Loaded {count} pending reminders.")
    except sqlite3.Error as e:
        log_error(f"Error initializing scheduler: {e}")
    finally:
        conn.close()
    return count

def add_reminder(task: str, delay_seconds: int) -> int:
    """Saves a reminder to SQLite with 'pending' status to fire after delay_seconds."""
    conn = db_manager.get_connection()
    reminder_id = -1
    try:
        due_at = datetime.now() + timedelta(seconds=delay_seconds)
        due_at_str = due_at.strftime('%Y-%m-%d %H:%M:%S')
        
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO reminders (task, due_at, status) VALUES (?, ?, 'pending')",
            (task, due_at_str)
        )
        conn.commit()
        reminder_id = cursor.lastrowid
        log_info(f"Added reminder ID {reminder_id} due at {due_at_str}: '{task}'")
        
        # Fire event
        event_bus.publish("REMINDER_ADDED", id=reminder_id, task=task, due_at=due_at_str)
    except sqlite3.Error as e:
        log_error(f"Error adding reminder: {e}")
    finally:
        conn.close()
    return reminder_id

def check_pending_reminders() -> list:
    """
    Checks for reminders that are past due, marks them completed inside SQLite 
    *before* dispatching notifications to avoid duplicate triggers.
    """
    conn = db_manager.get_connection()
    due_reminders = []
    try:
        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor = conn.cursor()
        
        # Select active, due reminders
        cursor.execute(
            "SELECT id, task FROM reminders WHERE status = 'pending' AND due_at <= ?",
            (now_str,)
        )
        rows = cursor.fetchall()
        
        for row in rows:
            r_id = row["id"]
            task = row["task"]
            due_reminders.append({"id": r_id, "task": task})
            
            # Immediately mark as completed to prevent duplicate evaluations
            cursor.execute("UPDATE reminders SET status = 'completed' WHERE id = ?", (r_id,))
            
        # Commit status transitions first
        if rows:
            conn.commit()
            
            # Now trigger the alerts
            for r in due_reminders:
                event_bus.publish("REMINDER_DUE", id=r["id"], task=r["task"])
                log_info(f"Reminder due: ID {r['id']} - '{r['task']}'")
                
    except sqlite3.Error as e:
        log_error(f"Error checking reminders: {e}")
    finally:
        conn.close()
    return due_reminders

# Run scheduler initialization on import
initialize()
