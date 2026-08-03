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

---

## 5. Module Instagram public (instagrapi 2.16.25)

Routes additives :
- `POST /api/insta/profile` avec `{"username":"..."}`;
- `POST /api/insta/medias` avec `{"username":"...","amount":10}`;
- suivi via `GET /api/scrape/status/{job_id}`.

L'étape 1 est strictement anonyme. L'adaptateur FaceLens appelle uniquement
`user_info_by_username_gql` et `user_medias_gql`, noms publics réels dans
instagrapi 2.16.25. Aucun login et aucune session ne sont chargés.

### Limites observées le 3 août 2026

- Python 3.14 : installation Windows et build Linux réussis.
- Premier lookup anonyme du compte officiel `instagram` : HTTP 429.
- La résolution HD et l'indexation réelle n'ont donc pas pu être validées.
- FaceLens limite désormais instagrapi à une seule tentative publique et
  termine le job en `partial`; aucun contournement n'est tenté.
- Les méthodes web publiques Instagram sont opportunistes : 401/403/404/429
  peuvent survenir sans changement de FaceLens.

### Risques et conformité

- Instagram peut bloquer l'IP ou un éventuel compte dédié ; respecter ses CGU
  et `robots.txt`, ne jamais contourner CAPTCHA, checkpoint ou paywall.
- Les embeddings faciaux sont des données biométriques sensibles au sens de
  l'article 9 du RGPD : définir une base légale, minimiser la collecte, limiter
  la conservation et traiter les demandes d'effacement.
- La suppression reste atomique via `DELETE /api/scrape/face/{id}`, suivie de
  `verify_integrity()`.

### Étape 2 — réservée, non activée

Le chemin prévu est `INSTAGRAM_SESSION_PATH=data/insta_session.json`, ignoré
par Git. Si l'étape 2 est autorisée plus tard : compte jetable dédié, jamais le
compte personnel, login initial dans l'application officielle, session
re-dumpée après résolution manuelle d'un checkpoint.

Limites maximales prévues : zéro parallélisme, délais aléatoires 5–8 s,
30 profils par session, environ 100 requêtes/heure, puis pause de 15 minutes.
`ChallengeRequired`, `FeedbackRequired` et `PleaseWaitFewMinutes` doivent
arrêter proprement la session ; aucun challenge ne sera automatisé.
