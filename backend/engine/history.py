import copy
from typing import List, Dict, Optional, Any
from models.schema import TimelineProject

class HistoryManager:
    def __init__(self, max_depth: int = 50):
        self.max_depth = max_depth
        self.undo_stack: List[Dict[str, Any]] = []
        self.redo_stack: List[Dict[str, Any]] = []
        self.snapshots: Dict[str, Dict[str, Any]] = {}

    def push(self, state: TimelineProject, action: str = "Edit"):
        """Save a new state onto the undo stack."""
        state_dict = state.model_dump()
        self.undo_stack.append({
            "action": action,
            "state": copy.deepcopy(state_dict)
        })
        if len(self.undo_stack) > self.max_depth:
            self.undo_stack.pop(0)
        self.redo_stack.clear()

    def undo(self, current_state: TimelineProject) -> Optional[TimelineProject]:
        """Revert to previous state."""
        if not self.undo_stack:
            return None

        # Push current to redo
        self.redo_stack.append({
            "action": "Current",
            "state": copy.deepcopy(current_state.model_dump())
        })

        prev_entry = self.undo_stack.pop()
        return TimelineProject(**prev_entry["state"])

    def redo(self, current_state: TimelineProject) -> Optional[TimelineProject]:
        """Restore next state from redo stack."""
        if not self.redo_stack:
            return None

        self.undo_stack.append({
            "action": "Undo Point",
            "state": copy.deepcopy(current_state.model_dump())
        })

        next_entry = self.redo_stack.pop()
        return TimelineProject(**next_entry["state"])

    def save_snapshot(self, snapshot_id: str, state: TimelineProject):
        self.snapshots[snapshot_id] = copy.deepcopy(state.model_dump())

    def get_snapshot(self, snapshot_id: str) -> Optional[TimelineProject]:
        if snapshot_id in self.snapshots:
            return TimelineProject(**self.snapshots[snapshot_id])
        return None

    @staticmethod
    def compute_diff(before: TimelineProject, after: TimelineProject) -> Dict[str, Any]:
        """Computes semantic difference between two timeline states for AI validation."""
        before_clips = {c.id: c for c in before.clips}
        after_clips = {c.id: c for c in after.clips}

        added_clips = [c.id for c in after.clips if c.id not in before_clips]
        removed_clips = [c.id for c in before.clips if c.id not in after_clips]

        modified_clips = []
        clip_changes = []
        for cid, c in after_clips.items():
            if cid in before_clips:
                b_clip = before_clips[cid]
                if b_clip.model_dump() != c.model_dump():
                    modified_clips.append(cid)
                    old, new = b_clip.model_dump(), c.model_dump()
                    changed = {
                        key: {"before": old.get(key), "after": new.get(key)}
                        for key in sorted(set(old) | set(new)) if old.get(key) != new.get(key)
                    }
                    clip_changes.append({"clipId": cid, "name": c.name, "changed": changed})

        before_tracks = {track.id: track.model_dump() for track in before.tracks}
        after_tracks = {track.id: track.model_dump() for track in after.tracks}
        before_captions = {caption.id: caption.model_dump() for caption in before.captions}
        after_captions = {caption.id: caption.model_dump() for caption in after.captions}
        before_markers = {marker.id: marker.model_dump() for marker in before.markers}
        after_markers = {marker.id: marker.model_dump() for marker in after.markers}

        removed_intervals = [{"clipId": clip_id, "start": before_clips[clip_id].timelineStart, "end": before_clips[clip_id].timelineEnd, "duration": before_clips[clip_id].timelineEnd - before_clips[clip_id].timelineStart} for clip_id in removed_clips]
        added_intervals = [{"clipId": clip_id, "start": after_clips[clip_id].timelineStart, "end": after_clips[clip_id].timelineEnd, "duration": after_clips[clip_id].timelineEnd - after_clips[clip_id].timelineStart} for clip_id in added_clips]
        return {
            "durationChange": after.duration - before.duration,
            "clipsAdded": added_clips,
            "clipsRemoved": removed_clips,
            "clipsModified": modified_clips,
            "clipChanges": clip_changes,
            "timelineIntervalsRemoved": removed_intervals,
            "timelineIntervalsAdded": added_intervals,
            "summary": {
                "removedTimelineSeconds": round(sum(item["duration"] for item in removed_intervals), 3),
                "addedTimelineSeconds": round(sum(item["duration"] for item in added_intervals), 3),
                "meaning": f"Removed {len(removed_clips)} clip(s), added {len(added_clips)} clip(s), and modified {len(modified_clips)} clip(s).",
            },
            "tracksAdded": sorted(set(after_tracks) - set(before_tracks)),
            "tracksModified": sorted(key for key in set(after_tracks) & set(before_tracks) if after_tracks[key] != before_tracks[key]),
            "captionsAdded": sorted(set(after_captions) - set(before_captions)),
            "captionsRemoved": sorted(set(before_captions) - set(after_captions)),
            "captionsModified": sorted(key for key in set(after_captions) & set(before_captions) if after_captions[key] != before_captions[key]),
            "markersAdded": sorted(set(after_markers) - set(before_markers)),
            "markersRemoved": sorted(set(before_markers) - set(after_markers)),
            "captionsCountBefore": len(before.captions),
            "captionsCountAfter": len(after.captions)
        }
