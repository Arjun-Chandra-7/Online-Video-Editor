from typing import Dict, Any, List
import math
from models.schema import TimelineProject

class IntelligenceEngine:
    @staticmethod
    def analyze_pacing(project: TimelineProject) -> Dict[str, Any]:
        v1_clips = [c for c in project.clips if c.trackId == "trk_v1"]
        total_cuts = max(0, len(v1_clips) - 1)
        duration = project.duration or 10.0

        avg_cut_duration = round(duration / (total_cuts + 1), 2)
        caption_density = round(len(project.captions) / (duration / 10.0), 2)

        # Viral retention algorithm
        pacing_score = max(10, min(100, int(100 - (avg_cut_duration - 2.2) * 15 + caption_density * 4)))

        recommendations = []
        if avg_cut_duration > 3.5:
            recommendations.append("Apply AI Silence Removal or punch-in zooms to increase cut frequency under 3.0s.")
        if len(project.captions) == 0:
            recommendations.append("Generate synchronized kinetic captions for 85%+ retention boost.")
        if not recommendations:
            recommendations.append("Pacing is optimal for high-retention algorithmic short-form feeds.")

        return {
            "viralScore": pacing_score,
            "totalCuts": total_cuts,
            "avgCutDuration": avg_cut_duration,
            "captionDensity": caption_density,
            "recommendations": recommendations,
            "status": "healthy" if pacing_score >= 70 else "needs_optimization"
        }

    @staticmethod
    def generate_viral_hooks(project: TimelineProject) -> List[Dict[str, Any]]:
        return [
            {
                "id": "hook_1",
                "title": "⚡ The 60-Second AI Battle",
                "sub": "BERT vs GPT: The Real Architecture Difference",
                "style": "High-Curiosity Challenge",
                "retentionPotential": "94%",
                "estimatedGain": "+38% View-Through Rate"
            },
            {
                "id": "hook_2",
                "title": "🚨 Stop Confusing BERT and GPT!",
                "sub": "Encoders vs Decoders in Under 60 Seconds",
                "style": "Contrarian / Pattern Interrupt",
                "retentionPotential": "91%",
                "estimatedGain": "+44% Completion Rate"
            },
            {
                "id": "hook_3",
                "title": "🧠 1 Transformer Trick You Never Knew",
                "sub": "Masked LM vs Next-Word Prediction",
                "style": "Insider Knowledge",
                "retentionPotential": "88%",
                "estimatedGain": "+29% Shares"
            }
        ]

    @staticmethod
    def analyze_energy_curve(project: TimelineProject) -> List[Dict[str, Any]]:
        duration = int(project.duration or 60)
        curve = []
        for sec in range(0, duration, 2):
            has_caption = any(c.start <= sec <= c.end for c in project.captions)
            has_cut = any(abs(c.timelineStart - sec) < 1.0 for c in project.clips)

            base_energy = 0.5 + 0.3 * math.sin(sec * 0.4)
            if has_caption: base_energy += 0.25
            if has_cut: base_energy += 0.2

            energy = min(1.0, max(0.15, round(base_energy, 2)))
            risk = "low" if energy > 0.65 else ("medium" if energy > 0.4 else "high")
            curve.append({"time": sec, "energy": energy, "risk": risk})
        return curve
