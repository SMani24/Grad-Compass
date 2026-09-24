# 🧭 Grad Compass

**Grad Compass** is an interactive, cartographic desktop workspace designed to organize international university applications, lab scouting, and faculty outreach.

Instead of juggling fractured spreadsheets, bookmarked lab pages, and scattered PDF folders, Grad Compass unifies the process into a visual hierarchy (**Country $\to$ Institution $\to$ Faculty Lead**) alongside an operational admissions Kanban board, cold outreach tracker, and a local document vault.

---

## Key Features

### 🗺️ Interactive Cartographic Directory

* **Vector World Map:** Rendered via Leaflet.js with low-overhead offline GeoJSON vector polygons—eliminating heavy map tile downloads and API subscription keys.
* **Country Highlighting & Flags:** Countries with active targets automatically highlight on the map. Every sovereign state resolves dynamically to its ISO code and flag emoji.
* **Cinematic Navigation:** Easing camera zoom (`flyTo`) transitions seamlessly from a blurred world hub down to local university coordinates.

### 🏛️ Automated Campus Geocoding & Wiki Image Caching

* **Autonomous Coordinate Resolution:** Input an institution name (e.g., *EPFL*, *ETH Zurich*, *TU Munich*); OpenStreetMap Nominatim automatically resolves its geographic latitude and longitude.
* **Wikipedia Visual Assets:** Integrates with the open Wikimedia REST API to fetch high-resolution campus photography, formatting pins as custom teardrop image badges on the map and rendering hero banners in the inspector pane.
* **Offline-Resilient Background Sync:** Images cache locally in `ui/cache/images/`. A background daemon continuously verifies and completes missing visual assets.

### 📂 Faculty Pipeline & Managed Document Vault

* **Relational Contact Hierarchy:** Track professors, lab affiliations, research focus keywords, and real-time communication statuses (*Not Contacted*, *Cold Emailed*, *Follow-up Needed*, *Interview Scheduled*).
* **Isolated Document Vault:** Attach CVs, statements of purpose, transcripts, or research papers directly to universities or professors. Files are safely copied into a categorized local vault directory and launched using your native OS PDF/document viewer.
* **One-Click Emailing:** Native `mailto:` integration launches pre-addressed drafts to faculty leads directly in your default mail client.

### 📋 Operational Radar & Admissions Kanban

* **Application Tracker:** A 4-stage Kanban pipeline (*Researching*, *Applying*, *Submitted*, *Decided*) with deadline reminders.
* **Faculty Outreach Radar:** A unified status dashboard with instant filtering to monitor pending replies and overdue follow-ups.
* **Fast To-Do Manager:** Add, check off, and delete checklist tasks linked to specific targets.

### ⚡ Desktop Ergonomics & Offline Independence

* **Local & Private:** Everything runs locally. Your data lives in a single local SQLite database (`grad_compass.db`) with zero external telemetry or cloud dependencies.
* **Browser-Style History Navigation:** Step forward and backward through exploration history using `Alt + ←` / `Alt + →` or `Esc`.
* **Persistent Preferences:** Automatically saves window dimensions, custom text sizing factors (*Normal*, *Medium*, *Large*, *XL*), and default map zoom levels across sessions.

---

## Tech Stack & Architecture

```
                    ┌────────────────────────────────────────┐
                    │      Desktop Shell (pywebview)         │
                    └───────────────────┬────────────────────┘
                                        │ (JS-Python Bridge)
         ┌──────────────────────────────┴──────────────────────────────┐
         ▼                                                             ▼
┌─────────────────────────────────┐                   ┌─────────────────────────────────┐
│        Frontend (WebKit/Qt)     │                   │       Backend (Python Core)     │
├─────────────────────────────────┤                   ├─────────────────────────────────┤
│ • Leaflet.js (Vector Map)       │                   │ • SQLite3 Relational Engine     │
│ • Hardware-accelerated CSS Blur │                   │ • Nominatim Geocoder (geopy)    │
│ • Dual-Drawer Sliding Inspector │                   │ • Wikipedia Image Scraper/Cache │
│ • Dual-Index Flag Resolver      │                   │ • Managed OS Document Vault     │
└─────────────────────────────────┘                   └─────────────────────────────────┘

```

