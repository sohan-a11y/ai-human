"""Maps agent state names to (emotion_key, display_label) tuples."""


def state_to_emotion(state_name: str) -> tuple[str, str]:
    mapping = {
        "IDLE":       ("idle",       "Idle        (•‿•)"),
        "PERCEIVING": ("perceiving", "Looking...  (👁 ‿ 👁)"),
        "THINKING":   ("thinking",   "Thinking    (•_•) ..."),
        "ACTING":     ("acting",     "Working     (⌐■_■)"),
        "LEARNING":   ("thinking",   "Learning    (•_•)"),
        "STOPPED":    ("idle",       "Stopped     (-_-)"),
    }
    return mapping.get(state_name, ("idle", state_name))
