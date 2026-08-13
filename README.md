# FaceLens — votre atelier local de recherche par similarité faciale

> **FaceLens vous aide à comparer des images, pas à prouver une identité.** Une ressemblance algorithmique n’est jamais une preuve. Utilisez cet outil uniquement de manière licite, proportionnée et respectueuse des personnes concernées.

FaceLens est une application **auto-hébergée** : elle fonctionne sur votre ordinateur ou votre propre serveur, au lieu d’envoyer votre corpus biométrique vers une plateforme tierce. Elle permet de constituer un corpus local, de comparer une image à ce corpus et de consulter des résultats de similarité depuis une console web claire.

Cette page est écrite pour être comprise même si vous ne développez pas. Vous pouvez suivre le parcours « démarrage guidé » sans avoir besoin de connaître Python, React ou l’IA.

| Vous voulez… | Commencez ici |
|---|---|
| Installer FaceLens sur votre ordinateur | [Démarrage guidé](#démarrage-guidé--la-voie-la-plus-simple) |
| Comprendre ce que l’outil fait réellement | [Ce que FaceLens fait](#ce-que-facelens-fait--et-ne-fait-pas) |
| Protéger l’accès à votre instance | [Configuration sûre](#configuration-sûre) |
| Utiliser l’application au quotidien | [Votre premier parcours](#votre-premier-parcours-dans-la-console) |
| Dépanner une installation | [Dépannage](#dépannage) |
| Contribuer au projet | [Pour les contributeurs](#pour-les-contributeurs) |

---

## Avant de commencer : un engagement simple

FaceLens traite des **données biométriques**, donc des données particulièrement sensibles. Avant chaque import ou recherche, assurez-vous d’avoir une base légale, une finalité légitime et le droit d’utiliser les images. Ne l’utilisez jamais pour suivre, harceler, discriminer ou identifier une personne sans son consentement ou sans autorisation applicable.

> **Règle pratique :** si vous ne pourriez pas expliquer calmement à la personne concernée pourquoi son image est utilisée et comment elle peut demander sa suppression, ne lancez pas la recherche.

L’application est conçue pour rester locale. Le dépôt ne contient ni corpus, ni images indexées, ni base SQLite, ni index vectoriel, ni clé secrète. Ces données restent dans votre répertoire `data/` et ne doivent jamais être publiées dans Git.

---

## Ce que FaceLens fait — et ne fait pas

FaceLens transforme un visage présent dans une image en une **empreinte mathématique locale**, puis cherche les empreintes les plus proches dans votre corpus. Le résultat est un score de similarité et non une identité certaine.

| FaceLens peut vous aider à… | FaceLens ne peut pas… |
|---|---|
| Comparer une image avec les visages que vous avez autorisés à indexer. | Confirmer l’identité civile, l’âge, l’origine, l’état de santé ou les intentions d’une personne. |
| Vérifier si deux images semblent représenter le même visage. | Remplacer une vérification humaine, documentaire ou contextuelle. |
| Organiser un corpus local et supprimer les entrées lorsqu’elles ne sont plus nécessaires. | Chercher librement dans « tout Internet » ou accéder à des bases privées. |
| Collecter des images sur des pages publiques dans le respect des règles techniques appliquées par l’application. | Contourner des contrôles d’accès, des restrictions de sites ou une interdiction exprimée dans `robots.txt`. |

### Les grandes fonctions, en langage courant

| Fonction | Explication simple |
|---|---|
| **Recherche dans le corpus** | Vous déposez une photo. FaceLens vous montre les entrées locales qui lui ressemblent le plus. |
| **Comparaison de deux photos** | Vous fournissez deux images et obtenez une indication de ressemblance. |
| **Corpus** | C’est votre classeur local : les portraits, leurs noms facultatifs et leurs sources. |
| **Collecte de pages publiques** | FaceLens peut analyser une page publique autorisée et proposer des images à examiner avant indexation. |
| **Suppression** | Vous pouvez retirer un visage du corpus pour appliquer une demande d’effacement ou corriger une erreur. |
| **Journal local** | L’application conserve les éléments nécessaires au suivi local des opérations. |

---

## Démarrage guidé — la voie la plus simple

La méthode recommandée utilise **Docker Desktop** : c’est une application qui lance FaceLens dans une boîte isolée, avec les réglages nécessaires. Elle évite d’installer manuellement les bibliothèques techniques.

### Ce dont vous avez besoin

Préparez un ordinateur avec au moins 8 Go de mémoire vive disponible et de l’espace disque pour les modèles et votre corpus. Installez [Docker Desktop](https://www.docker.com/products/docker-desktop/) puis vérifiez qu’il est ouvert avant de continuer. Sur Linux, Docker Engine et le module Compose sont nécessaires.

Téléchargez ce dépôt, soit avec le bouton **Code → Download ZIP** sur GitHub, soit avec la commande suivante si vous êtes à l’aise avec un terminal :

```bash
git clone https://github.com/eulogep/FaceLens-Moteur-de-Recherche-Biom-trique-Local-Module-de-Scraping.git
cd FaceLens-Moteur-de-Recherche-Biom-trique-Local-Module-de-Scraping
```

### Étape 1 — créer votre configuration privée

Copiez le modèle fourni. Le fichier `.env` reste sur votre machine : il ne doit pas être envoyé par courriel, publié ou ajouté à Git.

```bash
cp .env.example .env
```

Ouvrez ensuite `.env` dans un éditeur de texte et remplacez les deux valeurs de clé par **la même valeur longue, aléatoire et unique**. Vous pouvez en générer une avec :

```bash
openssl rand -hex 32
```

Collez le résultat à la fois dans `FACELENS_API_KEY` et dans `VITE_FACELENS_API_KEY`. La première protège l’API. La seconde permet uniquement à la console web locale de communiquer avec cette API. Ne rendez pas cette console accessible publiquement.

> **Important :** ne conservez jamais les valeurs d’exemple du fichier `.env.example`. Chaque installation doit posséder sa propre clé.

### Étape 2 — démarrer l’application

Depuis le dossier du projet, lancez :

```bash
docker compose up --build -d
```

La première exécution peut prendre quelques minutes : Docker télécharge les composants nécessaires et FaceLens prépare son environnement local. Pour suivre ce qui se passe, utilisez :

```bash
docker compose logs -f facelens
```

Quand le démarrage est terminé, vérifiez que les services sont actifs :

```bash
docker compose ps
```

### Étape 3 — vérifier que FaceLens répond

La réponse de santé exige votre clé API. Dans le même terminal, lancez :

```bash
curl -H "X-FaceLens-API-Key: $FACELENS_API_KEY" http://localhost:8000/
```

Vous devez obtenir une réponse contenant `"status":"online"`. Les ports sont volontairement limités à votre ordinateur :

| Adresse | Rôle |
|---|---|
| `http://localhost:8000` | API FaceLens protégée par clé API. |
| `http://localhost:8080` | Service de recherche local SearXNG. |

Pour arrêter l’application sans effacer les données, utilisez :

```bash
docker compose down
```

---

## Configuration sûre

FaceLens démarre avec des protections destinées à limiter l’exposition de données sensibles. Le tableau suivant explique les réglages de `.env` sans jargon.

| Réglage | À quoi il sert | Conseil simple |
|---|---|---|
| `FACELENS_API_KEY` | Verrouille chaque appel à l’API. | Une valeur aléatoire d’au moins 32 caractères, différente pour chaque installation. |
| `VITE_FACELENS_API_KEY` | Permet à votre console web locale de présenter la même clé. | À utiliser seulement pour une interface locale, jamais sur un site public. |
| `CORS_ORIGINS` | Liste les adresses web autorisées à appeler l’API depuis un navigateur. | Ne gardez que les adresses réellement nécessaires, séparées par des virgules. |
| `MAX_IMAGE_UPLOAD_BYTES` | Limite la taille d’un fichier image envoyé. | La valeur par défaut correspond à 10 Mo. Réduisez-la si vous n’avez pas besoin de gros fichiers. |
| `MAX_IMAGE_PIXELS` | Limite la résolution d’une image pour éviter les fichiers pièges ou trop lourds. | Gardez la valeur par défaut sauf besoin justifié. |
| `MAX_REMOTE_IMAGE_BYTES` | Limite les images téléchargées depuis une page publique. | Gardez la valeur par défaut, surtout lors de collectes. |
| `STRICT_REMOTE_URL_VALIDATION` | Bloque les adresses locales, privées ou non HTTP lors des collectes distantes. | Laissez toujours `true` en utilisation normale. |

### Les gestes qui protègent votre corpus

Conservez le dossier `data/` sur un disque chiffré lorsque cela est possible. N’exposez pas les ports de FaceLens sur Internet, ne partagez pas le fichier `.env` et créez des sauvegardes chiffrées hors ligne. Si une personne demande l’effacement de son image, utilisez la suppression dans le corpus puis vérifiez que la sauvegarde est gérée conformément à votre politique de conservation.

---

## Votre premier parcours dans la console

Lorsque votre console web locale est disponible, commencez par un corpus très limité, avec des images pour lesquelles vous disposez des droits nécessaires. Prenez le temps d’observer chaque résultat au lieu de l’interpréter automatiquement.

### 1. Ajouter une entrée au corpus

Dans la section **Corpus**, choisissez une image, donnez éventuellement un libellé descriptif et indiquez la source lorsqu’elle est pertinente. Le libellé doit être factuel : par exemple « photo fournie pour test interne » plutôt qu’une affirmation non vérifiée sur l’identité de la personne.

### 2. Lancer une recherche

Dans **Recherche**, déposez une image autorisée. FaceLens calcule des scores de similarité par rapport au corpus local. Un score élevé mérite une vérification supplémentaire ; il ne constitue pas une conclusion.

### 3. Comparer deux images

Dans **Comparaison**, sélectionnez deux fichiers. Cette fonction est utile pour préparer une revue humaine, par exemple lorsqu’une personne vous a fourni deux images dans un cadre légitime.

### 4. Examiner, documenter, effacer

Notez les éléments de contexte utiles, vérifiez les sources, puis supprimez toute entrée qui n’a plus de finalité. Le bon résultat n’est pas celui qui paraît le plus impressionnant : c’est celui qui est interprété avec prudence et traçabilité.

---

## Collecter des images sur des pages publiques

La collecte est une fonction avancée. Elle n’est pas un moyen de contourner un site, de récolter des profils protégés ou de construire un corpus sans base légale. FaceLens applique des contrôles de sécurité sur les URL, les redirections, la taille des réponses et les règles `robots.txt`.

Avant une collecte, vérifiez manuellement que la page est publique, que son usage est autorisé et que la collecte est proportionnée. Les URL locales, privées ou dangereuses sont refusées. Les pages nécessitant un rendu JavaScript complexe ne sont pas traitées par le chemin distant sécurisé par défaut.

---

## Pour les personnes plus techniques

### Installer sans Docker

Si vous préférez une installation de développement, installez Python 3.11 ou ultérieur et Node.js 20 ou ultérieur. Créez d’abord un environnement Python isolé :

```bash
python -m venv .venv
source .venv/bin/activate  # Windows : .venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

Créez votre fichier `.env` comme indiqué plus haut, puis lancez l’API :

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Dans un second terminal, démarrez la console :

```bash
cd frontend
npm install
npm run dev
```

Le build de production de la console est vérifiable avec :

```bash
npm run typecheck
npm run build
npm run preview
```

### Appels API essentiels

Tous les appels nécessitent l’en-tête `X-FaceLens-API-Key`. Remplacez `$FACELENS_API_KEY` par votre variable d’environnement locale ; ne copiez pas une clé réelle dans la documentation, dans un ticket ou dans le code.

```bash
# Vérifier que le service est en ligne
curl -H "X-FaceLens-API-Key: $FACELENS_API_KEY" http://localhost:8000/

# Comparer deux images autorisées
curl -X POST "http://localhost:8000/api/faces/verify" \
  -H "X-FaceLens-API-Key: $FACELENS_API_KEY" \
  -F "image_a=@image-a.jpg" \
  -F "image_b=@image-b.jpg"
```

La documentation interactive de FastAPI est disponible localement via `/docs`, mais elle est elle aussi protégée par la clé API.

---

## Vérifier l’installation

Avant d’utiliser un corpus réel, effectuez une vérification simple avec des images de test autorisées. Le projet maintient plusieurs niveaux de contrôle :

| Vérification | Commande | Ce qu’elle contrôle |
|---|---|---|
| Tests backend | `FACELENS_API_KEY="…" pytest -q` | Authentification, CORS, validation d’image, contrôles d’URL et régressions API. |
| Audit Python | `pip-audit` | Vulnérabilités connues dans les dépendances Python installées. |
| Contrôle frontend | `cd frontend && npm run typecheck && npm run build` | Typage TypeScript et construction du bundle de production. |
| Santé production simulée | `curl -H "X-FaceLens-API-Key: $FACELENS_API_KEY" http://localhost:8000/` | Démarrage du serveur avec ses réglages de production. |

Les workflows GitHub Actions exécutent ces contrôles sur les contributions à la branche principale. Consultez les fichiers de [CI backend](.github/workflows/backend-ci.yml) et de [CI frontend](.github/workflows/frontend-ci.yml) pour le détail exact.

---

## Dépannage

| Situation | Explication probable | Première action |
|---|---|---|
| « 401 Unauthorized » | La clé API est absente ou différente. | Vérifiez l’en-tête `X-FaceLens-API-Key` et la valeur dans `.env`. |
| La console ne charge pas les données | L’API ne démarre pas ou son origine n’est pas autorisée. | Vérifiez `docker compose ps`, les logs et `CORS_ORIGINS`. |
| Docker indique que le port est déjà utilisé | Une autre application utilise le port local. | Fermez l’autre application ou choisissez un port local différent dans `.env`. |
| Une image est refusée | Le fichier peut être non image, trop lourd ou d’une résolution excessive. | Utilisez une image valide et vérifiez les limites dans `.env`. |
| Une URL de collecte est refusée | L’adresse est privée, redirige vers une cible non sûre ou la collecte n’est pas autorisée. | N’essayez pas de contourner le blocage ; choisissez une source publique et autorisée. |
| Le premier démarrage paraît long | Les modèles et dépendances peuvent être préparés au premier lancement. | Attendez les logs de démarrage et vérifiez votre espace disque. |

Pour redémarrer proprement les services sans supprimer vos données :

```bash
docker compose down
docker compose up --build -d
```

---

## Pour les contributeurs

Chaque contribution doit préserver trois principes : ne jamais versionner des données biométriques réelles, ne jamais ajouter de secret et ne jamais réduire les contrôles de sécurité au profit de la rapidité. Travaillez dans une branche dédiée, exécutez les tests concernés et ouvrez une pull request vers `main`.

```bash
FACELENS_API_KEY="test-key-for-local-validation-only" pytest -q
cd frontend && npm run typecheck && npm run build
```

Les changements qui touchent l’authentification, le stockage, les URL distantes, le scraping ou l’exposition réseau doivent inclure des tests de régression. Consultez aussi les modèles de configuration dans [`.env.example`](.env.example) et [`docker-compose.yml`](docker-compose.yml).

---

## Références

[1] [Docker Desktop — installation et documentation](https://www.docker.com/products/docker-desktop/)

[2] [FastAPI — documentation officielle](https://fastapi.tiangolo.com/)

[3] [InsightFace — projet et modèles](https://github.com/deepinsight/insightface)

[4] [GitHub Actions du projet](.github/workflows/)
