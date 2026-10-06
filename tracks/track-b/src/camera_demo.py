"""Live Natural Voice & Camera Mentor Demo for Track B.

Connects your live computer camera to Google Gemini (gemini-flash-lite-latest)
with Google Gemini Studio Neural TTS (Aoede voice).
Gemini speaks as a warm, authentic master mentor, offering conversational,
natural coaching advice and celebrating transmission progress out loud!

Usage:
    python tracks/track-b/src/camera_demo.py
    python tracks/track-b/src/camera_demo.py --case kolam
    python tracks/track-b/src/camera_demo.py --list
"""

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
from typing import Any, Dict, List, Optional, Tuple
import wave
import winsound

# Ensure track-b root and repo root are in sys.path
repo_root = Path(__file__).resolve().parents[3]
track_b_dir = Path(__file__).resolve().parents[1]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))
if str(track_b_dir) not in sys.path:
    sys.path.insert(0, str(track_b_dir))

import cv2
from tracks.common.schemas import (
    KnowledgePackage,
    RubricDefinition,
    PracticeTask,
    LearnerAttempt,
    AttemptType,
    ParticipantRef,
    EvidenceRef,
    Modality,
    CriterionStatus,
)
from tracks.common.validator import load_bundle_from_directory
from src.observer import GeminiObserver
from src.evaluator import evaluate_attempt
from src.feedback import generate_coaching_feedback
from src.transmission import compute_transmission_record



# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# Google Gemini Natural Neural Voice Engine (Live Streaming)
# ---------------------------------------------------------------------------

_voice_lock = threading.Lock()

try:
    # pyrefly: ignore [missing-import]
    import sounddevice as sd
    _HAS_SOUNDDEVICE = True
except ImportError:
    _HAS_SOUNDDEVICE = False


def wsola_speedup(pcm_bytes: bytes, speed: float = 1.18, sample_rate: int = 24000) -> bytes:
    """Pitch-preserving time-scale modification using Synchronized Overlap-Add (WSOLA).
    
    Accelerates pure PCM frames cleanly without altering voice pitch or natural timbre.
    Trims exact output length and applies a smooth anti-pop fade-out at the end.
    """
    if speed <= 1.01:
        return pcm_bytes
    try:
        import numpy as np
        samples = np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.float32)
        win_size = int(0.025 * sample_rate)  # 25ms window
        syn_hop = win_size // 2              # 12.5ms synthesis hop
        ana_hop = int(syn_hop * speed)       # analysis hop
        search_range = int(0.008 * sample_rate)  # 8ms correlation search range

        num_syn_frames = (len(samples) - win_size - search_range) // ana_hop
        if num_syn_frames <= 1:
            return pcm_bytes

        out_len = int(len(samples) / speed) + win_size
        output = np.zeros(out_len, dtype=np.float32)
        win = np.hanning(win_size).astype(np.float32)
        weight = np.zeros(out_len, dtype=np.float32)

        last_pos = 0
        syn_pos = 0
        for i in range(num_syn_frames):
            target_ana_pos = int(i * ana_hop)
            search_start = max(0, target_ana_pos - search_range)
            search_end = min(len(samples) - win_size, target_ana_pos + search_range)

            ref_chunk = samples[last_pos:last_pos + win_size]
            best_pos = target_ana_pos
            best_corr = -1e9
            for cand in range(search_start, search_end, 3):
                corr = np.dot(ref_chunk, samples[cand:cand + win_size])
                if corr > best_corr:
                    best_corr = corr
                    best_pos = cand

            output[syn_pos:syn_pos + win_size] += samples[best_pos:best_pos + win_size] * win
            weight[syn_pos:syn_pos + win_size] += win
            last_pos = best_pos + syn_hop
            syn_pos += syn_hop

        actual_end = syn_pos + win_size
        output = output[:actual_end]
        weight = weight[:actual_end]

        mask = weight > 1e-4
        output[mask] /= weight[mask]

        # Apply smooth 12ms cosine fade-out at the end to prevent any clicks/pops
        fade_samples = min(int(0.012 * sample_rate), len(output))
        if fade_samples > 0:
            fade_ramp = np.linspace(1.0, 0.0, fade_samples)
            output[-fade_samples:] *= fade_ramp

        output = np.clip(output, -32768, 32767).astype(np.int16)
        return output.tobytes()
    except Exception:
        return pcm_bytes


