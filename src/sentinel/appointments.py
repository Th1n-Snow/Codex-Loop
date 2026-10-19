"""Persistent, one-shot appointment admission; never sends model requests itself."""
from dataclasses import replace
from .schedule import MULTI, multi_schedule_summary, MULTI_GRACE_SECONDS

PREPARE_LEAD = 90
RESET_BUFFER = 60

class BackgroundAppointments:
    def __init__(self, controller, start_action, prepare, busy):
        self.controller = controller
        self.start_action = start_action
        self.prepare = prepare
        self.busy = busy
        self.prepared_keys = set()

    def clear_pending(self):
        s = self.controller.settings
        if s.multi_pending_slot is None:
            return True
        return self.controller._save_settings(replace(s, multi_pending_slot=None,
                     multi_pending_reset=None, multi_pending_due=None, multi_pending_runtime=""))

    def tick(self, now):
        c = self.controller
        s = c.settings
        if s.schedule_mode != MULTI or not s.automation_enabled or s.pause_active(now):
            self.clear_pending()
            return
        if c.persistence_error is not None:
            return
        state = c.states.get('codex')
        if state is None or not state.installed or not state.automation_supported:
            return
        if s.multi_pending_slot is not None:
            # Resume only within the normal admission grace; no wake-up bursts.
            if (s.multi_pending_due is None or s.multi_pending_runtime != state.runtime_identity
                    or now > s.multi_pending_due + MULTI_GRACE_SECONDS):
                if not self.clear_pending(): return
                s = c.settings
            elif (state.quota_state == 'ANCHORED' and state.reset_at is not None
                    and s.multi_pending_reset is not None
                    and state.reset_at > s.multi_pending_reset + 60
                    and state.last_verified_at is not None
                    and state.last_verified_at >= s.multi_pending_slot):
                # Another normal Codex request already started the next window.
                if not self.clear_pending(): return
                s = c.settings
        summary = multi_schedule_summary(now, s.multi_start_times, s.multi_last_slot)
        if summary.due and 'codex' not in self.busy():
            slot = summary.next_action_at
            reset = state.reset_at if state.last_verified_at is not None else None
            due = max(slot, (reset + RESET_BUFFER) if reset is not None else slot)
            # Coalesce appointments waiting for the same window, preserving the first plan time.
            if s.multi_pending_slot is not None:
                candidate = replace(s, multi_last_slot=slot)
            else:
                candidate = replace(s, multi_last_slot=slot, multi_last_status='已接收预热检查',
                            multi_pending_slot=slot, multi_pending_reset=reset,
                            multi_pending_due=due, multi_pending_runtime=state.runtime_identity or '')
            if not c._save_settings(candidate):return
            s = c.settings
        target = s.multi_pending_due if s.multi_pending_slot is not None else summary.next_action_at
        compatible = (s.compatible_runtime_identities or {}).get('codex') == state.runtime_identity
        allowed = compatible and state.status not in {'Checking','Starting','Needs attention'} and state.compatibility_incident_id is None
        if not allowed or 'codex' in self.busy():
            return
        key = (target, state.runtime_identity)
        if target is not None and 0 < target-now <= PREPARE_LEAD and key not in self.prepared_keys:
            self.prepared_keys.add(key)
            if len(self.prepared_keys) > 48:
                self.prepared_keys = {key}
            self.prepare('codex', state.runtime_identity)
        if s.multi_pending_slot is None or now < s.multi_pending_due:
            return
        # Persist consumption BEFORE launching the worker; restart cannot duplicate it.
        slot = s.multi_pending_slot
        if not self.clear_pending():
            return
        mode = 'rollover' if state.last_verified_at is not None else 'bootstrap'
        self.start_action('codex', mode, slot)
