# Wake Word & Smart Home Sprachassistent (Vosk + Python + USBIP)

Ein leichtgewichtiger, vollständig lokaler Sprachassistent in **Python**, der für den Betrieb auf einer **CPU ohne GPU** (z. B. auf einer zentralen Smart-Home-VM) optimiert ist. Das System horcht im Hintergrund auf ein konfigurierbares Wake Word (z. B. *„Jarvis“*), schaltet bei Erkennung in den Aktiv-Modus, zeichnet Sprache mit einer dynamischen Stille-Erkennung (VAD) auf und transkribiert den Befehl via **Vosk**.

Dieses Projekt ist speziell für verteilte Smart-Home-Labore konzipiert, bei denen **mehrere USB-Mikrofone über USBIP (USB over IP) von verschiedenen Raspberry Pis** im Raum an eine zentrale VM angebunden werden.

---

## Inhaltsverzeichnis

1. [Projektstruktur](https://www.google.com/search?q=%23projektstruktur)
2. [Voraussetzungen](https://www.google.com/search?q=%23voraussetzungen)
3. [Installation & Setup](https://www.google.com/search?q=%23installation--setup)
4. [USBIP-Architektur & Mikrofon-Verteilung (Smart Home Lab)](https://www.google.com/search?q=%23usbip-architektur--mikrofon-verteilung-smart-home-lab)
5. [Skripte im Überblick](https://www.google.com/search?q=%23skripte-im-%C3%BCberblick)
6. [Verwendung & Ausführung](https://www.google.com/search?q=%23verwendung--ausf%C3%BChrung)
7. [Konfiguration & Feinjustierung](https://www.google.com/search?q=%23konfiguration--feinjustierung)

---

## Projektstruktur

Das Repository enthält im Root-Verzeichnis folgende Dateien und Ordner:

```text
C:\Users\Admin\Desktop\Projekte\wake_word\
│
├── .gitignore                      # Ignoriert temporäre Dateien und Cache
├── README.md                       # Diese Projektdokumentation
├── diagnose_without_gain.py        # Testskript zur reinen Pegelmessung (Rohsignal)
├── diagnose_with_gain.py           # Testskript mit Software-Verstärkung (Gain)
├── wake_word.py                    # Einzelplatz-Skript (für 1 Mikrofon / Lokaltest)
├── wake_word_multiple_microphones.py # Multi-Mikrofon-Skript für bis zu N USBIP-Mikrofone
└── vosk-model-de-0.21/             # Entpacktes deutsches Vosk-Sprachmodell (ca. 1.9 GB)
    ├── am/
    ├── conf/
    ├── graph/
    └── ...

```

---

## Voraussetzungen

* **Python 3.8+**
* Ausreichend Arbeitsspeicher (RAM) für das Sprachmodell (ca. 2–4 GB freier RAM für das Modell `vosk-model-de-0.21`).
* **Hardware:** Ein oder mehrere USB-Mikrofone (z. B. USB-Grenzflächenmikrofone wie das *Fame Audio BM91U* für größere Raumabdeckungen von 5–10 qm).
* **Netzwerkinfrastruktur:** Raspberry Pis als USBIP-Server (siehe [USBIP-Configuration Repository](https://github.com/Michdo93/USBIP-Configuration)).

### Notwendige Python-Bibliotheken

Installieren Sie die Abhängigkeiten über die PowerShell oder das Terminal:

```bash
pip install vosk sounddevice numpy

```

---

## Installation & Setup

1. **Repository klonen:**
Klonen Sie das Repository auf Ihrem System:
```bash
git clone https://github.com/Michdo93/wake-word
cd wake-word

```


2. **Vosk-Modell herunterladen:**
Laden Sie das deutsche Sprachmodell `vosk-model-de-0.21` (oder die leichtere Variante `vosk-model-small-de-0.15`) von [alphacephei.com/vosk/models](https://alphacephei.com/vosk/models) herunter.
3. **Modell entpacken:**
Entpacken Sie den heruntergeladenen Modell-Ordner direkt in das Projektverzeichnis. Der Ordnername muss exakt `vosk-model-de-0.21` lauten.

---

## USBIP-Architektur & Mikrofon-Verteilung (Smart Home Lab)

In einem verteilten Smart-Home-Labor stehen im Raum verteilt mehrere Raspberry Pis. Auf diesen Pis läuft ein USBIP-Server, der USB-Mikrofone (z. B. Konferenz-Grenzflächenmikrofone) im lokalen Netzwerk freigibt.

### 1. Einrichtung der USBIP-Server (Raspberry Pis)

Eine vollständige Anleitung und Konfigurationshilfen zur Bereitstellung der Geräte finden Sie im zugehörigen Repository:
👉 **[GitHub: Michdo93/USBIP-Configuration](https://github.com/Michdo93/USBIP-Configuration)**

### 2. Einbinden in die zentrale VM (Client)

Die zentrale VM (Ihr Host-System ohne GPU) bindet die entfernten USB-Mikrofone der Raspberry Pis über den USBIP-Client ein. Das Betriebssystem der VM erkennt jedes angeschlossene Mikrofon automatisch als eigenständiges USB-Audio-Eingabegerät (`Input-Device`).

### 3. Herausforderung bei 10+ Mikrofonen & die Lösung im Code:

* **Keine Überlastung:** Auf einer CPU-VM wäre es fatal, für jedes Mikrofon ein separates, schweres Sprachmodell zu laden. Das Skript teilt sich daher ein **einziges zentrales Vosk-Modell** im Arbeitsspeicher.
* **Multi-Threading:** Das Skript `wake_word_multiple_microphones.py` scannt automatisch alle verfügbaren Eingabegeräte und startet für jedes verbundene USBIP-Mikrofon einen eigenen, ressourcenschonenden Hintergrund-Thread.
* **Kollisionsschutz ("First-Wins"-Lock):** Wenn in einem großen Raum mehrere Mikrofone gleichzeitig das Wake Word *"Jarvis"* hören, würde dies ohne Schutz zu Echo-Effekten und doppelten Antworten führen. Ein globaler `threading.Lock()` sorgt dafür, dass das Mikrofon mit dem ersten Treffer die exklusive Session übernimmt und alle anderen Mikrofone für die Dauer der Sprachaufnahme (sowie 3 Sekunden Stille-Puffer) automatisch stummschaltet.

---

## Skripte im Überblick

* **`diagnose_without_gain.py`**: Hilfskript, um zu prüfen, ob Audio-Streams auf der VM ankommen und welche Rohpegel (RMS) das Mikrofon liefert.
* **`diagnose_with_gain.py`**: Testskript mit integrierter Software-Verstärkung (`GAIN_FACTOR`), ideal für leisere Hardware oder schlecht ausgestattete Soundtreiber.
* **`wake_word.py`**: Einfaches Standalone-Skript für den lokalen Test mit genau einem Mikrofon.
* **`wake_word_multiple_microphones.py`**: Das Hauptskript für das Labor, das automatisch alle über USBIP angebundenen Mikrofone überwacht.

---

## Verwendung & Ausführung

### Multi-Mikrofon-Betrieb (Labor-Modus)

Starten Sie das Multi-Mikrofon-Skript in Ihrer zentralen VM:

```bash
python wake_word_multiple_microphones.py

```

### Ablauf der Interaktion:

1. **Automatischer Scan:** Das Skript listet beim Start alle erkannten Audio-Inputs (Ihre USBIP-Mikrofone) auf und startet die Überwachung.
2. **Standby:** Alle Threads lauschen im Hintergrund auf das Wake Word (`jarvis`).
3. **Aktivierung & Lock:** Fällt das Wort an einem Mikrofon, greift der Lock. Die anderen Mikrofone werden ignoriert.
4. **Satzaufnahme mit VAD (Voice Activity Detection):**
* Sprechen Sie Ihren Befehl (z. B. *„Wie ist das Wetter heute in Furtwangen?“*).
* **Stille-Timeout:** Sobald auf dem aktiven Mikrofon **3 Sekunden** lang ununterbrochen geschwiegen wird, bricht die Aufnahme automatisch ab.
* **Maximales Limit:** Die Aufnahme stoppt spätestens nach **30 Sekunden** als Hard-Limit.


5. **Ausgabe & Reset:** Der transkribierte Befehl wird ausgegeben, die Session wird freigegeben und das System kehrt nahtlos in den Standby-Modus zurück.

---

## Konfiguration & Feinjustierung

Im oberen Bereich der Python-Skripte können Sie Anpassungen vornehmen:

* **`SAMPLE_RATE = 16000`**: Standard-Abtastrate für Vosk.
* **`WAKE_WORD = "jarvis"`**: Das auslösende Schlüsselwort.
* **`GAIN_FACTOR = 8.0`**: Software-Verstärkung, falls die USBIP-Mikrofone im System zu leise übertragen werden.
* **`MODEL_PATH = "vosk-model-de-0.21"`**: Pfad zum verwendeten Sprachmodell.