def _play_pcm_in_memory(raw_audio_bytes: bytes, speed_factor: float = 1.18) -> None:
    """Extracts pure audio frames, strips trailing metadata, applies WSOLA, and plays cleanly."""
    import io
    import wave

    # 1. Strip container metadata (Gemini WAV returns 44-byte RIFF header + trailing metadata chunks)
    if raw_audio_bytes[:4] == b"RIFF":
        try:
            with wave.open(io.BytesIO(raw_audio_bytes), "rb") as wf:
                channels = wf.getnchannels()
                sample_width = wf.getsampwidth()
                sample_rate = wf.getframerate()
                clean_pcm = wf.readframes(wf.getnframes())
        except Exception:
            clean_pcm, sample_rate, channels, sample_width = raw_audio_bytes, 24000, 1, 2
    else:
        clean_pcm, sample_rate, channels, sample_width = raw_audio_bytes, 24000, 1, 2

    # 2. Apply pitch-preserving acceleration on pure PCM frames
    if speed_factor > 1.01:
        processed_pcm = wsola_speedup(clean_pcm, speed=speed_factor, sample_rate=sample_rate)
    else:
        processed_pcm = clean_pcm

    # 3. Play clean audio without extraneous trailing bytes
    if _HAS_SOUNDDEVICE:
        try:
            with sd.RawOutputStream(samplerate=sample_rate, channels=channels, dtype="int16") as audio_stream:
                audio_stream.write(processed_pcm)
            return
        except Exception:
            pass

    # Windows RAM fallback: build clean WAV container in RAM and play via winsound.SND_MEMORY
    try:
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(channels)
            wf.setsampwidth(sample_width)
            wf.setframerate(sample_rate)
            wf.writeframes(processed_pcm)
        winsound.PlaySound(buf.getvalue(), winsound.SND_MEMORY)
    except Exception:
        pass


TTS_MODELS = [
    "gemini-3.8-flash-lite-tts",
    "gemini-3.8-flash-tts",
    "gemini-2.5-flash-preview-tts",
    "gemini-3.1-flash-tts-preview",
]


