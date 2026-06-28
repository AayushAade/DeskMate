import sqlite3
from datetime import datetime, timedelta
from database import db_manager
from events import event_bus

def add_reminder(task: str, delay_seconds: int) -> int:
    """Saves a reminder to SQLite to fire after delay_seconds."""
    conn = db_manager.get_connection()
    reminder_id = -1
    try:
        due_at = datetime.now() + timedelta(seconds=delay_seconds)
        due_at_str = due_at.strftime('%Y-%m-%d %H:%M:%S')
        
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO reminders (task, due_at, completed) VALUES (?, ?, 0)",
            (task, due_at_str)
        )
        conn.commit()
        reminder_id = cursor.lastrowid
        print(f"[Scheduler] Added reminder ID {reminder_id} due at {due_at_str}: '{task}'")
        
        # Fire event
        event_bus.publish("REMINDER_ADDED", id=reminder_id, task=task, due_at=due_at_str)
    except sqlite3.Error as e:
        print(f"[Scheduler] Error adding reminder: {e}")
    finally:
        conn.close()
    return reminder_id

def check_pending_reminders() -> list:
    """
    Checks for reminders that are past due, marks them completed, 
    and returns them in a list of dicts.
    """
    conn = db_manager.get_connection()
    due_reminders = []
    try:
        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor = conn.cursor()
        
        # Select active, due reminders
        cursor.execute(
            "SELECT id, task FROM reminders WHERE completed = 0 AND due_at <= ?",
            (now_str,)
        )
        rows = cursor.fetchall()
        
        for row in rows:
            r_id = row["id"]
            task = row["task"]
            due_reminders.append({"id": r_id, "task": task})
            
            # Mark as completed
            cursor.execute("UPDATE reminders SET completed = 1 WHERE id = ?", (r_id,))
            
            # Fire event
            event_bus.publish("REMINDER_DUE", id=r_id, task=task)
            print(f"[Scheduler] Reminder due: ID {r_id} - '{task}'")
            
        if rows:
            conn.commit()
    except sqlite3.Error as e:
        print(f"[Scheduler] Error checking reminders: {e}")
    finally:
        conn.close()
    return due_reminders
