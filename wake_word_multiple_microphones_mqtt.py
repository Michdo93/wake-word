import queue
import sys
import threading
import sounddevice as sd
import vosk
import json
import numpy as np
import paho.mqtt.client as mqtt

# ================= CONFIGURATION =================
SAMPLE_RATE = 16000
BLOCKSIZE = 8000
MODEL_PATH = "vosk-model-de-0.21"
WAKE_WORD = "jarvis"

# MQTT Konfiguration
MQTT_BROKER = "localhost"  # IP oder Hostname Ihres MQTT-Brokers
MQTT_PORT = 1883
MQTT_TOPIC = "smarthome/voice/command"

# Individuelle Software-Verstärkung (Gain) je nach Mikrofon-Typ (z.B. Fame Audio BM91U)
# Greift per Teilstring-Matching auf den Gerätenamen zu. Fallback ist 'default'.
MIC_GAIN_CONFIG = {
    "Fame Audio BM91U": 4.0,   # Grenzflächenmikrofon (bereits sehr raumempfindlich)
    "default": 8.0             # Standard-Verstärkung für leisere No-Name Pucks
}
# ==================================================

# MQTT Client initialisieren
mqtt_client = mqtt.Client()
try:
    mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
    mqtt_client.loop_start()
    print( erfolgreich mit MQTT-Broker verbunden.")
except Exception as e:
    print(f"[!] Warnung: Konnte nicht mit MQTT-Broker verbinden: {e}")

# Lade zentrales Vosk-Modell
try:
    print("[*] Lade zentrales Vosk-Modell...")
    model = vosk.Model(MODEL_PATH)
    print("[+] Modell erfolgreich geladen!\n")
except Exception as e:
    print(f"[FEHLER] Konnte Vosk-Modell nicht laden: {e}")
    sys.exit(1)

session_lock = threading.Lock()
active_session = False

def get_gain_for_mic(mic_name):
    """Ermittelt den passenden Gain-Faktor anhand des Mikrofonnamens."""
    for key, gain in MIC_GAIN_CONFIG.items():
        if key.lower() in mic_name.lower():
            return gain
    return MIC_GAIN_CONFIG["default"]

def calculate_rms(data_bytes):
    audio_data = np.frombuffer(data_bytes, dtype=np.int16).astype(np.float64)
    if len(audio_data) == 0:
        return 0.0
    return float(np.sqrt(np.maximum(0.0, np.mean(audio_data ** 2))))

def get_usb_microphones():
    devices = sd.query_devices()
    mic_indices = []
    for i, dev in enumerate(devices):
        if dev['max_input_channels'] > 0:
            mic_indices.append((i, dev['name']))
            print(f"[*] Gefundenes Mikrofon [ID {i}]: {dev['name']}")
    return mic_indices

def handle_active_command(stream_q, mic_name, rec):
    global active_session
    print(f"\n[🎙️ HÖRE ZU über {mic_name}] Sprechen Sie Ihren Befehl... (Max. 30 Sek.)")
    
    frames = []
    silent_chunks = 0
    max_silent_chunks = int(SAMPLE_RATE / BLOCKSIZE * 3)   # 3 Sek. Stille
    max_total_chunks = int(SAMPLE_RATE / BLOCKSIZE * 30)   # 30 Sek. Max
    total_chunks = 0
    
    rec.Reset()
    
    while total_chunks < max_total_chunks:
        try:
            data = stream_q.get(timeout=0.5)
        except queue.Empty:
            continue
            
        frames.append(data)
        total_chunks += 1
        
        rms = calculate_rms(data)
        if (rms < 300.0):
            silent_chunks += 1
        else:
            silent_chunks = 0
            
        if silent_chunks >= max_silent_chunks and len(frames) > max_silent_chunks:
            print(f"\n[!] 3 Sekunden Stille auf {mic_name} erkannt. Aufnahme beendet.")
            break

        rec.AcceptWaveform(data)

    result = json.loads(rec.Result())
    command_text = result.get("text", "").strip()
    
    print(f"\n==========================================")
    print(f"[BEFEHL von {mic_name}]: {command_text if command_text else '[Kein Text verstanden]'}")
    print(f"==========================================\n")
    
    # Per MQTT publishen, falls Text vorhanden
    if command_text:
        payload = json.dumps({"microphone": mic_name, "command": command_text})
        mqtt_client.publish(MQTT_TOPIC, payload)
        print(f"[MQTT] Gesendet an Topic '{MQTT_TOPIC}': {payload}")
    
    with session_lock:
        active_session = False
    print(f"[*] System wieder im Standby. Warte auf '{WAKE_WORD}'...\n")

def monitor_microphone(mic_id, mic_name):
    global active_session
    q = queue.Queue()
    gain = get_gain_for_mic(mic_name)
    print(f"[*] Mikrofon '{mic_name}' nutzt Gain-Faktor: {gain}")

    def callback(indata, frames, time_info, status):
        audio_float = np.frombuffer(indata, dtype=np.int16).astype(np.float64)
        audio_boosted = audio_float * gain
        audio_clipped = np.clip(audio_boosted, -32768, 32767).astype(np.int16)
        q.put(audio_clipped.tobytes())

    rec = vosk.KaldiRecognizer(model, SAMPLE_RATE)

    try:
        with sd.RawInputStream(samplerate=SAMPLE_RATE, blocksize=BLOCKSIZE, dtype='int16',
                               channels=1, callback=callback, device=mic_id):
            while True:
                try:
                    data = q.get(timeout=0.1)
                except queue.Empty:
                    continue
                
                if active_session:
                    continue

                if rec.AcceptWaveform(data):
                    result = json.loads(rec.Result())
                    text = result.get("text", "").lower()
                    
                    if WAKE_WORD in text:
                        if session_lock.acquire(blocking=False):
                            try:
                                if not active_session:
                                    active_session = True
                                    print(f"\n[🔔 WAKE WORD ERKANNT auf {mic_name} (ID {mic_id})]!")
                                    handle_active_command(q, mic_name, rec)
                            finally:
                                session_lock.release()

    except Exception as e:
        print(f"[FEHLER bei Mikrofon {mic_id} - {mic_name}]: {e}")

if __name__ == "__main__":
    print("=== MULTI-MIKROFON WAKE-WORD SYSTEM (USBIP + MQTT) ===")
    mics = get_usb_microphones()
    if not mics:
        print("[!] Keine Mikrofone gefunden! Prüfen Sie Ihre USBIP-Verbindungen.")
        sys.exit(1)

    print(f"\n[+] Starte Threads für {len(mics)} Mikrofone...\n")

    for mic_id, mic_name in mics:
        t = threading.Thread(target=monitor_microphone, args=(mic_id, mic_name), daemon=True)
        t.start()

    try:
        while True:
            threading.Event().wait(1)
    except KeyboardInterrupt:
        print("\n[!] System wird heruntergefahren...")
        mqtt_client.loop_stop()
