"""Read-only quota polling; scheduled warm-ups always take priority."""
from .schedule import MULTI, multi_schedule_summary


class UsageAutoSync:
    def __init__(self, window):
        self.window = window
        self.retry_after = 0.0

    def tick(self, now):
        w = self.window
        c = w.controller
        state = c.states.get('codex')
        if (state is None or not state.installed or not state.runtime_identity or w.active_operations
                or c.persistence_error is not None or state.compatibility_incident_id
                or (c.settings.compatible_runtime_identities or {}).get('codex') != state.runtime_identity
                or now < self.retry_after):
            return
        foreground = w.isVisible() and not w.isMinimized() and w.pages.currentIndex() == 0
        interval = 60 if foreground else 300
        if state.usage_checked_at is not None and now - state.usage_checked_at < interval:
            return
        s = c.settings
        if s.automation_enabled and not s.pause_active(now):
            targets = [s.multi_pending_due, state.reset_at]
            if s.schedule_mode == MULTI:
                targets.append(multi_schedule_summary(now,s.multi_start_times,s.multi_last_slot).next_action_at)
            if any(target is not None and -15 <= target-now <= 180 for target in targets):
                return
        # Throttle failed requests as well as successful ones; never overlap workers.
        self.retry_after = now + interval
        w.start_usage_sync('codex', automatic=True)

    def finished(self, now, *, success):
        self.retry_after = 0 if success else now + 300
