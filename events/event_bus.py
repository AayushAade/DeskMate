import collections

# Global subscriber registry mapping event names to lists of subscriber callbacks
_subscribers = collections.defaultdict(list)

def subscribe(event_type: str, callback):
    """Registers a callback function to trigger when an event of event_type is published."""
    if callback not in _subscribers[event_type]:
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