class GeminiNaturalVoice:
    """Generates warm, human-like teaching voice using Google Gemini TTS with live accelerated playback."""

    def __init__(self, api_key: Optional[str] = None, voice_name: str = "Kore", speed_factor: float = 1.18):
        from src.observer import _load_env_file
        _load_env_file()
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        self.voice_name = voice_name
        self.speed_factor = speed_factor
        self._client = None
        self._last_thread: Optional[threading.Thread] = None

        if self.api_key:
            try:
                from google import genai
                self._client = genai.Client(api_key=self.api_key)
            except Exception:
                pass

    def stop(self) -> None:
        """Immediately interrupts and purges any currently playing audio."""
        try:
            winsound.PlaySound(None, winsound.SND_PURGE)
        except Exception:
            pass

    def speak(self, text: str, block: bool = False) -> None:
        """Speaks out loud asynchronously with crisp tempo and zero disk I/O."""
        def _worker():
            with _voice_lock:
                if self._client is not None:
                    from google.genai import types
                    cfg = types.GenerateContentConfig(
                        response_modalities=["AUDIO"],
                        speech_config=types.SpeechConfig(
                            voice_config=types.VoiceConfig(
                                prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                    voice_name=self.voice_name
                                )
                            )
                        ),
                    )

                    # Iterate through active Gemini TTS model cascade
                    for model in TTS_MODELS:
                        try:
                            resp = self._client.models.generate_content(
                                model=model,
                                contents=text,
                                config=cfg,
                            )
                            if resp.candidates and resp.candidates[0].content.parts:
                                pcm_data = resp.candidates[0].content.parts[0].inline_data.data
                                _play_pcm_in_memory(pcm_data, sample_rate=24000, speed_factor=self.speed_factor)
                                return
                        except Exception as e:
                            err_str = str(e)
                            if "429" in err_str:
                                continue
                            continue

                # Local fallback if API is unavailable or quota is exceeded
                self._local_fallback_speak(text)

        # Stop previous sound before speaking new sentence
        self.stop()
        t = threading.Thread(target=_worker)
        self._last_thread = t
        t.start()
        if block:
            t.join()

    def wait(self, timeout: float = 6.0) -> None:
        """Waits for current active speech to finish playing."""
        if self._last_thread and self._last_thread.is_alive():
            self._last_thread.join(timeout=timeout)

    def compose_natural_coaching(
        self,
        attempt_number: int,
        total_score: float,
        max_score: float,
        passed: bool,
        eval_findings: List[str],
        top_advice: str,
        skill_name: str = "your craft",
        gain_pts: Optional[int] = None,
    ) -> str:
        """Instant zero-latency spoken dialogue synthesis directly from rubric findings."""
        score_val = int(total_score)
        max_val = int(max_score)
        finding_snippet = eval_findings[0].strip() if eval_findings else ""
        if finding_snippet.endswith("."):
            finding_snippet = finding_snippet[:-1]

        advice_clean = top_advice.split(":", 1)[-1].strip() if ":" in top_advice else top_advice
        if advice_clean.endswith("."):
            advice_clean = advice_clean[:-1]

        if attempt_number == 1:
            if passed:
                return f"Superb start! You passed your baseline attempt with {score_val} points. {finding_snippet}."
            else:
                return f"Good initial try! You scored {score_val} points. For your next attempt: {advice_clean}."
        else:
            if gain_pts is not None and gain_pts > 0:
                if passed:
                    return f"Incredible progress! You gained {gain_pts} points and passed with {score_val} out of {max_val}. {finding_snippet}."
                else:
                    return f"Nice improvement! You gained {gain_pts} points, bringing your score to {score_val}. Now, {advice_clean.lower()}."
            else:
                if passed:
                    return f"Well done! You maintained your passing score of {score_val} points. {finding_snippet}."
                else:
                    return f"Keep practicing! Your score is {score_val} points. Focus on this next: {advice_clean}."

    def _local_fallback_speak(self, text: str) -> None:
        try:
            import win32com.client
            speaker = win32com.client.Dispatch("SAPI.SpVoice")
            speaker.Rate = 2  # Accelerated speaking rate
            speaker.Speak(text)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Track A Run Discovery & Artifact Loader
# ---------------------------------------------------------------------------

