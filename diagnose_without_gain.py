import queue
import sys
import sounddevice as sd
import numpy as np

SAMPLE_RATE = 16000
BLOCKSIZE = 2000  # Kleinerer Puffer für schnelle Visualisierung (4x pro Sekunde)

q = queue.Queue()

def callback(indata, frames, time_info, status):
    if status:
        print(status, file=sys.stderr)
    q.put(bytes(indata))

print("=== MIKROFON-TEST & PEGELLIVE-ANZEIGE ===")
print("Sprechen oder klatschen Sie jetzt! Strg+C zum Beenden.\n")

try:
    with sd.RawInputStream(samplerate=SAMPLE_RATE, blocksize=BLOCKSIZE, dtype='int16',
                           channels=1, callback=callback):
        while True:
            data = q.get()
            # Audio-Daten in Zahlen umwandeln und Lautstärke (RMS) berechnen
            audio_data = np.frombuffer(data, dtype=np.int16)
            rms = np.sqrt(np.mean(audio_data**2))
            
            # Pegelbalken für die Konsole bauen
            bars = "#" * int(rms / 50)
            
            # Statusanzeige
            if rms < 100:
                status_text = "[STILLE / MIKRO ZU LEISE]"
            elif rms < 500:
                status_text = "[RAUSCHEN / LEISE SPRACHE]"
            else:
                status_text = "[SPRACHE / LAUT]"
                
            # Schreibt die Zeile live in der Konsole neu
            sys.stdout.write(f"\rPegel: {int(rms):5d} | {bars:<30} {status_text}")
            sys.stdout.flush()

except KeyboardInterrupt:
    print("\n\nTest beendet.")
except Exception as e:
    print(f"\n[FEHLER]: {e}")