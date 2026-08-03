# FaceLens Console

Interface React/Vite de la console d'investigation FaceLens. L'application
s'ouvre directement sur la recherche faciale et utilise l'API locale FaceLens.

## Prérequis

- Node.js 20 ou version ultérieure
- API FaceLens accessible
- SearXNG accessible pour les workflows de collecte

## Installation

Depuis le dossier `frontend/` :

```bash
npm install
```

Pour une installation reproductible en CI :

```bash
npm ci
```

## Configuration

L'URL de l'API est configurable avec `VITE_API_URL`. Sans configuration,
la console utilise `http://localhost:8000`.

Exemple dans `frontend/.env.local` :

```env
VITE_API_URL=http://localhost:8000
```

Ne placez aucun secret dans une variable `VITE_*` : ces valeurs sont intégrées
au JavaScript livré au navigateur.

## Lancement en développement

```bash
npm run dev
```

Vite affiche l'URL locale, généralement `http://localhost:3000`.

## Vérification et build

Le build exécute d'abord le contrôle TypeScript, puis génère `frontend/dist/` :

```bash
npm run build
```

Pour prévisualiser le build :

```bash
npm run preview
```

## Responsive

- 1024 px et plus : console complète avec rail latéral.
- 768 px : navigation basse, panneaux empilés et tables défilables.
- Les animations respectent `prefers-reduced-motion`.

## Avertissement

La similarité faciale n'est pas une preuve d'identité. Vérifiez les sources
avant toute conclusion.