def discover_available_cases(runs_dir: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Discovers runnable cases from Track A output runs and fallback fixtures."""
    runs_dir = runs_dir or (repo_root / "tracks" / "track-a" / "data" / "runs")
    cases: List[Dict[str, Any]] = []

    # 1. Scan Track A data runs folder
    if runs_dir.exists():
        for case_dir in sorted(runs_dir.iterdir()):
            if case_dir.is_dir():
                rubric_file = case_dir / "rubric.json"
                task_file = case_dir / "practice_task.json"
                if rubric_file.exists() and task_file.exists():
                    try:
                        r_data = json.loads(rubric_file.read_text(encoding="utf-8"))
                        criteria = r_data.get("criteria", [])
                        max_w = sum(c.get("weight", 0.0) for c in criteria)
                        cases.append({
                            "id": case_dir.name,
                            "source_type": "Track A Output",
                            "dir": case_dir,
                            "is_bundle": False,
                            "title": r_data.get("title", case_dir.name),
                            "criteria_count": len(criteria),
                            "passing_score": r_data.get("passing_score", 0.0),
                            "max_score": r_data.get("max_possible_score", max_w or 100.0),
                        })
                    except Exception:
                        pass

    # 2. Built-in Track B replay fixture fallback if no runs found
    fixture_dir = track_b_dir / "fixtures" / "replay" / "case-001"
    if fixture_dir.exists() and not any(c["id"] == "case-001" for c in cases):
        cases.append({
            "id": "case-001",
            "source_type": "Track B Fixture",
            "dir": fixture_dir,
            "is_bundle": False,
            "title": "Outside Micrometer Reading & Calibration",
            "criteria_count": 3,
            "passing_score": 80.0,
            "max_score": 100.0,
        })

    return cases


def select_case_interactive(available_cases: List[Dict[str, Any]], requested_id: Optional[str] = None) -> Dict[str, Any]:
    """Allows user to select case by CLI flag or via an interactive terminal menu."""
    if not available_cases:
        raise RuntimeError("No runnable cases discovered in Track A runs or fixtures.")

    if requested_id:
        req_clean = requested_id.strip().lower()
        for c in available_cases:
            if c["id"].lower() == req_clean:
                return c
        print(f"⚠️ Requested case ID '{requested_id}' not found. Showing case selection menu...\n")

    print("\n" + "=" * 70)
    print("  🎨 ANVESHAN MULTI-CASE LIVE MENTOR (Track A -> Track B) 🎨")
    print("=" * 70)
    print("Available cases detected from Track A output runs:\n")
    for idx, c in enumerate(available_cases, start=1):
        rel_path = c["dir"].relative_to(repo_root) if c["dir"].is_relative_to(repo_root) else c["dir"]
        print(f"  [{idx}] {c['id']:<18} : {c['title']}")
        print(f"      Score: {c['passing_score']} to pass / {c['max_score']} max ({c['criteria_count']} criteria)")
        print(f"      Path:  {rel_path} [{c['source_type']}]\n")

    print("-" * 70)
    default_case = available_cases[0]
    prompt_str = f"Select case number [1-{len(available_cases)}] or enter case ID [default: 1 ({default_case['id']})]: "

    try:
        user_choice = input(prompt_str).strip()
    except (EOFError, KeyboardInterrupt):
        print("\nUsing default case.")
        return default_case

    if not user_choice:
        print(f"--> Selected: {default_case['id']} ({default_case['title']})\n")
        return default_case

    if user_choice.isdigit():
        val = int(user_choice)
        if 1 <= val <= len(available_cases):
            selected = available_cases[val - 1]
            print(f"--> Selected: {selected['id']} ({selected['title']})\n")
            return selected

    for c in available_cases:
        if c["id"].lower() == user_choice.lower():
            print(f"--> Selected: {c['id']} ({c['title']})\n")
            return c

    print(f"⚠️ Unrecognized choice '{user_choice}'. Defaulting to: {default_case['id']} ({default_case['title']})\n")
    return default_case


def load_case_artifacts(case_entry: Dict[str, Any]) -> Tuple[RubricDefinition, PracticeTask, Optional[KnowledgePackage]]:
    """Loads and validates Pydantic contracts from the chosen case folder."""
    case_dir = case_entry["dir"]
    rubric_file = case_dir / "rubric.json"
    task_file = case_dir / "practice_task.json"
    pkg_file = case_dir / "knowledge_package.json"

    if rubric_file.exists() and task_file.exists():
        rubric = RubricDefinition.model_validate_json(rubric_file.read_text(encoding="utf-8"))
        task = PracticeTask.model_validate_json(task_file.read_text(encoding="utf-8"))
        pkg = KnowledgePackage.model_validate_json(pkg_file.read_text(encoding="utf-8")) if pkg_file.exists() else None
        return rubric, task, pkg

    bundle = load_bundle_from_directory(case_dir)
    rubric = RubricDefinition.model_validate(bundle["rubric"])
    task = PracticeTask.model_validate(bundle["practice_task"])
    pkg = KnowledgePackage.model_validate(bundle["knowledge_package"]) if "knowledge_package" in bundle else None
    return rubric, task, pkg


# ---------------------------------------------------------------------------
# Camera & Evaluation Loop
# ---------------------------------------------------------------------------

def run_camera(
    selected_case_id: Optional[str] = None,
    runs_dir: Optional[Path] = None,
    voice_name: str = "Kore",
    speed_factor: float = 1.18,
):
    available_cases = discover_available_cases(runs_dir=runs_dir)
    case_entry = select_case_interactive(available_cases, requested_id=selected_case_id)
    rubric, task, knowledge_pkg = load_case_artifacts(case_entry)

    observer = GeminiObserver()
    voice = GeminiNaturalVoice(voice_name=voice_name, speed_factor=speed_factor)

    print("=" * 65)
    print("  🎨 ANVESHAN LIVE NATURAL MENTOR (Track B + Gemini Studio TTS) 🎨  ")
    print("=" * 65)
    print(f"[Case ID]     {case_entry['id']}")
    print(f"[Target Skill]{rubric.title}")
    print(f"[Passing]     {rubric.passing_score} / {rubric.max_possible_score} points ({len(rubric.criteria)} criteria)")
    print(f"[Source]      {case_entry['source_type']} ({case_entry['dir'].name})")
    print(f"[AI Observer] Model: {observer.model_name}")
    print(f"[AI Voice]    Studio Voice: Gemini '{voice_name}' (Speed: {speed_factor:.2f}x)")
    print(f"[AI Status]   Live Gemini Mode: {'🟢 ACTIVE' if observer.is_live() else '🟡 OFFLINE SIMULATION'}")
    print("=" * 65)
    print("Commands:")
    print("  [SPACE]  : Capture current frame & receive natural voice coaching")
    print("  [ESC/Q]  : Quit")
    print("=" * 65 + "\n")

    # Natural welcome greeting tailored to the selected skill
    greeting = f"Hello! I am your {rubric.title} mentor. Whenever you are ready with your work, hold it up and press spacebar."
    voice.speak(greeting)

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        cap = cv2.VideoCapture(1)

    if not cap.isOpened():
        print("❌ Could not open webcam (#0 or #1). Reviewing sample lesson...")
        voice.speak("I cannot see a camera, so let us review the sample lesson instead.", block=True)
        sample_path = repo_root / "app" / "public" / "assets" / "learner-attempt.jpg"
        if sample_path.exists():
            eval_res, fb = evaluate_snapshot(
                sample_path, observer, rubric, task, attempt_num=1, knowledge_package=knowledge_pkg
            )
            findings = [r.observed_finding for r in eval_res.criterion_results]
            top_advice = fb.items[0].corrective_advice if fb.items else "Review the lesson criteria."
            spoken_diag = voice.compose_natural_coaching(
                attempt_number=1,
                total_score=eval_res.total_score,
                max_score=rubric.max_possible_score,
                passed=eval_res.passed,
                eval_findings=findings,
                top_advice=top_advice,
                skill_name=rubric.title,
            )
            print(f"\n🗣️ MENTOR SAYS: \"{spoken_diag}\"\n")
            voice.speak(spoken_diag, block=True)
        return

    learner = ParticipantRef(participant_id="live-learner", name="You (Learner)")
    attempt_history = []
    attempt_counter = 1
    evaluating = False
    last_status_banner = "Press SPACEBAR to Evaluate"
    last_color = (0, 255, 0)

    failed_reads = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            failed_reads += 1
            if failed_reads > 30:
                print("⚠️ Camera signal lost.")
                break
            time.sleep(0.03)
            continue
        failed_reads = 0

        h, w = frame.shape[:2]
        display_frame = frame.copy()

        # Alignment guide box
        box_w, box_h = int(w * 0.65), int(h * 0.65)
        x1 = (w - box_w) // 2
        y1 = (h - box_h) // 2
        x2, y2 = x1 + box_w, y1 + box_h
        cv2.rectangle(display_frame, (x1, y1), (x2, y2), (255, 255, 0), 2)
        cv2.putText(
            display_frame,
            f"ALIGN {case_entry['id'].upper()} HERE",
            (x1 + 10, y1 - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (255, 255, 0),
            1,
        )

        # Top banner
        cv2.rectangle(display_frame, (0, 0), (w, 50), (20, 20, 20), -1)
        banner_text = f"Attempt #{attempt_counter} | {last_status_banner}"
        cv2.putText(display_frame, banner_text, (20, 33), cv2.FONT_HERSHEY_SIMPLEX, 0.7, last_color, 2)

        # Bottom banner
        cv2.rectangle(display_frame, (0, h - 35), (w, h), (20, 20, 20), -1)
        cv2.putText(
            display_frame,
            "[SPACE] Capture & Grade with Gemini Voice   |   [Q/ESC] Quit",
            (20, h - 12),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (200, 200, 200),
            1,
        )

        cv2.imshow("Anveshan Natural Voice Mentor", display_frame)
        key = cv2.waitKey(1) & 0xFF

        if key == ord("q") or key == 27:
            voice.stop()
            break
        elif key == 32 and not evaluating:  # SPACEBAR
            voice.stop()
            evaluating = True
            last_status_banner = "Mentor is inspecting your work..."
            last_color = (0, 255, 255)
            print(f"\n📸 Capturing Attempt #{attempt_counter}...")

            temp_img = track_b_dir / "src" / f"temp_attempt_{attempt_counter}.jpg"
            cv2.imwrite(str(temp_img), frame)

            try:
                attempt_type = AttemptType.BASELINE if attempt_counter == 1 else AttemptType.RETRY
                eval_res, fb = evaluate_snapshot(
                    temp_img, observer, rubric, task, attempt_counter, attempt_type, learner, knowledge_pkg
                )
                attempt_history.append((attempt_counter, eval_res))

                score_val = int(eval_res.total_score)
                max_val = int(rubric.max_possible_score)
                findings = [r.observed_finding for r in eval_res.criterion_results]
                top_advice = fb.items[0].corrective_advice if fb.items else "Keep refining your technique."

                gain_pts = None
                if attempt_counter >= 2:
                    base_eval = attempt_history[0][1]
                    gain_pts = int(eval_res.total_score - base_eval.total_score)
                    b_att = LearnerAttempt(
                        attempt_id="att-base-live",
                        task_id=task.task_id,
                        learner=learner,
                        attempt_type=AttemptType.BASELINE,
                        attempt_number=1,
                        evidence=EvidenceRef(
                            evidence_id="ev-base",
                            source_id="live_cam_1.jpg",
                            modality=Modality.IMAGE,
                        ),
                    )
                    r_att = LearnerAttempt(
                        attempt_id=f"att-retry-{attempt_counter}",
                        task_id=task.task_id,
                        learner=learner,
                        attempt_type=AttemptType.RETRY,
                        attempt_number=attempt_counter,
                        evidence=EvidenceRef(
                            evidence_id=f"ev-retry-{attempt_counter}",
                            source_id=f"live_cam_{attempt_counter}.jpg",
                            modality=Modality.IMAGE,
                        ),
                    )
                    trans_record = compute_transmission_record(
                        task=task,
                        rubric=rubric,
                        baseline_attempt=b_att,
                        retry_attempt=r_att,
                        baseline_eval=base_eval,
                        retry_eval=eval_res,
                    )
                    print("\n" + "=" * 65)
                    print(f"🎉 TRANSMISSION RECORD ISSUED!")
                    print(f"   Baseline: {trans_record.baseline_score} -> Retry: {trans_record.retry_score}")
                    print(f"   Net Gain: {'+' if gain_pts >= 0 else ''}{gain_pts} points!")
                    print("=" * 65)

                if eval_res.passed:
                    last_status_banner = f"PASSED! Score: {score_val}/{max_val}"
                    last_color = (0, 255, 0)
                else:
                    last_status_banner = f"NEEDS RETRY (Score: {score_val}/{max_val})"
                    last_color = (0, 0, 255)

                # Compose natural human mentoring dialogue tailored to this skill
                spoken_dialogue = voice.compose_natural_coaching(
                    attempt_number=attempt_counter,
                    total_score=eval_res.total_score,
                    max_score=rubric.max_possible_score,
                    passed=eval_res.passed,
                    eval_findings=findings,
                    top_advice=top_advice,
                    skill_name=rubric.title,
                    gain_pts=gain_pts,
                )

                print(f"\n🗣️ MENTOR SAYS: \"{spoken_dialogue}\"\n")
                voice.speak(spoken_dialogue)
                attempt_counter += 1

                # Flush any stale frames accumulated during evaluation
                for _ in range(5):
                    cap.grab()
            except Exception as e:
                print(f"❌ Error during evaluation: {e}")
                voice.speak("I had a little trouble seeing that clearly. Could you hold it up and try once more?")
            finally:
                evaluating = False

    voice.stop()
    cap.release()
    cv2.destroyAllWindows()
    print("\nCamera session ended.")
    voice.speak("Wonderful practice today. Goodbye!", block=True)


def evaluate_snapshot(
    image_path: Path,
    observer: GeminiObserver,
    rubric: RubricDefinition,
    task: PracticeTask,
    attempt_num: int = 1,
    attempt_type: AttemptType = AttemptType.BASELINE,
    learner: Optional[ParticipantRef] = None,
    knowledge_package: Optional[KnowledgePackage] = None,
):
    print("⏳ Sending image to Gemini Multimodal for inspection...")
    t0 = time.time()

    learner_ref = learner or ParticipantRef(participant_id="live-learner", name="Learner")
    attempt = LearnerAttempt(
        attempt_id=f"att-live-{attempt_num}",
        task_id=task.task_id,
        learner=learner_ref,
        attempt_type=attempt_type,
        attempt_number=attempt_num,
        submitted_at=datetime.now(timezone.utc).isoformat(),
        evidence=EvidenceRef(
            evidence_id=f"ev-live-{attempt_num}",
            source_id=str(image_path.name),
            modality=Modality.IMAGE,
            cue_excerpt="Live camera snapshot",
        ),
    )

    observations = observer.observe(attempt, rubric, media_path=image_path)
    eval_result = evaluate_attempt(attempt, rubric, observations)
    feedback = generate_coaching_feedback(eval_result, rubric, knowledge_package=knowledge_package)
    elapsed = time.time() - t0

    print("\n" + "-" * 65)
    print(f"📊 EVALUATION RESULTS (Evaluated in {elapsed:.2f}s)")
    print(f"   Total Score: {eval_result.total_score} / {rubric.max_possible_score}")
    print(f"   Status:      {'✅ PASSED' if eval_result.passed else '❌ NEEDS RETRY'}")
    print("-" * 65)

    for r in eval_result.criterion_results:
        symbol = "✅" if r.status == CriterionStatus.SATISFIED else ("⚠️" if r.status == CriterionStatus.PARTIALLY_SATISFIED else "❌")
        print(f"  {symbol} {r.criterion_id}: {r.status.value.upper()} | Score: {r.score}")
        print(f"     Observation: {r.observed_finding}")
        if r.deviation_analysis:
            print(f"     Deviation:   {r.deviation_analysis}")

    print("\n💡 ACTIONABLE COACHING FEEDBACK:")
    print(f"   {feedback.summary}")
    for item in feedback.items:
        print(f"   - [{item.criterion_id}]: {item.corrective_advice}")
    print("-" * 65)

    return eval_result, feedback


def main():
    parser = argparse.ArgumentParser(description="Live Natural Voice & Camera Mentor Demo for Track B.")
    parser.add_argument("--case", type=str, default=None, help="Specific case ID to run (e.g. kolam, micrometer, origami)")
    parser.add_argument("--runs-dir", type=Path, default=None, help="Custom Track A runs directory")
    parser.add_argument("--voice", type=str, default="Kore", help="Gemini studio prebuilt voice (Kore, Puck, Aoede, Charon)")
    parser.add_argument("--speed", type=float, default=1.18, help="Speech speed multiplier (default: 1.18)")
    parser.add_argument("--list", action="store_true", help="List available cases discovered in Track A runs and exit")
    args = parser.parse_args()

    if args.list:
        cases = discover_available_cases(runs_dir=args.runs_dir)
        print("\nAvailable Track A & Fixture cases:")
        for idx, c in enumerate(cases, 1):
            print(f"  [{idx}] {c['id']:<18} : {c['title']} ({c['source_type']})")
        return

    run_camera(
        selected_case_id=args.case,
        runs_dir=args.runs_dir,
        voice_name=args.voice,
        speed_factor=args.speed,
    )


if __name__ == "__main__":
    main()