* **GUI Engine:** [`pywebview`](https://pywebview.flowrl.com/?utm_source=gemini) powered by Qt6 WebEngine (or WebKitGTK on Linux).
* **Backend:** Python 3.10+ standard libraries (`sqlite3`, `threading`, `urllib`).
* **Geocoding:** `geopy` (OpenStreetMap Nominatim).
* **Cartography:** [Leaflet.js](https://leafletjs.com/?utm_source=gemini) v1.9.4 with local GeoJSON boundary vectors.

---

## Directory Structure

```text
Grad-Compass/
├── app.py                      # Main desktop application & pywebview API bridge
├── core/
│   ├── database.py             # SQLite schema, migrations, and CRUD operations
│   ├── geocoder.py             # OpenStreetMap geocoding & Wikipedia photo caching
│   └── vault.py                # Managed document storage & OS launcher hooks
├── ui/
│   ├── index.html              # Main application markup & modal templates
│   ├── css/
│   │   └── styles.css          # Theme tokens, layout frames, and photo pins
│   ├── js/
│   │   ├── app.js              # State manager, history stack, and UI controller
│   │   ├── flags.js            # Comprehensive ISO-3 country & emoji flag registry
│   │   └── map.js              # Leaflet engine, GeoJSON layers, and marker plots
│   ├── data/
│   │   └── countries.geo.json  # Bundled 110m low-poly world boundaries
│   ├── cache/                  # Local cache for university thumbnail images
│   └── vendor/
│       ├── leaflet.js          # Vendored Leaflet library
│       └── leaflet.css
├── data/                       # Local database and document storage (git-ignored)
│   ├── grad_compass.db         # Relational SQLite database
│   ├── config.json             # Window geometry & scale preferences
│   └── vault/                  # Stored SOPs, CVs, transcripts, and papers
├── requirements.txt
└── README.md

```

---

## Installation & Setup

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/grad-compass.git
cd grad-compass

```

### 2. Create and Activate a Virtual Environment

```bash
python3 -m venv envGradCompass
source envGradCompass/bin/activate

```

### 3. Install Python Dependencies

```bash
pip install -r requirements.txt

```

#### `requirements.txt`

```text
pywebview>=5.0.0
geopy>=2.4.0
PyQt6>=6.5.0
PyQt6-WebEngine>=6.5.0
qtpy>=2.4.0

```

> **Linux System Note:** On Ubuntu, Pop!_OS, or Debian, ensure your system has the standard multimedia and web libraries installed:
> ```bash
> sudo apt update && sudo apt install -y libgl1-mesa-glx
> 
> ```
> 
> 

---

## Running the Application

Launch the desktop interface from your terminal:

```bash
python3 app.py

```

---

## Desktop Integration (Linux / Pop!_OS / Ubuntu)

To integrate Grad Compass into your desktop environment so it appears in your system application launcher and dock:

1. **Create the `.desktop` launcher file:**
```bash
cat << 'EOF' > ~/.local/share/applications/grad-compass.desktop
[Desktop Entry]
Type=Application
Name=Grad Compass
GenericName=University Application Tracker
Comment=Global university application, faculty outreach, and vault manager
Exec=/absolute/path/to/grad-compass/envGradCompass/bin/python3 /absolute/path/to/grad-compass/app.py
Path=/absolute/path/to/grad-compass/
Icon=applications-education
Terminal=false
Categories=Office;Education;Utility;
Keywords=university;graduate;phd;masters;applications;compass;
StartupNotify=true
EOF

```


*(Be sure to replace `/absolute/path/to/grad-compass/` with your actual project directory).*
2. **Make it executable and update your desktop cache:**
```bash
chmod +x ~/.local/share/applications/grad-compass.desktop
update-desktop-database ~/.local/share/applications/

```


3. Press the **Super** key, search for **Grad Compass**, and pin it to your favorites.

---

## Keyboard Shortcuts

| Shortcut | Action | Scope |
| --- | --- | --- |
| `Ctrl + W` / `⌘ + W` | Save geometry and exit cleanly | Global |
| `Alt + ←` | Navigate back in history | Global |
| `Alt + →` | Navigate forward in history | Global |
| `Esc` | Close open modal, or step back one level | Global |

---

## Database Schema Overview

```sql
-- Target institutions
CREATE TABLE universities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    country_code TEXT NOT NULL,
    name TEXT NOT NULL,
    city TEXT,
    latitude REAL,
    longitude REAL,
    portal_url TEXT,
    deadline TEXT,
    status TEXT DEFAULT 'Researching', -- 'Researching', 'Applying', 'Submitted', 'Decided'
    image_url TEXT
);

-- Faculty contacts
CREATE TABLE professors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    university_id INTEGER NOT NULL REFERENCES universities(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    email TEXT,
    lab_website TEXT,
    research_interests TEXT,
    outreach_status TEXT DEFAULT 'Not Contacted' -- 'Not Contacted', 'Cold Emailed', 'Follow-up Needed', etc.
);

-- Local document vault metadata
CREATE TABLE attachments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    parent_type TEXT NOT NULL,                  -- 'university' or 'professor'
    parent_id INTEGER NOT NULL,
    file_name TEXT NOT NULL,
    stored_path TEXT NOT NULL
);

```

---

## Contributing

Contributions, bug reports, and suggestions are welcome.

1. Fork the Project.
2. Create a Feature Branch (`git checkout -b feature/NewFeature`).
3. Commit your changes (`git commit -m 'Add NewFeature'`).
4. Push to the Branch (`git push origin feature/NewFeature`).
5. Open a Pull Request.

---

## License

Distributed under the MIT License. See `LICENSE` for more information.