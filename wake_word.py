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
GAIN_FACTOR = 8.0          # Software-Verstärkung für das Mikrofon
WAKE_WORD = "jarvis"       # Das zu suchende Wake Word

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
        
    # Signal verstärken und clippen
    audio_float = np.frombuffer(indata, dtype=np.int16).astype(np.float64)
    audio_boosted = audio_float * GAIN_FACTOR
    audio_clipped = np.clip(audio_boosted, -32768, 32767).astype(np.int16)
    q.put(audio_clipped.tobytes())

def calculate_rms(data_bytes):
    audio_data = np.frombuffer(data_bytes, dtype=np.int16).astype(np.float64)
    if len(audio_data) == 0:
        return 0.0
    return float(np.sqrt(np.maximum(0.0, np.mean(audio_data ** 2))))

def listen_for_command(rec):
    """Zustand nach dem Wake Word: Nimmt den Befehl entgegen (max 30 Sek., bricht bei 3 Sek. Stille ab)."""
    print("\n[🎙️ HÖRE ZU] Sprechen Sie jetzt Ihren Befehl... (Max. 30 Sek.)")
    
    frames = []
    silent_chunks = 0
    max_silent_chunks = int(SAMPLE_RATE / BLOCKSIZE * 3)   # 3 Sekunden Stille
    max_total_chunks = int(SAMPLE_RATE / BLOCKSIZE * 30)   # 30 Sekunden max
    total_chunks = 0
    
    # Rec neu initialisieren für den Befehl
    rec.Reset()
    
    while total_chunks < max_total_chunks:
        try:
            data = q.get(timeout=0.5)
        except queue.Empty:
            continue
            
        frames.append(data)
        total_chunks += 1
        
        rms = calculate_rms(data)
        is_silent = rms < 300.0
        
        # Live-Pegel anzeigen
        num_bars = min(30, int(rms / 100))
        sys.stdout.write(f"\r[Pegel: {int(rms):5d}] {'#' * num_bars:<30}")
        sys.stdout.flush()
        
        if is_silent:
            silent_chunks += 1
        else:
            silent_chunks = 0
            
        # Abbruch nach 3 Sekunden Stille (sofern schon was gesagt wurde)
        if silent_chunks >= max_silent_chunks and len(frames) > max_silent_chunks:
            print("\n\n[!] 3 Sekunden Stille erkannt. Aufnahme beendet.")
            break

        rec.AcceptWaveform(data)

    result = json.loads(rec.Result())
    command_text = result.get("text", "").strip()
    return command_text

def main():
    rec = vosk.KaldiRecognizer(model, SAMPLE_RATE)
    print(f"=== WAKE WORD SYSTEM BEREIT ===")
    print(f"Sage das Wake Word: '{WAKE_WORD}'\n")
    
    with sd.RawInputStream(samplerate=SAMPLE_RATE, blocksize=BLOCKSIZE, dtype='int16',
                           channels=1, callback=callback, device=1):
        while True:
            try:
                data = q.get(timeout=0.1)
            except queue.Empty:
                continue
            
            # Prüfen, ob das Wake Word im Datenstrom fällt
            if rec.AcceptWaveform(data):
                result = json.loads(rec.Result())
                text = result.get("text", "").lower()
                
                if WAKE_WORD in text:
                    print(f"\n[🔔 WAKE WORD ERKANNT!] ({WAKE_WORD})")
                    
                    # Befehl aufnehmen
                    command = listen_for_command(rec)
                    
                    print(f"\n==========================================")
                    print(f"[ERFASSTER BEFEHL]: {command if command else '[Kein Text verstanden]'}")
                    print(f"==========================================\n")
                    print(f"Warte wieder auf '{WAKE_WORD}'...\n")
                    
                    # Recognizer für den nächsten Wake-Word-Durchlauf zurücksetzen
                    rec.Reset()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nProgramm beendet.")