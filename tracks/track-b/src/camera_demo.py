"""Live Natural Voice & Camera Mentor Demo for Track B.

Connects your live computer camera to Google Gemini (gemini-flash-lite-latest)
with Google Gemini Studio Neural TTS (Aoede voice).
Gemini speaks as a warm, authentic master mentor, offering conversational,
natural coaching advice and celebrating transmission progress out loud!

Usage:
    python tracks/track-b/src/camera_demo.py
"""

from datetime import datetime, timezone
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
from typing import Optional, List
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
    import sounddevice as sd
    _HAS_SOUNDDEVICE = True
except ImportError:
    _HAS_SOUNDDEVICE = False


def _play_pcm_in_memory(pcm_bytes: bytes, sample_rate: int = 24000) -> None:
    """Plays raw PCM bytes in-memory using sounddevice or RAM-only WAV buffer (zero disk I/O)."""
    if _HAS_SOUNDDEVICE:
        try:
            with sd.RawOutputStream(samplerate=sample_rate, channels=1, dtype="int16") as audio_stream:
                audio_stream.write(pcm_bytes)
            return
        except Exception:
            pass

    # Windows RAM fallback: build WAV container in RAM and play via winsound.SND_MEMORY
    try:
        import io
        import wave
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)      # Mono
            wf.setsampwidth(2)      # 16-bit PCM = 2 bytes
            wf.setframerate(sample_rate)
            wf.writeframes(pcm_bytes)
        winsound.PlaySound(buf.getvalue(), winsound.SND_MEMORY)
    except Exception:
        pass


TTS_MODELS = [
    "gemini-3.1-flash-tts-preview",
    "gemini-3.8-flash-lite-tts",
    "gemini-3.8-flash-tts",
    "gemini-2.5-flash-preview-tts",
]


class GeminiNaturalVoice:
    """Generates warm, human-like teaching voice using Google Gemini TTS with live audio streaming."""

    def __init__(self, api_key: Optional[str] = None, voice_name: str = "Aoede"):
        from src.observer import _load_env_file
        _load_env_file()
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        self.voice_name = voice_name
        self._client = None
        self._last_thread: Optional[threading.Thread] = None

        if self.api_key:
            try:
                from google import genai
                self._client = genai.Client(api_key=self.api_key)
            except Exception:
                pass

    def speak(self, text: str, block: bool = False) -> None:
        """Live streams speech out loud asynchronously without creating any files on disk."""
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
                            if _HAS_SOUNDDEVICE:
                                stream = self._client.models.generate_content_stream(
                                    model=model,
                                    contents=text,
                                    config=cfg,
                                )
                                pcm_chunks = []
                                with sd.RawOutputStream(samplerate=24000, channels=1, dtype="int16") as audio_out:
                                    for chunk in stream:
                                        if chunk.candidates and chunk.candidates[0].content and chunk.candidates[0].content.parts:
                                            for part in chunk.candidates[0].content.parts:
                                                data = getattr(part.inline_data, "data", None) if getattr(part, "inline_data", None) else None
                                                if data:
                                                    audio_out.write(data)
                                                    pcm_chunks.append(data)
                                if pcm_chunks:
                                    return
                            else:
                                resp = self._client.models.generate_content(
                                    model=model,
                                    contents=text,
                                    config=cfg,
                                )
                                if resp.candidates and resp.candidates[0].content.parts:
                                    pcm_data = resp.candidates[0].content.parts[0].inline_data.data
                                    _play_pcm_in_memory(pcm_data)
                                    return
                        except Exception as e:
                            # 429 quota exhaustion or transient error: try next model in cascade
                            err_str = str(e)
                            if "429" in err_str:
                                continue
                            print(f"⚠️ Voice streaming with {model} failed ({e}), trying next model...")
                            continue

                # Fallback to local SAPI voice if API is unavailable or quota is exceeded
                self._local_fallback_speak(text)

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
        passed: bool,
        eval_findings: List[str],
        top_advice: str,
        gain_pts: Optional[int] = None,
    ) -> str:
        """Ask Gemini to synthesize rubric findings into warm, natural spoken dialogue."""
        if not self._client:
            # Simple template if offline
            if passed:
                return f"Beautiful work! You passed attempt {attempt_number} with {int(total_score)} points. Your loops are smooth and balanced."
            return f"Good try! On attempt {attempt_number}, you scored {int(total_score)} points. {top_advice}"

        try:
            prompt = (
                "You are Meenakshi, a warm, encouraging master artisan teaching your student Kolam art. "
                "You are looking at their practice through the camera. "
                f"Attempt number: {attempt_number}.\n"
                f"Score awarded: {int(total_score)} out of 100 points.\n"
                f"Passed: {passed}.\n"
                f"Observed findings: {'; '.join(eval_findings[:2])}\n"
                f"Core advice: {top_advice}\n"
                + (f"Net improvement from previous attempt: +{gain_pts} points!\n" if gain_pts is not None else "")
                + "\nSpeak directly to the student in 2 short, warm, natural spoken sentences. "
                "Sound conversational, encouraging, and human—like a real mentor in the room with them. "
                "Do NOT use bullet points, jargon, or say 'Criterion C01'. Speak naturally with heart."
            )

            resp = self._client.models.generate_content(
                model="gemini-flash-lite-latest",
                contents=prompt,
            )
            return resp.text.strip().replace('"', '')
        except Exception:
            return f"Good try! On attempt {attempt_number}, you scored {int(total_score)} points. {top_advice}"

    def _local_fallback_speak(self, text: str) -> None:
        try:
            import win32com.client
            speaker = win32com.client.Dispatch("SAPI.SpVoice")
            speaker.Speak(text)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Camera & Evaluation Loop
