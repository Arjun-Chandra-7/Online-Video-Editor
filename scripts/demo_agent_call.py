#!/usr/bin/env python3
"""
Viralist Video Editor — Sub-Agent Call Demonstration
Shows how a Channel Agent interacts with the Video Editor via API / MCP tools.
"""
import requests
import json
import time

BASE_URL = "http://localhost:8080/api"

def run_agent_workflow():
    print("🤖 Channel Agent initiating Video Editor Sub-Agent workflow...\n")

    # 1. Check System & Hardware Status
    status = requests.get(f"{BASE_URL}/status").json()
    print(f"✅ Sub-Agent Online. Hardware: {status['hardware']['type']}")
    print(f"📁 Active Project: {status['activeProject']} (Duration: {status['duration']}s)\n")

    # 2. Inspect Timeline State
    timeline = requests.get(f"{BASE_URL}/timeline").json()
    print(f"📊 Timeline Inspection: {len(timeline['tracks'])} Tracks, {len(timeline['clips'])} Clips, {len(timeline['captions'])} Captions.\n")

    # 3. Perform AI Silence Removal (Dead air cut)
    print("⚡ [Agent Action] Calling AI Silence Removal...")
    silence_res = requests.post(f"{BASE_URL}/ai/remove_silence", json={"minDuration": 0.4}).json()
    print(f"   -> Result: {silence_res['summary']['totalTimeSaved']}s saved across {len(silence_res['summary']['silenceRanges'])} pause intervals.\n")
    time.sleep(1)

    # 4. Perform AI Punch-in Zooms for Retention Pattern Interrupts
    print("⚡ [Agent Action] Calling AI Punch-in Zooms...")
    zoom_res = requests.post(f"{BASE_URL}/ai/punch_in_zoom", json={"zoomFactor": 1.22}).json()
    print(f"   -> Result: Applied dynamic zoom transforms to {zoom_res['appliedCount']} clips.\n")
    time.sleep(1)

    # 5. Generate Dynamic Word-by-Word Captions
    print("⚡ [Agent Action] Calling AI Dynamic Reel Captions...")
    cap_res = requests.post(f"{BASE_URL}/ai/generate_captions").json()
    print(f"   -> Result: Generated {len(cap_res['captions'])} styled caption lines.\n")
    time.sleep(1)

    # 6. Audit Viral Pacing & Retention Score
    print("🔍 [Agent Action] Requesting Auditor Pacing Analysis...")
    audit_res = requests.get(f"{BASE_URL}/ai/pacing_analysis").json()
    print(f"   -> Viral Retention Score: {audit_res['retentionScore']}/100")
    print(f"   -> Avg Cut Duration: {audit_res['avgCutDurationSeconds']}s (Total Cuts: {audit_res['totalCuts']})")
    print(f"   -> Recommendation: {audit_res['recommendation']}\n")

    # 7. Render / Export Project
    print("🎬 [Agent Action] Triggering Final Hardware-Accelerated 9:16 Render...")
    export_res = requests.post(f"{BASE_URL}/export", json={"filename": "agent_auto_reel_01.mp4"}).json()
    print(f"   -> Render Output: {export_res['outputPath']} ({export_res['status']})")
    print(f"   -> Encoder Used: {export_res['encoder']}\n")

    print("🎉 Workflow complete! View live result in browser at http://localhost:8080")

if __name__ == "__main__":
    try:
        run_agent_workflow()
    except Exception as e:
        print(f"❌ Error connecting to Viralist Server (Make sure backend is running on http://localhost:8080): {e}")
