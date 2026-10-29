import queue
import sys
import sounddevice as sd
import vosk
import json
import numpy as np

# Konfiguration
SAMPLE_RATE = 16000
BLOCKSIZE = 8000
MODEL_PATH = "vosk-model-de-0.21"
GAIN_FACTOR = 8.0  # Erhöht auf 8.0 für schwache Laptops

# Lade Vosk-Modell
try:
    print("[*] Lade Vosk-Modell (1.9 GB)... Bitte einen Moment gedulden.")
    model = vosk.Model(MODEL_PATH)
    print("[+] Modell erfolgreich geladen!\n")
except Exception as e:
    print(f"[FEHLER] Konnte Vosk-Modell nicht laden: {e}")
    sys.exit(1)

q = queue.Queue()

def callback(indata, frames, time_info, status):
    if status:
        print(status, file=sys.stderr)
        
    # SICHERS CASTING: Wandle Audio in float64 um, um Überläufe zu vermeiden
    audio_float = np.frombuffer(indata, dtype=np.int16).astype(np.float64)
    
    # Software-Verstärkung anwenden
    audio_boosted = audio_float * GAIN_FACTOR
    
    # Werte sauber auf Int16 begrenzen (-32768 bis 32767)
    audio_clipped = np.clip(audio_boosted, -32768, 32767).astype(np.int16)
    
    q.put(audio_clipped.tobytes())

def calculate_rms(data_bytes):
    """Berechnet sicher den RMS-Pegel ohne Math-Fehler."""
    audio_data = np.frombuffer(data_bytes, dtype=np.int16).astype(np.float64)
    if len(audio_data) == 0:
        return 0.0
    mean_square = np.mean(audio_data ** 2)
    # np.maximum verhindert negative Werte durch Floating-Point-Ungenauigkeiten
    return float(np.sqrt(np.maximum(0.0, mean_square)))

def listen_and_transcribe():
    rec = vosk.KaldiRecognizer(model, SAMPLE_RATE)
    print("[+] Höre zu... Sprechen Sie jetzt!")
    
    frames = []
    silent_chunks = 0
    max_silent_chunks = int(SAMPLE_RATE / BLOCKSIZE * 3)   # 3 Sekunden Stille
    max_total_chunks = int(SAMPLE_RATE / BLOCKSIZE * 30)   # 30 Sekunden max
    total_chunks = 0
    
    with sd.RawInputStream(samplerate=SAMPLE_RATE, blocksize=BLOCKSIZE, dtype='int16',
                           channels=1, callback=callback, device=1):
        while total_chunks < max_total_chunks:
            try:
                data = q.get(timeout=0.5)
            except queue.Empty:
                continue
                
            frames.append(data)
            total_chunks += 1
            
            rms = calculate_rms(data)
            is_silent = rms < 300.0
            
            # Live-Pegel in der Konsole anzeigen
            num_bars = min(30, int(rms / 100))
            bars = "#" * num_bars
            sys.stdout.write(f"\r[Live-Pegel: {int(rms):5d}] {bars:<30}")
            sys.stdout.flush()
            
            if is_silent:
                silent_chunks += 1
            else:
                silent_chunks = 0
                
            # Abbruch nach 3 Sekunden Stille
            if silent_chunks >= max_silent_chunks and len(frames) > max_silent_chunks:
                print("\n\n[!] 3 Sekunden Stille erkannt. Aufnahme beendet.")
                break

            # Live an Vosk füttern
            if rec.AcceptWaveform(data):
                partial = json.loads(rec.Result())
                if partial.get("text"):
                    print(f"\n[Zwischenergebnis]: {partial['text']}")

    # Endgültiges Ergebnis
    result = json.loads(rec.FinalResult())
    text = result.get("text", "")
    return text

if __name__ == "__main__":
    print("=== Vosk Test mit Software-Verstärkung (Gefixt) ===")
    try:
        spoken_text = listen_and_transcribe()
        print(f"\n==========================================")
        print(f"[FINAL ERKANNT]: {spoken_text if spoken_text else '[Kein Text erkannt]'}")
        print(f"==========================================\n")
    except KeyboardInterrupt:
        print("\nAbgebrochen.")