# ---------------------------------------------------------------------------

def run_camera():
    print("=" * 65)
    print("  🎨 ANVESHAN LIVE NATURAL MENTOR (Track B + Gemini Studio TTS) 🎨  ")
    print("=" * 65)
    print("Commands:")
    print("  [SPACE]  : Capture current frame & receive natural voice coaching")
    print("  [ESC/Q]  : Quit")
    print("=" * 65)

    fixture_dir = track_b_dir / "fixtures" / "replay" / "case-001"
    bundle = load_bundle_from_directory(fixture_dir)
    rubric = RubricDefinition.model_validate(bundle["rubric"])
    task = PracticeTask.model_validate(bundle["practice_task"])

    observer = GeminiObserver()
    voice = GeminiNaturalVoice(voice_name="Aoede")

    print(f"\n[AI Observer] Model: {observer.model_name}")
    print(f"[AI Voice]    Studio Voice: Gemini 'Aoede' (Warm Natural Mentor)")
    print(f"[AI Status]   Live Gemini Mode: {'🟢 ACTIVE' if observer.is_live() else '🟡 OFFLINE SIMULATION'}")
    print(f"[Target Skill]{rubric.title} (Passing Score: {rubric.passing_score} / {rubric.max_possible_score})\n")

    # Natural welcome greeting
    voice.speak("Hello! I am your Kolam mentor. Whenever you are ready with your drawing, hold it up and press spacebar.")

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("❌ Could not open webcam #0.")
        voice.speak("I cannot see a camera, so let us review the sample lesson instead.")
        sample_path = repo_root / "app" / "public" / "assets" / "learner-attempt.jpg"
        evaluate_snapshot(sample_path, observer, rubric, task, attempt_num=1)
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
            "ALIGN DRAWING HERE",
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
            break
        elif key == 32 and not evaluating:  # SPACEBAR
            evaluating = True
            last_status_banner = "Mentor is inspecting your work..."
            last_color = (0, 255, 255)
            print(f"\n📸 Capturing Attempt #{attempt_counter}...")

            temp_img = track_b_dir / "src" / f"temp_attempt_{attempt_counter}.jpg"
            cv2.imwrite(str(temp_img), frame)

            try:
                attempt_type = AttemptType.BASELINE if attempt_counter == 1 else AttemptType.RETRY
                eval_res, fb = evaluate_snapshot(
                    temp_img, observer, rubric, task, attempt_counter, attempt_type, learner
                )
                attempt_history.append((attempt_counter, eval_res))

                score_val = int(eval_res.total_score)
                max_val = int(rubric.max_possible_score)
                findings = [r.observed_finding for r in eval_res.criterion_results]
                top_advice = fb.items[0].corrective_advice if fb.items else "Keep up the smooth lines."

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

                # Compose natural human mentoring dialogue
                spoken_dialogue = voice.compose_natural_coaching(
                    attempt_number=attempt_counter,
                    total_score=eval_res.total_score,
                    passed=eval_res.passed,
                    eval_findings=findings,
                    top_advice=top_advice,
                    gain_pts=gain_pts,
                )

                print(f"\n🗣️ MENTOR MEENAKSHI SAYS: \"{spoken_dialogue}\"\n")
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
    feedback = generate_coaching_feedback(eval_result, rubric)
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


if __name__ == "__main__":
    run_camera()
