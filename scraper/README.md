# 🕷️ FaceLens Spider — Guide du Module de Scraping

## 1. Principes & Règles de Politesse

Le module de scraping **FaceLens Spider** est conçu pour collecter exclusivement des données visuelles biométriques à partir de **pages web publiques**.

### Consignes de politesse obligatoires :
1. **Respect de `robots.txt`** : Consultation automatique du fichier `robots.txt` du domaine cible avant toute requête HTTP.
2. **Délais aléatoires** : Temporisation de **2 à 5 secondes** entre chaque téléchargement de page.
3. **Limitation de concurence** : Maximum 3 requêtes simultanées par domaine (`Semaphore(3)`).
4. **Gestion du Rate-Limit (HTTP 429)** : Interruption propre du crawl et enregistrement de l'échec dans `errors_by_domain`.
5. **Aucun contournement anti-bot** : Interdiction formelle de résoudre des CAPTCHAs, d'outrepasser Cloudflare ou d'utiliser des cookies de sessions privées.

---

## 2. Périmètre & Sources Autorisées
- Pages publiques de forums (sans authentification).
- Profils publics de réseaux sociaux ou sites de rencontre ouverts.
- Articles de presse et blogs d'actualité.
- Recherche d'images via méta-moteur **SearXNG** self-hosted.

---

## 3. Déduplication des Visages (Skip 0.95)
Chaque visage extrait subit une comparaison vectorielle cosinus avec le corpus existant :
- Si `similarité >= 0.95`, l'image est considérée comme déjà indexée et est **ignorée** (`duplicates_skipped`).

---

## 4. Procédure du Droit à l'Oubli Local

Conformément à la réglementation locale et à l'éthique du projet :

### Suppression d'un visage spécifique
```bash
curl -X DELETE "http://localhost:8000/api/scrape/face/42"
```

### Exclusion d'un domaine entier & Purge des visages
```bash
curl -X DELETE "http://localhost:8000/api/scrape/source/domaine-interdit.com"
```
Cette commande :
1. Ajoute `domaine-interdit.com` dans la table SQLite `excluded_domains`.
2. Purge atomiquement tous les visages et vecteurs FAISS associés à ce domaine.
3. Bloque tout futur scraping ciblant ce domaine.
