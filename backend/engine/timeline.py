from typing import Dict, Any, List, Optional
import copy
import uuid
import re
from pathlib import Path
from models.schema import (
    TimelineProject, Track, Clip, CaptionItem, CaptionStyle, ClipTransform,
    ColorGrading, Asset, ClipKeyframe, TimelineMarker
)
from engine.transcriber import AudioTranscriber
from config import ASSETS_DIR

class TimelineHistory:
    def __init__(self, max_history: int = 30):
        self.undo_stack: List[TimelineProject] = []
        self.redo_stack: List[TimelineProject] = []
        self.max_history = max_history

    def push(self, state: TimelineProject, action_name: str = ""):
        self.undo_stack.append(copy.deepcopy(state))
        if len(self.undo_stack) > self.max_history:
            self.undo_stack.pop(0)
        self.redo_stack.clear()

    def undo(self, current_state: TimelineProject) -> Optional[TimelineProject]:
        if not self.undo_stack:
            return None
        self.redo_stack.append(copy.deepcopy(current_state))
        return self.undo_stack.pop()

    def redo(self, current_state: TimelineProject) -> Optional[TimelineProject]:
        if not self.redo_stack:
            return None
        self.undo_stack.append(copy.deepcopy(current_state))
        return self.redo_stack.pop()

