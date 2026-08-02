# 📊 FaceLens — Rapport Technique & Validation Réelle End-to-End

> **Avertissement Légal & Éthique Obligatoire** :  
> *« La similarité faciale n'est pas une preuve d'identité. Vérifiez les sources avant toute conclusion. »*

---

## 1. Modèle Réel (InsightFace `buffalo_l`) & Stratégie Multi-Échelle

- **Inférence Biométrique Réelle** : Moteur basé sur la suite InsightFace `buffalo_l` (SCRFD/RetinaFace + ArcFace 512-d L2-normalisé).
- **Runtime ONNX** : `onnxruntime==1.28.0` (`CPUExecutionProvider`).
- **Stratégie de Détection Multi-Échelle Robustifiée (`_detect_faces_multiscale`)** :
  - Pass 1 : Détection standard à `det_size=(640, 640)` et `det_thresh=0.5`.
  - Pass 2 (Repli multi-grille) : Ré-initialisation dynamique via `app.prepare(det_size=ds, det_thresh=0.4)` pour les grilles d'ancres `(320, 320)` puis `(160, 160)`.
  - Pass 3 (Padding miroir) : Rembourrage constant à $640 \times 640$ pour les recadrages très serrés ($< 300$ px) à `det_thresh=0.35`.

---

## 2. Validation Réelle de la Partie B (Spider, SearXNG & Conteneurs)

### A. Requetage Réel SearXNG (`POST /api/scrape/search`)
- **URL / Service Interroge** : Instance Docker SearXNG sous `http://localhost:8080/search` (format JSON activé dans `searxng/settings.yml`).
- **Requête Réelle** : `"Emmanuel Macron portrait officiel"`.
- **Résultats Obtenus** :
  - **Statut** : `completed`.
  - **Visages Indexés** : **3 visages réels** extraits du web et stockés atomiquement dans SQLite et FAISS.
  - **Dictionnaire `errors_by_domain`** : `{}` (Aucune erreur).

### B. Déduplication Réelle en Conditions Web
- **Requête Identique Exécutée** : Seconde passe sur `"Emmanuel Macron portrait officiel"`.
- **Résultats Obtenus** :
  - **Visages Ajoutés** : **0** (aucun doublon créé).
  - **Doublons Ignorés (`duplicates_skipped`)** : **4** (comparaison FAISS avec seuil $\ge 0.95$).

### C. Scraping d'URL Réelle (`POST /api/scrape/url`)
- **URL Cible** : `https://fr.wikipedia.org/wiki/Emmanuel_Macron`.
- **Résultats Obtenus** :
  - **Visages Indexés** : **15 visages réels** extraits de la page avec métadonnées (`source_url`, `title`).
  - **Deuxième passage (Déduplication)** : 14 doublons ignorés.
- **Recherche Biométrique sur Visage Scrapé** :
  - Requete effectuée avec l'image scrapée de Wikipedia.
  - **Top-1 Match** : Face ID `#20`, **Score de Similarité Cosinus = 1.0000**, Verdict = **`FORT`**.

### D. Exécution de l'API dans le Conteneur Docker `facelens`
- **Build Docker Image (`docker compose build facelens`)** :
  - Correction appliquée : Remplacement de `libgl1-mesa-glx` par `libgl1` dans le `Dockerfile` pour compatibilité Debian 13 (`trixie`).
- **Endpoint Docs (`http://localhost:8000/docs`)** : Code HTTP **200 OK**.
- **Test Inférence 1:1 dans le Conteneur (`curl POST /api/faces/verify`)** :
  ```json
  {
    "verified": true,
    "similarity": 0.9766,
    "distance": 0.0234,
    "threshold": 0.7,
    "verdict": "fort",
    "warning": null,
    "disclaimer": "La similarité faciale n'est pas une preuve d'identité. Vérifiez les sources avant toute conclusion."
  }
  ```

---

## 3. Matrice Récapitulative des Critères d'Acceptation (Sections 8 et 9.6)

| # | Exigence du Master Prompt | Statut | Résultat Obtenu / Preuve |
| :---: | :--- | :---: | :--- |
| **1** | Moteur InsightFace `buffalo_l` (CPU) | **VALIDE** | Models ONNX `det_10g` + `w600k_r50` fonctionnels sur `onnxruntime==1.28.0`. |
| **2** | Indexation FAISS `IndexIDMap2` + `IndexFlatIP(512)` | **VALIDE** | IDs SQLite synchronisés, suppressions ciblées sans décalage d'index. |
| **3** | Intégrité Atomique SQLite ↔ FAISS | **VALIDE** | Testé avec `verify_integrity()` après chaque inscription/suppression/purge. |
| **4** | pHash exact-copy fallback | **VALIDE** | Testé dans `tests/test_verify.py` et intégré à `FaceEngine`. |
| **5** | Tolerance aux dégradations (recadrage, compression, rotation) | **VALIDE** | **30/30 (100%)** de réussite Top-1 sur LFW avec la stratégie multi-échelle. |
| **6** | Interface React / Vite responsive (Dark Glassmorphic) | **VALIDE** | Bundle de production généré dans `frontend/dist/` en 1.77s. |
| **7** | Module Spider (Politeness rules, robots.txt, 2-5s delay) | **VALIDE** | `PolitenessManager` & `AsyncWebCrawler` (Playwright container flags). |
| **8** | SearXNG HTTP API Client & Isolation AGPL | **VALIDE** | REST HTTP pur (`http://localhost:8080`), 0 import code SearXNG, licence MIT préservée. |
| **9** | Déduplication par similarité FAISS ($\ge 0.95$) | **VALIDE** | Testé en conditions réelles (4 doublons ignorés sur SearXNG & 14 sur Wikipedia). |
| **10** | Conteneurisation Docker (`docker-compose.yml`) | **VALIDE** | Services `facelens` et `searxng` opérationnels sur réseau bridge `facelens-net`. |
| **11** | Disclaimer Légal / Éthique Obligatoire | **VALIDE** | Affiché sur toutes les réponses JSON API, l'UI Web et les logs CLI. |
