"""语音工具 - 语音识别和语音合成"""
import os
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


def transcribe_audio(
    audio_path: str,
    language: str = "auto"
) -> Dict[str, Any]:
    """Transcribe audio to text using speech recognition.
    
    Args:
        audio_path: Path to audio file (wav, mp3, m4a)
        language: Language code (zh, en, auto)
    
    Returns:
        {
            "success": bool,
            "text": str,
            "language": str,
            "error": str (if failed)
        }
    """
    try:
        path = Path(audio_path)
        if not path.exists():
            return {"success": False, "error": f"Audio file not found: {audio_path}"}
        
        text = None
        detected_lang = language
        
        # Method 1: OpenAI Whisper (best quality)
        try:
            import whisper
            
            model = whisper.load_model("base")
            
            # Auto-detect language if not specified
            if language == "auto":
                # First detect language
                audio = whisper.load_audio(audio_path)
                audio = whisper.pad_or_trim(audio)
                mel = whisper.log_mel_spectrogram(audio).to(model.device)
                _, probs = model.detect_language(mel)
                detected_lang = max(probs, key=probs.get)
            
            result = model.transcribe(audio_path, language=None if language == "auto" else language)
            text = result["text"].strip()
            
        except ImportError:
            logger.info("Whisper not available, trying SpeechRecognition")
        except Exception as e:
            logger.warning(f"Whisper failed: {e}")
        
        # Method 2: SpeechRecognition (Google API, free)
        if not text:
            try:
                import speech_recognition as sr
                
                r = sr.Recognizer()
                
                # Convert to wav if needed
                if path.suffix.lower() != ".wav":
                    audio_path = _convert_to_wav(audio_path)
                
                with sr.AudioFile(audio_path) as source:
                    audio = r.record(source)
                
                lang = "zh-CN" if language in ["zh", "chinese"] else "en-US" if language in ["en", "english"] else None
                
                text = r.recognize_google(audio, language=lang)
                
            except ImportError:
                logger.info("SpeechRecognition not available")
            except Exception as e:
                logger.warning(f"SpeechRecognition failed: {e}")
        
        if text:
            return {
                "success": True,
                "text": text,
                "language": detected_lang,
            }
        
        return {
            "success": False,
            "error": "No speech recognition library available. Install: pip install openai-whisper",
        }
        
    except Exception as e:
        logger.error(f"Transcription failed: {e}")
        return {"success": False, "error": str(e)}


def text_to_speech(
    text: str,
    output_path: str = None,
    language: str = "zh",
    slow: bool = False
) -> Dict[str, Any]:
    """Convert text to speech.
    
    Args:
        text: Text to convert
        output_path: Path to save audio file (default: temp file)
        language: Language code (zh, en)
        slow: Slow down speech
    
    Returns:
        {
            "success": bool,
            "path": str,
            "duration": float (seconds),
            "error": str (if failed)
        }
    """
    try:
        if not text:
            return {"success": False, "error": "Empty text"}
        
        if not output_path:
            output_path = tempfile.mktemp(suffix=".mp3")
        
        # Method 1: gTTS (Google Text-to-Speech)
        try:
            from gtts import gTTS
            
            lang_map = {
                "zh": "zh-CN",
                "en": "en",
                "chinese": "zh-CN",
                "english": "en",
            }
            
            tts = gTTS(text, lang=lang_map.get(language, "zh-CN"), slow=slow)
            tts.save(output_path)
            
            # Estimate duration (gTTS doesn't return it)
            words = len(text.split())
            duration = words * 0.5 if language == "en" else words * 0.8
            
            return {
                "success": True,
                "path": output_path,
                "duration": duration,
            }
            
        except ImportError:
            logger.info("gTTS not available")
        
        # Method 2: pyttsx3 (offline TTS)
        try:
            import pyttsx3
            
            engine = pyttsx3.init()
            
            # Set language
            voices = engine.getProperty('voices')
            for voice in voices:
                if language in voice.languages[0].lower() or \
                   (language == "zh" and "chinese" in voice.name.lower()):
                    engine.setProperty('voice', voice.id)
                    break
            
            if slow:
                engine.setProperty('rate', 100)
            
            engine.save_to_file(text, output_path)
            engine.runAndWait()
            
            return {
                "success": True,
                "path": output_path,
            }
            
        except ImportError:
            logger.info("pyttsx3 not available")
        
        return {
            "success": False,
            "error": "No TTS library available. Install: pip install gtts",
        }
        
    except Exception as e:
        logger.error(f"TTS failed: {e}")
        return {"success": False, "error": str(e)}


def record_audio(
    duration: int = 5,
    output_path: str = None,
    sample_rate: int = 16000
) -> Dict[str, Any]:
    """Record audio from microphone.
    
    Args:
        duration: Recording duration in seconds
        output_path: Path to save audio (default: temp file)
        sample_rate: Audio sample rate
    
    Returns:
        {
            "success": bool,
            "path": str,
            "duration": int,
            "error": str (if failed)
        }
    """
    try:
        if not output_path:
            output_path = tempfile.mktemp(suffix=".wav")
        
        # Try sounddevice
        try:
            import sounddevice as sd
            import soundfile as sf
            
            recording = sd.rec(
                int(duration * sample_rate),
                samplerate=sample_rate,
                channels=1
            )
            sd.wait()
            
            sf.write(output_path, recording, sample_rate)
            
            return {
                "success": True,
                "path": output_path,
                "duration": duration,
            }
            
        except ImportError:
            pass
        
        # Try pyaudio
        try:
            import pyaudio
            import wave
            
            chunk = 1024
            format = pyaudio.paInt16
            channels = 1
            
            p = pyaudio.PyAudio()
            
            stream = p.open(
                format=format,
                channels=channels,
                rate=sample_rate,
                input=True,
                frames_per_buffer=chunk
            )
            
            frames = []
            
            for _ in range(0, int(sample_rate / chunk * duration)):
                data = stream.read(chunk)
                frames.append(data)
            
            stream.stop_stream()
            stream.close()
            p.terminate()
            
            wf = wave.open(output_path, 'wb')
            wf.setnchannels(channels)
            wf.setsampwidth(p.get_sample_size(format))
            wf.setframerate(sample_rate)
            wf.writeframes(b''.join(frames))
            wf.close()
            
            return {
                "success": True,
                "path": output_path,
                "duration": duration,
            }
            
        except ImportError:
            pass
        
        return {
            "success": False,
            "error": "No audio recording library available. Install: pip install sounddevice soundfile",
        }
        
    except Exception as e:
        logger.error(f"Recording failed: {e}")
        return {"success": False, "error": str(e)}


def _convert_to_wav(audio_path: str) -> str:
    """Convert audio file to WAV format."""
    try:
        from pydub import AudioSegment
        
        audio = AudioSegment.from_file(audio_path)
        wav_path = tempfile.mktemp(suffix=".wav")
        audio.export(wav_path, format="wav")
        return wav_path
        
    except ImportError:
        # Try ffmpeg directly
        import subprocess
        
        wav_path = tempfile.mktemp(suffix=".wav")
        subprocess.run([
            "ffmpeg", "-i", audio_path, "-ar", "16000", "-ac", "1", wav_path
        ], capture_output=True)
        return wav_path