class TimelineEngine:
    def __init__(self):
        self.history = TimelineHistory()
        self.state = self._init_clean_project()
        try:
            self.state.captions = self.generate_captions()
        except Exception as e:
            print(f"Initial caption generation error: {e}")

    def _init_clean_project(self) -> TimelineProject:
        tracks = [
            Track(id="trk_v2", type="video", name="V2 Overlays / B-Roll", order=0, muted=False, locked=False, visible=True),
            Track(id="trk_v1", type="video", name="V1 Main Video", order=1, muted=False, locked=False, visible=True),
            Track(id="trk_a1", type="audio", name="A1 Voiceover Dialogue", order=2, muted=False, locked=False, visible=True),
            Track(id="trk_a2", type="audio", name="A2 Music & Ambience", order=3, muted=False, locked=False, visible=True),
        ]

        assets = []
        user_video_files = sorted(
            [f for f in ASSETS_DIR.glob("*.mp4") if not f.name.startswith("preview_")],
            key=lambda x: x.stat().st_mtime,
            reverse=True
        )
        user_audio_files = sorted(
            [f for f in ASSETS_DIR.glob("*.mp3") if not f.name.startswith("preview_")],
            key=lambda x: x.stat().st_mtime,
            reverse=True
        )

        primary_video_url = ""
        primary_video_name = "Imported Video"
        primary_duration = 59.61

        for vf in user_video_files:
            clean_name = re.sub(r'^user_\d+_', '', vf.name).replace('_', ' ')
            dur = AudioTranscriber.get_media_duration(vf)

            if "BERT" in vf.name:
                primary_video_url = f"/api/assets/{vf.name}"
                primary_video_name = clean_name
                primary_duration = dur

            assets.append(Asset(
                id=f"ast_{vf.stem}",
                name=clean_name,
                url=f"/api/assets/{vf.name}",
                type="video",
                duration=dur,
                tags=["user_video"]
            ))

        for af in user_audio_files:
            clean_name = re.sub(r'^user_\d+_', '', af.name).replace('_', ' ')
            assets.append(Asset(
                id=f"ast_{af.stem}",
                name=clean_name,
                url=f"/api/assets/{af.name}",
                type="audio",
                duration=primary_duration,
                tags=["user_audio"]
            ))

        if not primary_video_url and user_video_files:
            primary_video_url = f"/api/assets/{user_video_files[0].name}"
            primary_video_name = re.sub(r'^user_\d+_', '', user_video_files[0].name).replace('_', ' ')
            primary_duration = AudioTranscriber.get_media_duration(user_video_files[0])

        clips = []
        if primary_video_url:
            clips.append(Clip(
                id="clip_main_v1",
                trackId="trk_v1",
                assetId="asset_main",
                assetUrl=primary_video_url,
                name=primary_video_name,
                timelineStart=0.0,
                timelineEnd=primary_duration,
                sourceStart=0.0,
                sourceEnd=primary_duration,
                volume=1.0,
                speed=1.0,
                assetType="video",
                transform=ClipTransform(scale=1.0, posX=0, posY=0, rotation=0, opacity=1.0),
                colorGrading=ColorGrading(exposure=0.0, contrast=1.05, temperature=0.0, tint=0.0, saturation=1.05),
                effects=[]
            ))

        clips.append(Clip(
            id="clip_voice_a1",
            trackId="trk_a1",
            assetId="asset_voiceover",
            assetUrl="/api/assets/voiceover.mp3",
            name="Voiceover Dialogue",
            timelineStart=0.0,
            timelineEnd=primary_duration,
            sourceStart=0.0,
            sourceEnd=primary_duration,
            volume=1.0,
            speed=1.0,
            assetType="audio",
            transform=ClipTransform(),
            colorGrading=ColorGrading(),
            effects=[]
        ))

        markers = [
            TimelineMarker(id="m_hook", time=0.0, label="Viral Hook (0-3s)", color="#EF4444", category="hook"),
            TimelineMarker(id="m_core", time=10.0, label="Core Tension / Concept", color="#3B82F6", category="structure"),
            TimelineMarker(id="m_cta", time=primary_duration - 4.0, label="Payoff / CTA", color="#10B981", category="cta"),
        ]

        return TimelineProject(
            id="proj_clean_reel",
            title="Clean Video Project",
            aspectRatio="9:16",
            canvasWidth=1080,
            canvasHeight=1920,
            frameRate=60,
            audioSampleRate=48000,
            duration=primary_duration,
            playhead=0.0,
            autoDucking=True,
            duckingAmount=0.25,
            tracks=tracks,
            clips=clips,
            captions=[],
            markers=markers,
            assets=assets
        )

    def update_project_settings(
        self,
        title: Optional[str] = None,
        width: Optional[int] = None,
        height: Optional[int] = None,
        frame_rate: Optional[int] = None,
        audio_sample_rate: Optional[int] = None,
    ) -> bool:
        self.history.push(self.state, "Update sequence settings")
        if title is not None and title.strip():
            self.state.title = title.strip()[:120]
        if width is not None:
            self.state.canvasWidth = max(320, min(7680, int(width)))
        if height is not None:
            self.state.canvasHeight = max(320, min(7680, int(height)))
        if frame_rate is not None:
            self.state.frameRate = int(frame_rate) if int(frame_rate) in {23, 24, 25, 30, 50, 60} else 30
        if audio_sample_rate is not None:
            self.state.audioSampleRate = int(audio_sample_rate) if int(audio_sample_rate) in {44100, 48000, 96000} else 48000
        divisor = self.state.canvasHeight or 1
        ratio = self.state.canvasWidth / divisor
        if abs(ratio - 9 / 16) < 0.02:
            self.state.aspectRatio = "9:16"
        elif abs(ratio - 1) < 0.02:
            self.state.aspectRatio = "1:1"
        elif abs(ratio - 4 / 5) < 0.02:
            self.state.aspectRatio = "4:5"
        else:
            self.state.aspectRatio = "16:9"
        return True

    def set_clip_audio(
        self,
        clip_id: str,
        volume: Optional[float] = None,
        pan: Optional[float] = None,
        fade_in: Optional[float] = None,
        fade_out: Optional[float] = None,
        enhance: Optional[float] = None,
    ) -> bool:
        clip = next((c for c in self.state.clips if c.id == clip_id), None)
        if not clip or self._clip_is_locked(clip):
            return False
        self.history.push(self.state, f"Update audio for {clip.name}")
        duration = max(0.0, clip.timelineEnd - clip.timelineStart)
        if volume is not None: clip.volume = round(max(0.0, min(2.0, float(volume))), 2)
        if pan is not None: clip.pan = round(max(-1.0, min(1.0, float(pan))), 2)
        if fade_in is not None: clip.fadeIn = round(max(0.0, min(duration / 2, float(fade_in))), 2)
        if fade_out is not None: clip.fadeOut = round(max(0.0, min(duration / 2, float(fade_out))), 2)
        if enhance is not None: clip.audioEnhance = round(max(0.0, min(1.0, float(enhance))), 2)
        return True

    def set_clip_transition(
        self,
        clip_id: str,
        transition_in: Optional[str] = None,
        transition_out: Optional[str] = None,
        duration: Optional[float] = None,
    ) -> bool:
        clip = next((c for c in self.state.clips if c.id == clip_id), None)
        if not clip or self._clip_is_locked(clip):
            return False
        self.history.push(self.state, f"Update transitions for {clip.name}")
        allowed = {None, "none", "dissolve", "fade", "dip_black", "zoom", "wipe"}
        if transition_in in allowed:
            clip.transitionIn = None if transition_in in {None, "none"} else transition_in
        if transition_out in allowed:
            clip.transitionOut = None if transition_out in {None, "none"} else transition_out
        if duration is not None:
            clip.transitionDuration = round(max(0.1, min(2.0, float(duration))), 2)
        return True

    def fit_timeline_to_duration(self, new_duration: float):
        if new_duration <= 0.5:
            return

        new_duration = round(new_duration, 2)
        self.state.duration = new_duration

        for c in self.state.clips:
            if c.trackId == "trk_a1":
                c.timelineStart = 0.0
                c.timelineEnd = new_duration
                c.sourceEnd = new_duration

        v1_clips = [c for c in self.state.clips if c.trackId == "trk_v1"]
        if v1_clips:
            v1_clips.sort(key=lambda x: x.timelineStart)
            total_old_v1 = sum(c.timelineEnd - c.timelineStart for c in v1_clips) or 1.0

            cur_time = 0.0
            for i, c in enumerate(v1_clips):
                orig_dur = c.timelineEnd - c.timelineStart
                if i == len(v1_clips) - 1:
                    new_dur = round(new_duration - cur_time, 2)
                else:
                    new_dur = round((orig_dur / total_old_v1) * new_duration, 2)

                c.timelineStart = round(cur_time, 2)
                c.timelineEnd = round(cur_time + new_dur, 2)
                c.sourceStart = 0.0
                c.sourceEnd = new_dur
                cur_time += new_dur

        self._recalculate()

    def inspect(self) -> Dict[str, Any]:
        return self.state.model_dump()

    def _clip_is_locked(self, clip: Clip) -> bool:
        track = next((item for item in self.state.tracks if item.id == clip.trackId), None)
        return bool(track and track.locked)

    def _recalculate(self):
        if self.state.clips:
            max_end = max(c.timelineEnd for c in self.state.clips)
            if max_end > self.state.duration:
                self.state.duration = round(max_end, 2)

    def split_clip(self, clip_id: str, split_time: float) -> Optional[Dict[str, Any]]:
        self.history.push(self.state, f"Split clip at {split_time:.2f}s")
        clip = next((c for c in self.state.clips if c.id == clip_id), None)
        if not clip or self._clip_is_locked(clip):
            return None
        if split_time <= clip.timelineStart or split_time >= clip.timelineEnd:
            return None

        first_end = round(split_time, 3)
        second_start = first_end
        dur_first = first_end - clip.timelineStart

        first_clip = clip.model_copy(update={
            "timelineEnd": first_end,
            "sourceEnd": round(clip.sourceStart + dur_first * clip.speed, 3)
        })

        second_clip = clip.model_copy(update={
            "id": f"clip_{uuid.uuid4().hex[:6]}",
            "name": f"{clip.name} (Part 2)",
            "timelineStart": second_start,
            "timelineEnd": clip.timelineEnd,
            "sourceStart": round(clip.sourceStart + dur_first * clip.speed, 3),
            "sourceEnd": clip.sourceEnd
        })

        self.state.clips = [c for c in self.state.clips if c.id != clip_id] + [first_clip, second_clip]
        self._recalculate()
        return {"original": first_clip.model_dump(), "new": second_clip.model_dump()}

    def trim_clip(self, clip_id: str, new_start: Optional[float] = None, new_end: Optional[float] = None) -> bool:
        clip = next((c for c in self.state.clips if c.id == clip_id), None)
        if not clip or self._clip_is_locked(clip):
            return False
        self.history.push(self.state, f"Trim clip {clip_id}")
        if new_start is not None and new_start < clip.timelineEnd:
            diff = (new_start - clip.timelineStart) * clip.speed
            clip.timelineStart = round(new_start, 3)
            clip.sourceStart = round(clip.sourceStart + diff, 3)
        if new_end is not None and new_end > clip.timelineStart:
            diff = (clip.timelineEnd - new_end) * clip.speed
            clip.timelineEnd = round(new_end, 3)
            clip.sourceEnd = round(clip.sourceEnd - diff, 3)
        self._recalculate()
        return True

    def move_clip(self, clip_id: str, new_start: float, new_track_id: Optional[str] = None) -> bool:
        clip = next((c for c in self.state.clips if c.id == clip_id), None)
        if not clip or self._clip_is_locked(clip):
            return False
        self.history.push(self.state, f"Move clip {clip_id}")

        target_track = new_track_id or clip.trackId
        duration = round(clip.timelineEnd - clip.timelineStart, 3)
        desired_start = round(max(0.0, new_start), 3)
        desired_end = round(desired_start + duration, 3)

        clip.timelineStart = desired_start
        clip.timelineEnd = desired_end
        clip.trackId = target_track

        other_clips = [c for c in self.state.clips if c.trackId == target_track and c.id != clip_id]

        if other_clips:
            other_clips.sort(key=lambda x: x.timelineStart)
            for other in other_clips:
                if max(clip.timelineStart, other.timelineStart) < min(clip.timelineEnd, other.timelineEnd):
                    if clip.timelineStart <= other.timelineStart:
                        other_dur = round(other.timelineEnd - other.timelineStart, 3)
                        other.timelineStart = round(clip.timelineEnd, 3)
                        other.timelineEnd = round(other.timelineStart + other_dur, 3)
                    else:
                        other_dur = round(other.timelineEnd - other.timelineStart, 3)
                        other.timelineEnd = round(clip.timelineStart, 3)
                        other.timelineStart = round(max(0.0, other.timelineEnd - other_dur), 3)

            all_track_clips = [c for c in self.state.clips if c.trackId == target_track]
            all_track_clips.sort(key=lambda x: x.timelineStart)
            for i in range(1, len(all_track_clips)):
                prev = all_track_clips[i - 1]
                curr = all_track_clips[i]
                if curr.timelineStart < prev.timelineEnd:
                    curr_dur = round(curr.timelineEnd - curr.timelineStart, 3)
                    curr.timelineStart = round(prev.timelineEnd, 3)
                    curr.timelineEnd = round(curr.timelineStart + curr_dur, 3)

        self._recalculate()
        return True

    def set_clip_speed(self, clip_id: str, speed: float = 1.0, is_reversed: Optional[bool] = None, is_frozen: Optional[bool] = None) -> bool:
        clip = next((c for c in self.state.clips if c.id == clip_id), None)
        if not clip:
            return False
        self.history.push(self.state, f"Set speed {speed}x on {clip_id}")

        old_speed = clip.speed or 1.0
        new_speed = max(0.1, min(10.0, float(speed)))
        source_dur = clip.sourceEnd - clip.sourceStart
        new_timeline_dur = round(source_dur / new_speed, 3)

        clip.speed = new_speed
        clip.timelineEnd = round(clip.timelineStart + new_timeline_dur, 3)
        if is_reversed is not None:
            clip.isReversed = is_reversed
        if is_frozen is not None:
            clip.isFrozen = is_frozen

        self._recalculate()
        return True

    def add_or_update_keyframe(self, clip_id: str, prop: str, value: float, time_pos: float, easing: str = "ease-in-out") -> Optional[ClipKeyframe]:
        clip = next((c for c in self.state.clips if c.id == clip_id), None)
        if not clip:
            return None
        self.history.push(self.state, f"Add {prop} keyframe at {time_pos:.2f}s")

        existing = next((k for k in clip.keyframes if k.property == prop and abs(k.time - time_pos) < 0.05), None)
        if existing:
            existing.value = float(value)
            existing.easing = easing
            return existing

        new_kf = ClipKeyframe(
            id=f"kf_{uuid.uuid4().hex[:6]}",
            time=round(time_pos, 3),
            property=prop,
            value=float(value),
            easing=easing
        )
        clip.keyframes.append(new_kf)
        clip.keyframes.sort(key=lambda x: x.time)
        return new_kf

    def delete_keyframe(self, clip_id: str, keyframe_id: str) -> bool:
        clip = next((c for c in self.state.clips if c.id == clip_id), None)
        if not clip:
            return False
        self.history.push(self.state, f"Delete keyframe {keyframe_id}")
        clip.keyframes = [k for k in clip.keyframes if k.id != keyframe_id]
        return True

    def add_marker(self, time_pos: float, label: str, color: str = "#EF4444", category: str = "hook") -> TimelineMarker:
        self.history.push(self.state, f"Add marker '{label}' at {time_pos:.2f}s")
        marker = TimelineMarker(
            id=f"m_{uuid.uuid4().hex[:6]}",
            time=round(time_pos, 3),
            label=label,
            color=color,
            category=category
        )
        self.state.markers.append(marker)
        self.state.markers.sort(key=lambda x: x.time)
        return marker

    def delete_marker(self, marker_id: str) -> bool:
        self.history.push(self.state, f"Delete marker {marker_id}")
        self.state.markers = [m for m in self.state.markers if m.id != marker_id]
        return True

    def delete_transcript_range(self, start_time: float, end_time: float) -> bool:
        """
        Text-Based Editing (Descript / Premiere Style):
        Deletes audio, video, and captions within [start_time, end_time] and ripple-contracts the entire timeline!
        """
        self.history.push(self.state, f"Transcript Ripple Delete [{start_time:.2f}s - {end_time:.2f}s]")
        dur_to_remove = round(end_time - start_time, 3)
        if dur_to_remove <= 0.05:
            return False

        # Split and remove video clips overlapping this range
        new_clips: List[Clip] = []
        for c in self.state.clips:
            if c.timelineEnd <= start_time:
                new_clips.append(c)
            elif c.timelineStart >= end_time:
                c.timelineStart = round(max(0.0, c.timelineStart - dur_to_remove), 3)
                c.timelineEnd = round(max(0.0, c.timelineEnd - dur_to_remove), 3)
                new_clips.append(c)
            elif c.timelineStart < start_time and c.timelineEnd > end_time:
                # Clip spans across deleted range -> split into two
                first_part = c.model_copy(update={
                    "timelineEnd": start_time,
                    "sourceEnd": round(c.sourceStart + (start_time - c.timelineStart) * c.speed, 3)
                })
                second_part = c.model_copy(update={
                    "id": f"clip_{uuid.uuid4().hex[:6]}",
                    "timelineStart": start_time,
                    "timelineEnd": round(c.timelineEnd - dur_to_remove, 3),
                    "sourceStart": round(c.sourceStart + (end_time - c.timelineStart) * c.speed, 3),
                    "sourceEnd": c.sourceEnd
                })
                new_clips.extend([first_part, second_part])
            elif c.timelineStart < start_time:
                c.timelineEnd = start_time
                c.sourceEnd = round(c.sourceStart + (start_time - c.timelineStart) * c.speed, 3)
                new_clips.append(c)
            elif c.timelineEnd > end_time:
                c.sourceStart = round(c.sourceStart + (end_time - c.timelineStart) * c.speed, 3)
                c.timelineStart = start_time
                c.timelineEnd = round(max(start_time + 0.1, c.timelineEnd - dur_to_remove), 3)
                new_clips.append(c)

        self.state.clips = new_clips

        # Filter & shift captions
        new_captions: List[CaptionItem] = []
        for cap in self.state.captions:
            if cap.end <= start_time:
                new_captions.append(cap)
            elif cap.start >= end_time:
                cap.start = round(max(0.0, cap.start - dur_to_remove), 3)
                cap.end = round(max(0.0, cap.end - dur_to_remove), 3)
                for w in cap.words:
                    w.start = round(max(0.0, w.start - dur_to_remove), 3)
                    w.end = round(max(0.0, w.end - dur_to_remove), 3)
                new_captions.append(cap)

        self.state.captions = new_captions
        self.state.duration = round(max(1.0, self.state.duration - dur_to_remove), 3)
        self._recalculate()
        return True

    def add_clip(
        self,
        track_id: str,
        asset_id: str,
        start_time: float,
        duration: float = 4.0,
        asset_url: Optional[str] = None,
        asset_name: Optional[str] = None,
        asset_type: Optional[str] = None,
        replace_track: bool = False,
    ) -> Optional[Clip]:
        self.history.push(self.state, f"Add clip to {track_id} at {start_time:.2f}s")
        track = next((item for item in self.state.tracks if item.id == track_id), None)
        if not track or track.locked:
            return None

        url = asset_url or f"/api/assets/{asset_id}"
        name = asset_name or "New Clip"
        atype = asset_type or ("video" if "mp4" in url or "mov" in url else "audio")
        if (track.type == "video" and atype == "audio") or (track.type == "audio" and atype != "audio"):
            return None
        if replace_track:
            self.state.clips = [clip for clip in self.state.clips if clip.trackId != track_id]

        new_clip = Clip(
            id=f"clip_{uuid.uuid4().hex[:6]}",
            trackId=track_id,
            assetId=asset_id,
            assetUrl=url,
            name=name,
            timelineStart=round(start_time, 3),
            timelineEnd=round(start_time + duration, 3),
            sourceStart=0.0,
            sourceEnd=round(duration, 3),
            volume=1.0,
            speed=1.0,
            assetType=atype,
            transform=ClipTransform(),
            colorGrading=ColorGrading(),
            effects=[]
        )

        self.state.clips.append(new_clip)
        self._recalculate()
        return new_clip

    def duplicate_clip(self, clip_id: str, create_new_layer: bool = False) -> Optional[Clip]:
        clip = next((c for c in self.state.clips if c.id == clip_id), None)
        if not clip:
            return None

        self.history.push(self.state, f"Duplicate clip {clip.name}")
        target_track = clip.trackId
        start_pos = clip.timelineEnd

        if create_new_layer:
            new_track = self.add_track(clip.assetType or "video", f"Layer {len(self.state.tracks) + 1}")
            target_track = new_track.id
            start_pos = clip.timelineStart

        dur = clip.timelineEnd - clip.timelineStart
        new_clip = clip.model_copy(update={
            "id": f"clip_{uuid.uuid4().hex[:6]}",
            "name": f"{clip.name} (Copy)",
            "trackId": target_track,
            "timelineStart": round(start_pos, 3),
            "timelineEnd": round(start_pos + dur, 3),
        })

        self.state.clips.append(new_clip)
        self._recalculate()
        return new_clip

    def add_track(self, track_type: str = "video", name: Optional[str] = None) -> Track:
        if track_type not in {"video", "audio"}:
            track_type = "video"
        self.history.push(self.state, f"Add {track_type} track")
        track_num = len([t for t in self.state.tracks if t.type == track_type]) + 1
        t_name = name or (f"V{track_num} Video Layer" if track_type == "video" else f"A{track_num} Audio Layer")
        new_track = Track(
            id=f"trk_{uuid.uuid4().hex[:6]}",
            type=track_type,
            name=t_name,
            order=len(self.state.tracks),
            muted=False,
            locked=False,
            visible=True
        )
        self.state.tracks.insert(0 if track_type == "video" else len(self.state.tracks), new_track)
        return new_track

    def ripple_delete(self, clip_id: str) -> bool:
        clip = next((c for c in self.state.clips if c.id == clip_id), None)
        if not clip:
            return False

        self.history.push(self.state, f"Delete clip {clip.name}")
        dur = clip.timelineEnd - clip.timelineStart
        track_id = clip.trackId

        self.state.clips = [c for c in self.state.clips if c.id != clip_id]

        for c in self.state.clips:
            if c.trackId == track_id and c.timelineStart >= clip.timelineEnd:
                c.timelineStart = round(max(0.0, c.timelineStart - dur), 3)
                c.timelineEnd = round(max(0.0, c.timelineEnd - dur), 3)

        self._recalculate()
        return True

    def update_caption(
        self,
        caption_id: str,
        text: Optional[str] = None,
        style_dict: Optional[Dict[str, Any]] = None,
        apply_to_all: bool = False
    ) -> bool:
        self.history.push(self.state, "Update Subtitle Styling")
        if apply_to_all and style_dict:
            for cap in self.state.captions:
                current_style = cap.style.model_dump()
                current_style.update(style_dict)
                cap.style = CaptionStyle(**current_style)
            return True

        cap = next((c for c in self.state.captions if c.id == caption_id), None)
        if not cap:
            cap = self.state.captions[0] if self.state.captions else None
        if not cap:
            return False

        if text is not None:
            cap.text = text
        if style_dict is not None:
            current_style = cap.style.model_dump()
            current_style.update(style_dict)
            cap.style = CaptionStyle(**current_style)

        return True

    def set_track_state(
        self,
        track_id: str,
        muted: Optional[bool] = None,
        locked: Optional[bool] = None,
        visible: Optional[bool] = None
    ) -> bool:
        track = next((t for t in self.state.tracks if t.id == track_id), None)
        if not track:
            return False

        if muted is not None: track.muted = muted
        if locked is not None: track.locked = locked
        if visible is not None: track.visible = visible
        return True

    def apply_effect_to_clip(self, clip_id: str, effect_id: str) -> bool:
        clip = next((c for c in self.state.clips if c.id == clip_id), None)
        if not clip:
            clip = next((c for c in self.state.clips if c.trackId == "trk_v1"), None)
        if not clip:
            return False

        self.history.push(self.state, f"Apply effect '{effect_id}' to {clip.name}")
        if clip.effects is None:
            clip.effects = []

        if effect_id in clip.effects:
            clip.effects.remove(effect_id)
            if effect_id in {"punch_zoom", "super_zoom"}:
                clip.transform.scale = 1.0
            if clip.colorGrading.lut == effect_id:
                clip.colorGrading.lut = None
                clip.colorGrading.exposure = 0.0
                clip.colorGrading.contrast = 1.0
                clip.colorGrading.temperature = 0.0
                clip.colorGrading.saturation = 1.0
            return True
        else:
            clip.effects.append(effect_id)

        # Apply corresponding parameter defaults for visual feedback
        if effect_id == 'punch_zoom':
            clip.transform.scale = 1.22
        elif effect_id == 'super_zoom':
            clip.transform.scale = 1.45
        elif effect_id == 'teal_orange':
            clip.colorGrading.lut = 'teal_orange'
            clip.colorGrading.contrast = 1.2
            clip.colorGrading.saturation = 1.25
        elif effect_id == 'golden_hour':
            clip.colorGrading.lut = 'golden_hour'
            clip.colorGrading.temperature = 0.35
            clip.colorGrading.saturation = 1.15
        elif effect_id == 'cyber_neon':
            clip.colorGrading.lut = 'cyber_neon'
            clip.colorGrading.contrast = 1.25
            clip.colorGrading.saturation = 1.4
        elif effect_id == 'noir_bw':
            clip.colorGrading.lut = 'noir_bw'
            clip.colorGrading.saturation = 0.0
            clip.colorGrading.contrast = 1.3
        elif effect_id == 'sepia_vintage':
            clip.colorGrading.lut = 'sepia_vintage'
            clip.colorGrading.temperature = 0.4
            clip.colorGrading.contrast = 1.1

        return True

    def set_clip_color_grading(
        self,
        clip_id: str,
        exposure: Optional[float] = None,
        contrast: Optional[float] = None,
        temperature: Optional[float] = None,
        tint: Optional[float] = None,
        saturation: Optional[float] = None,
        vignette: Optional[float] = None,
        lut: Optional[str] = None,
        curves: Optional[Any] = None
    ) -> bool:
        clip = next((c for c in self.state.clips if c.id == clip_id), None)
        if not clip:
            clip = next((c for c in self.state.clips if c.trackId == "trk_v1"), None)
        if not clip:
            return False

        if exposure is not None: clip.colorGrading.exposure = round(float(exposure), 2)
        if contrast is not None: clip.colorGrading.contrast = round(float(contrast), 2)
        if temperature is not None: clip.colorGrading.temperature = round(float(temperature), 2)
        if tint is not None: clip.colorGrading.tint = round(float(tint), 2)
        if saturation is not None: clip.colorGrading.saturation = round(float(saturation), 2)
        if vignette is not None: clip.colorGrading.vignette = round(float(vignette), 2)
        if lut is not None: clip.colorGrading.lut = lut
        if curves is not None: clip.colorGrading.curves = curves

        return True

    def set_clip_transform(
        self,
        clip_id: str,
        scale: Optional[float] = None,
        pos_x: Optional[float] = None,
        pos_y: Optional[float] = None,
        rotation: Optional[float] = None,
        opacity: Optional[float] = None,
        flip_h: Optional[bool] = None,
        flip_v: Optional[bool] = None
    ) -> bool:
        clip = next((c for c in self.state.clips if c.id == clip_id), None)
        if not clip:
            clip = next((c for c in self.state.clips if c.trackId == "trk_v1"), None)
        if not clip:
            return False

        if scale is not None: clip.transform.scale = round(float(scale), 2)
        if pos_x is not None: clip.transform.posX = round(float(pos_x), 1)
        if pos_y is not None: clip.transform.posY = round(float(pos_y), 1)
        if rotation is not None: clip.transform.rotation = round(float(rotation), 1)
        if opacity is not None: clip.transform.opacity = round(float(opacity), 2)
        if flip_h is not None: clip.transform.flipH = flip_h
        if flip_v is not None: clip.transform.flipV = flip_v

        return True

    def remove_silences(self, min_duration: float = 0.4) -> Dict[str, Any]:
        self.history.push(self.state, "AI Automatic Silence Removal")
        removed_count = 0
        total_time_saved = 0.0
        ranges = []

        # Find word pauses greater than min_duration from captions
        all_words = []
        for cap in self.state.captions:
            for w in cap.words:
                all_words.append(w)
        all_words.sort(key=lambda x: x.start)

        for idx in range(len(all_words) - 1):
            w_curr = all_words[idx]
            w_next = all_words[idx + 1]
            gap = w_next.start - w_curr.end
            if gap >= min_duration:
                ranges.append([round(w_curr.end, 2), round(w_next.start, 2)])

        for r in reversed(ranges):
            start, end = r[0], r[1]
            if (end - start) >= min_duration:
                if self.delete_transcript_range(start, end):
                    removed_count += 1
                    total_time_saved += (end - start)

        return {
            "intervalsRemoved": removed_count,
            "totalTimeSaved": round(total_time_saved, 2),
            "silenceRanges": ranges
        }

    def add_punch_in_zooms(self, zoom_factor: float = 1.22) -> int:
        self.history.push(self.state, "AI Dynamic Punch-in Zooms")
        v1_clips = [c for c in self.state.clips if c.trackId == "trk_v1"]

        # If there's only 1 large clip, split it into 3-5s segments so zoom pattern interrupts can be applied
        if len(v1_clips) == 1 and v1_clips[0].timelineEnd - v1_clips[0].timelineStart > 6.0:
            target_clip = v1_clips[0]
            split_points = []
            cur = target_clip.timelineStart + 4.0
            while cur < target_clip.timelineEnd - 2.0:
                split_points.append(round(cur, 2))
                cur += 4.5

            for sp in split_points:
                self.split_clip(target_clip.id, sp)
                # re-fetch latest clip matching remainder
                rem_clips = [c for c in self.state.clips if c.trackId == "trk_v1" and c.timelineStart >= sp]
                if rem_clips:
                    target_clip = rem_clips[0]
                else:
                    break

        v1_clips = sorted([c for c in self.state.clips if c.trackId == "trk_v1"], key=lambda x: x.timelineStart)
        applied = 0
        for i, clip in enumerate(v1_clips):
            if i % 2 == 1:
                clip.transform.scale = zoom_factor
                if clip.effects is None: clip.effects = []
                if "punch_zoom" not in clip.effects: clip.effects.append("punch_zoom")
                applied += 1
            else:
                clip.transform.scale = 1.0

        return applied

    def generate_captions(self) -> List[CaptionItem]:
        from engine.auto_caption_ai import AutoCaptionAI
        from engine.transcriber import AudioTranscriber
        from config import ASSETS_DIR

        main_v1_clip = next((c for c in self.state.clips if c.trackId == "trk_v1" and c.assetType == "video"), None)
        if main_v1_clip and main_v1_clip.assetUrl:
            filename = main_v1_clip.assetUrl.split("/")[-1]
            video_path = ASSETS_DIR / filename
            if video_path.exists():
                dur = AudioTranscriber.get_media_duration(video_path)
                trans_result = AudioTranscriber.transcribe_full_audio(video_path, dur)
                if trans_result.get("boundaries"):
                    return AutoCaptionAI.analyze_and_caption_transcript(
                        raw_text=trans_result.get("transcript", ""),
                        total_duration=dur,
                        preset_name="hero_depth_action",
                        speech_boundaries=trans_result.get("boundaries")
                    )

        return AutoCaptionAI.analyze_and_caption_transcript(total_duration=self.state.duration)

    def undo(self) -> bool:
        prev = self.history.undo(self.state)
        if prev:
            self.state = prev
            return True
        return False

    def redo(self) -> bool:
        nxt = self.history.redo(self.state)
        if nxt:
            self.state = nxt
            return True
        return False
