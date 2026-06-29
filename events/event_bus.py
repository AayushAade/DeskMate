import collections
from config.settings import log_debug

# Global subscriber registry mapping event names to lists of subscriber callbacks
_subscribers = collections.defaultdict(list)
_dropped_events_count = 0

def subscribe(event_type: str, callback):
    """Registers a callback function to trigger when an event of event_type is published."""
    global _dropped_events_count
    if callback in _subscribers[event_type]:
        log_debug(
            f"[EventBus] Warning: Callback '{callback.__name__ if hasattr(callback, '__name__') else callback}' "
            f"is already subscribed to event '{event_type}'. Ignoring duplicate registration."
        )
        _dropped_events_count += 1
        return
    _subscribers[event_type].append(callback)

def unsubscribe(event_type: str, callback):
    """Removes a callback function from an event subscription list."""
    if callback in _subscribers[event_type]:
        _subscribers[event_type].remove(callback)

def publish(event_type: str, *args, **kwargs):
    """Fires an event, invoking all registered callbacks with provided arguments."""
    for callback in _subscribers[event_type]:
        try:
            callback(*args, **kwargs)
        except Exception as e:
            print(f"[EventBus] Error executing callback for event {event_type}: {e}")

def get_dropped_events_count() -> int:
    """Returns total count of dropped duplicate subscriptions."""
    return _dropped_events_count
