# Wake Word & Smart Home Sprachassistent (Vosk + Python + USBIP)

Ein leichtgewichtiger, vollständig lokaler Sprachassistent in **Python**, der für den Betrieb auf einer **CPU ohne GPU** (z. B. auf einer zentralen Smart-Home-VM) optimiert ist. Das System horcht im Hintergrund auf ein konfigurierbares Wake Word (z. B. *„Jarvis“*), schaltet bei Erkennung in den Aktiv-Modus, zeichnet Sprache mit einer dynamischen Stille-Erkennung (VAD) auf und transkribiert den Befehl via **Vosk**.

Dieses Projekt ist speziell für verteilte Smart-Home-Labore konzipiert, bei denen **mehrere USB-Mikrofone über USBIP (USB over IP) von verschiedenen Raspberry Pis** im Raum an eine zentrale VM angebunden werden.

---

## Inhaltsverzeichnis

1. [Wichtige Architektur-Abgrenzung (Transkription vs. LLM)](#wichtige-architektur-abgrenzung-transkription-vs-llm)
2. [Projektstruktur](#projektstruktur)
3. [Voraussetzungen & Hardware](#voraussetzungen--hardware)
4. [Installation & Setup](#installation--setup)
5. [USBIP-Architektur & Mikrofon-Verteilung](#usbip-architektur--mikrofon-verteilung)
6. [Pegelanpassung & Per-Mic Gain](#pegelanpassung--per-mic-gain)
7. [Skripte im Überblick](#skripte-im-überblick)
8. [MQTT-Integration](#mqtt-integration)
9. [24/7 Betrieb als Systemd-Service](#247-betrieb-als-systemd-service)
10. [Verwendung & Ausführung](#verwendung--ausführung)

---

## Wichtige Architektur-Abgrenzung (Transkription vs. LLM)

> ⚠️ **Wichtiger Hinweis zum Einsatzzweck:**
> Dieses Skript ist **keine** semantische KI oder Intent-Erkennung. Es führt keinerlei Analyse des Gesagten aus und steuert direkt **keinerlei** Smart-Home-Geräte. 
> 
> * **Was dieses Tool tut:** Es erkennt das Wake Word, nimmt den Audiostrom auf, transkribiert den gesprochenen Text buchstabengetreu über Vosk und gibt ihn aus (bzw. publisht ihn optional per MQTT).
> * **Die Konsequenz:** Da Spracherkennung auf CPU-Modellen (wie dem kleinen oder mittleren Vosk-Modell) gelegentlich zu Tippfehlern, homophonen Verwechslungen oder Grammatikunzulänglichkeiten führen kann, muss eine nachgeschaltete Instanz (z. B. ein Large Language Model / LLM, Node-RED oder Home Assistant) die semantische Korrektur vornehmen. Das LLM ist dafür zuständig, Tippfehler im erkannten Text zu interpretieren, zu korrigieren und die eigentliche Smart-Home-Aktion abzuleiten.

---

## Projektstruktur

```text
/root/wake_word/
│
├── .gitignore                          # Ignoriert temporäre Dateien und Cache
├── README.md                           # Diese Projektdokumentation
├── diagnose_without_gain.py            # Testskript zur reinen Pegelmessung
├── diagnose_with_gain.py               # Testskript mit Software-Verstärkung
├── wake_word.py                        # Einzelplatz-Skript (für 1 Mikrofon)
├── wake_word_multiple_microphones.py   # Multi-Mikrofon-Skript (Konsole / Standalone)
├── wake_word_multiple_microphones_mqtt.py # Multi-Mikrofon-Skript mit MQTT-Publish
└── vosk-model-de-0.21/                 # Entpacktes deutsches Vosk-Sprachmodell (ca. 1.9 GB)
```

---

## Voraussetzungen & Hardware

* **Python 3.8+**
* **Arbeitsspeicher (RAM):** Ca. 2–4 GB freier RAM für das Modell `vosk-model-de-0.21`.
* **Empfohlene Hardware:**
* **Mikrofon:** *Fame Audio BM91U* (USB-Grenzflächenmikrofon / Boundary Mic). Durch die flache Bauweise und Kugelcharakteristik ideal zur raumfüllenden Abdeckung von 5–10 qm geeignet.
* **Infrastruktur:** Raspberry Pis als USBIP-Server im Raum verteilt (siehe [USBIP-Configuration Repository](https://github.com/Michdo93/USBIP-Configuration)).

### Notwendige Python-Bibliotheken

Für die Standard-Skripte:

```bash
pip install vosk sounddevice numpy
```

Zusätzlich für `wake_word_multiple_microphones_mqtt.py`:

```bash
pip install paho-mqtt
```

---

## Installation & Setup

1. **Repository klonen:**
```bash
git clone [https://github.com/Michdo93/wake-word](https://github.com/Michdo93/wake-word)
cd wake-word
```

2. **Vosk-Modell herunterladen & entpacken:**
Laden Sie `vosk-model-de-0.21` von [alphacephei.com/vosk/models](https://alphacephei.com/vosk/models) herunter und entpacken Sie es im Projektverzeichnis.

---

## USBIP-Architektur & Mikrofon-Verteilung

Die Raspberry Pis im Raum stellen die USB-Mikrofone über USBIP im Netzwerk bereit. Die zentrale VM bindet diese ein. Das Betriebssystem der VM sieht jedes Mikrofon als eigenständiges Audiogerät.
Die Multi-Mikrofon-Skripte scannen alle Inputs und starten für jedes Gerät einen isolierten Thread. Ein globaler `threading.Lock()` verhindert Echo und Mehrfachantworten nach dem "First-Wins"-Prinzip.

---

## Pegelanpassung & Per-Mic Gain

Da verschiedene Mikrofone im Raum unterschiedliche Grundpegel aufweisen, können Sie im Skript über das Dictionary `MIC_GAIN_CONFIG` individuelle Verstärkungen hinterlegen:

```python
MIC_GAIN_CONFIG = {
    "Fame Audio BM91U": 4.0,   # Geringerer Gain, da hochempfindliches Grenzflächenmikrofon
    "default": 8.0             # Höherer Fallback-Gain für Standard-Dongles/Billig-Pucks
}
```

* **Zu niedriger Pegel (< 300 RMS):** Das Signal wird von Vosk als Rauschen verworfen. Erhöhen Sie den `GAIN_FACTOR` im Code oder drehen Sie den Pegel im Linux-Mixer (`alsamixer`) hoch.
* **Zu hoher Pegel (> 25000 RMS):** Es droht Übersteuerung (Clipping). Reduzieren Sie den Gain, um Verzerrungen bei der Spracherkennung zu vermeiden.

---

## Skripte im Überblick

* **`diagnose_without_gain.py`**: Prüft, ob Audio-Streams auf der VM ankommen und liefert die rohen RMS-Pegel.
* **`diagnose_with_gain.py`**: Testskript mit Software-Verstärkung (`GAIN_FACTOR`) zur Kalibrierung.
* **`wake_word.py`**: Einzelplatz-Skript für den lokalen Test mit exakt einem Mikrofon.
* **`wake_word_multiple_microphones.py`**: Überwacht alle USBIP-Mikrofone parallel, steuert das First-Wins-Lock und gibt erkannte Befehle direkt in der **Konsole** aus.
* **`wake_word_multiple_microphones_mqtt.py`**: Identisch zur Multi-Mikrofon-Logik, leitet den erkannten Text jedoch zusätzlich per **MQTT** an einen Broker weiter.

---

## MQTT-Integration (`wake_word_multiple_microphones_mqtt.py`)

Nutzen Sie die MQTT-Variante, wenn die erkannten Befehle ins Smart Home (z. B. Node-RED, Home Assistant oder ein LLM-Service) übertragen werden sollen.

* **Topic:** `smarthome/voice/command` (anpassbar im Code)
* **Payload Beispiel (JSON):**
```json
{
  "microphone": "Fame Audio BM91U (USB Audio)",
  "command": "wie ist das wetter heute in furtwangen"
}
```

---

## 24/7 Betrieb als Systemd-Service

Für den permanenten Hintergrundbetrieb auf einer Linux-VM (hier am Beispiel der MQTT-Variante):

1. Erstellen Sie die Service-Datei:
```bash
sudo nano /etc/systemd/system/wakeword.service
```


2. Tragen Sie folgende Konfiguration ein:
```ini
[Unit]
Description=Wake Word Smart Home Lab Service (Vosk + USBIP + MQTT)
After=network.target sound.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/wake_word
ExecStart=/usr/bin/python3 /root/wake_word/wake_word_multiple_microphones_mqtt.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```


3. Aktivieren und starten:
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now wakeword.service
```

---

## Verwendung & Ausführung

Starten Sie das gewünschte Skript manuell oder über den Systemdienst:

```bash
# Entweder die Konsolen-Version:
python wake_word_multiple_microphones.py

# Oder die MQTT-Version:
python wake_word_multiple_microphones_mqtt.py
```

Das System lauscht nun permanent auf allen angebundenen USBIP-Mikrofonen, filtert Überlagerungen heraus, transkribiert lokal auf der CPU und übergibt die Daten an die nachgeschaltete Logik bzw. das LLM.
