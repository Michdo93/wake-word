# Wake Word & Smart Home Sprachassistent (Vosk + Python)

Ein leichtgewichtiger, vollständig lokaler Sprachassistent in **Python**, der auf einer CPU ohne GPU läuft. Das System horcht im Hintergrund auf ein Wake Word (z. B. *„Jarvis“*), wechselt bei Erkennung in den Aktiv-Modus, zeichnet Sprache mit einer dynamischen Stille-Erkennung (VAD) auf und transkribiert den Befehl via **Vosk**.

Dieses Projekt dient als Basis für verteilte Mikrofone (z. B. mit USBIP und Raspberry Pis).

---

## 📋 Inhaltsverzeichnis

1. [Voraussetzungen](#voraussetzungen)
2. [Installation & Setup](#installation--setup)
3. [Verwendung](#verwendung)
4. [Projektstruktur](#projektstruktur)
5. [Konfiguration & Feinjustierung](#konfiguration--feinjustierung)

---

## 🛠️ Voraussetzungen

* **Python 3.8+**
* Ein funktionierendes Mikrofon (unter Windows/Linux getestet)
* Ausreichend Arbeitsspeicher (RAM) für das gewählte Vosk-Modell (ca. 2–4 GB frei für das große Modell).

### Notwendige Python-Bibliotheken

Installieren Sie die Abhängigkeiten über die PowerShell oder das Terminal:

```bash
pip install vosk sounddevice numpy
```

---

## 🚀 Installation & Setup

1. **Repository klonen:**
Klonen sie das Repository `wake-word` auf Ihrem System:
```bash
git clone https://github.com/Michdo93/wake-word
cd wake-word
```


2. **Vosk-Modell herunterladen:**
Laden Sie ein deutsches Sprachmodell von [alphacephei.com/vosk/models](https://alphacephei.com/vosk/models) herunter (empfohlen für hohe Erkennungsrate auf CPUs: `vosk-model-de-0.21` oder die leichtere Variante `vosk-model-small-de-0.15`).
3. **Modell entpacken:**
Entpacken Sie den heruntergeladenen Modell-Ordner direkt in Ihr Projektverzeichnis `wake_word`. Der Ordnername (z. B. `vosk-model-de-0.21`) muss exakt mit dem Pfad im Skript übereinstimmen.
4. **Skript ablegen:**
Speichern Sie das Hauptskript als `wake_word.py` im selben Verzeichnis.

---

## 💡 Verwendung

Starten Sie das Skript direkt über die Konsole:

```bash
python wake_word.py
```

### So funktioniert die Interaktion:

1. **Standby:** Das Skript lauscht im Hintergrund auf das definierte Wake Word (`jarvis`).
2. **Aktivierung:** Sobald das Wake Word fällt, schaltet das System in den Aufnahme-Modus (`[🎙️ HÖRE ZU]`).
3. **Satzaufnahme:**
* Sprechen Sie Ihren Befehl (z. B. *„Wie ist das Wetter heute in Furtwangen?“*).
* **Stille-Erkennung:** Sobald Sie **3 Sekunden** lang schweigen, stoppt die Aufnahme automatisch.
* **Sicherheitslimit:** Die Aufnahme bricht spätestens nach **30 Sekunden** automatisch ab.


4. **Ausgabe:** Der erkannte Text wird ausgegeben und das System kehrt in den Standby zurück.

---

## 📂 Projektstruktur

```text
wake_word/
│
├── wake_word.py              # Hauptskript mit Wake-Word- & VAD-Logik
└── vosk-model-de-0.21/       # Entpacktes Vosk-Sprachmodell (Deutsch)
    ├── am/
    ├── conf/
    ├── graph/
    └── ...
```

---

## ⚙️ Konfiguration & Feinjustierung

Im oberen Bereich der `wake_word.py` können Sie Parameter an Ihre Hardware anpassen:

* **`SAMPLE_RATE = 16000`**: Standard-Abtastrate für Spracherkennung.
* **`WAKE_WORD = "jarvis"`**: Das auslösende Schlüsselwort.
* **`GAIN_FACTOR = 8.0`**: Software-Verstärkung für leisere Mikrofone (verhindert, dass das Signal unter dem Schwellenwert liegt).
* **`device=1`**: ID des Eingabegeräts (kann bei Bedarf via `sd.query_devices()` angepasst werden, falls das Standardmikrofon gewechselt werden muss).
