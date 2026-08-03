# 🔍 FaceLens — Moteur de Recherche Biométrique Local & Module de Scraping

> **Avertissement Légal & Éthique Obligatoire** :  
> *« La similarité faciale n'est pas une preuve d'identité. Vérifiez les sources avant toute conclusion. »*

**FaceLens** est un outil 100 % open source et self-hosted de recherche de visage par similarité biométrique (alternative libre à PimEyes / FaceCheck.ID).

> Le dépôt contient uniquement le code source. Les corpus, images indexées,
> bases SQLite, index FAISS, fichiers `.env` et sessions Instagram restent
> locaux et sont exclus de Git.

---

## 🚀 Fonctionnalités Clés
- **Recherche par Visage (1:N)** : Indexation vectorielle 512-d via ArcFace (`buffalo_l`) et FAISS `IndexIDMap2`.
- **Vérification 1:1** : Comparaison directe de deux photos de profil avec verdicts (`fort`, `moyen`, `sosie`, `faux_positif`).
- **Cohérence Atomique SQLite ↔ FAISS** : Double écriture transactionnelle avec vérification automatique d'intégrité (`verify_integrity`).
- **Module Scraping "Spider"** : Collecte intelligente de pages web publiques via Playwright (scroll lazy-load) et SearXNG, avec déduplication cosinus > 0.95.
- **CLI Catfish Checker** : Script d'analyse rapide en ligne de commande avec support `--dry-run`.
- **Droit à l'Oubli & Exclusion** : Endpoints de suppression de visage et d'exclusion de domaine.

## 🖥️ Console Web

FaceLens inclut une console React responsive pour piloter localement les
principaux workflows :

- recherche faciale 1:N avec détection et landmarks réels ;
- comparaison directe 1:1 ;
- consultation et suppression contrôlée du corpus ;
- lancement et suivi des collectes publiques ;
- journal local exportable des opérations.

Les instructions d'installation, de configuration et de build se trouvent
dans [`frontend/README.md`](frontend/README.md).

---

## 🛠️ Stack Technique
- **Détection & Embedding** : InsightFace `buffalo_l` (RetinaFace/SCRFD + ArcFace 512-d L2 normalisé).
- **Index Vectoriel** : FAISS `IndexIDMap2(IndexFlatIP(512))`.
- **Stockage Métadonnées** : SQLite local.
- **Backend API** : FastAPI (Python 3.11+).
- **Scraping** : Playwright (async Chromium headless), BeautifulSoup, Trafilatura, SearXNG API (HTTP uniquement).
- **Fallback Exact Copy** : Perceptual hashing (`imagehash` pHash).

---

## 📦 Installation Locale

```bash
# 1. Cloner le dépôt et créer un environnement virtuel
python -m venv venv
source venv/bin/activate  # Sur Windows: venv\Scripts\activate

# 2. Installer les dépendances
pip install -r requirements.txt

# 3. Installer les navigateurs Playwright (pour le scraping JS)
playwright install chromium
```

### Téléchargement des Modèles `buffalo_l`
Au premier lancement, **InsightFace** télécharge automatiquement le modèle `buffalo_l` dans `~/.insightface/models/buffalo_l.zip`.  
Si vous devez le télécharger manuellement sur un environnement hors-ligne :
1. Téléchargez `buffalo_l.zip` depuis le dépôt officiel [InsightFace Releases](https://github.com/deepinsight/insightface/releases).
2. Extrayez le dossier dans `~/.insightface/models/buffalo_l/` (doit contenir `det_10g.onnx`, `w600k_mbf.onnx`, etc.).

---

## 🧪 Exemples d'Utilisation API (Curl)

Lancer le serveur API FastAPI :
```bash
uvicorn app.main:app --reload --port 8000
```

### 1. Comparaison 1:1 (`POST /api/faces/verify`)
```bash
curl -X POST "http://localhost:8000/api/faces/verify" \
  -F "image_a=@photo1.jpg" \
  -F "image_b=@photo2.jpg"
```

### 2. Inscription au Corpus (`POST /api/faces/enroll`)
```bash
curl -X POST "http://localhost:8000/api/faces/enroll" \
  -F "file=@suspect.jpg" \
  -F "person_name=John Doe" \
  -F "source_url=https://example.com/profile" \
  -F "source_type=web"
```

### 3. Recherche 1:N (`POST /api/faces/search`)
```bash
curl -X POST "http://localhost:8000/api/faces/search?top_k=10" \
  -F "file=@query.jpg"
```

### 4. Lancer un Job de Scraping (`POST /api/scrape/url`)
```bash
curl -X POST "http://localhost:8000/api/scrape/url" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://forum-public.com/topic/123", "max_images": 30}'
```

---

## 💻 Usage CLI — Catfish Checker (`check_catfish.py`)

Comparer une photo suspecte contre un dossier ou un fichier CSV (`chemin|nom`) :

```bash
# Vérification normale
python cli/check_catfish.py --target suspect.jpg --candidates ./candidats_dir/

# Mode Simulation (Dry-Run sans écriture)
python cli/check_catfish.py --target suspect.jpg --candidates candidats.csv --dry-run
```

---

## 🐳 Déploiement Docker Compose

Pour déployer **FaceLens** et l'instance locale **SearXNG** sur le même réseau isolé :

```bash
docker-compose up -d
```

- API FaceLens : `http://localhost:8000`
- API SearXNG : `http://localhost:8080`

---

## 🧪 Exécution des Tests

```bash
python -m pytest tests/ -v
```

---

## 🤝 Contribution

Créez une branche dédiée, vérifiez les tests concernés puis ouvrez une
Pull Request vers `main`. Les corpus, images indexées, bases et sessions
locales ne doivent jamais être joints à une contribution.
