# FaceLens Console

Console locale d'investigation faciale construite avec Vite, React 18,
TypeScript et du CSS natif. Aucune bibliothèque d'interface ou d'animation
n'est requise.

## Structure

- `src/api/` : client HTTP et types d'échange avec FaceLens.
- `src/components/` : composants réutilisables (rail, cartes, jauges,
  dropzones, scan et notifications).
- `src/screens/` : Recherche, Comparaison, Corpus, Scraping et Journal.
- `src/styles/` : tokens visuels, responsive et animations CSS.
- `dist/` : bundle de production généré, non édité manuellement.

## Prérequis et installation

Node.js 20 ou ultérieur est recommandé. Depuis `frontend/` :

```bash
npm install
```

## Configuration

En développement, Vite écoute sur `http://localhost:3000`. Son proxy
transmet `/api` et `/static` à `http://localhost:8000`.

Variables optionnelles dans `frontend/.env.local` :

```env
VITE_API_URL=http://localhost:8000
VITE_SEARXNG_URL=http://localhost:8080
```

`VITE_API_URL` cible l'API FaceLens et `VITE_SEARXNG_URL` l'instance
SearXNG. Ces valeurs sont publiques dans le bundle : aucun secret ne doit
être placé dans une variable `VITE_*`.

## Développement

```bash
npm run dev
```

L'API FaceLens doit être disponible sur le port 8000 pour utiliser les
écrans avec les données réelles.

## Build et prévisualisation

```bash
npm run build
npm run preview
```

Le build exécute le contrôle TypeScript avant de générer `dist/`. La
prévisualisation sert exactement ce bundle de production.

## Responsive et accessibilité

- 1440 px : console complète avec rail latéral.
- 768 px : navigation basse, corpus sur deux colonnes et dropzones pleine
  largeur.
- 375 px : navigation basse fixe, cartes empilées, modales plein écran,
  viewport de scan proportionnel et topbar simplifiée.
- Les zones tabulaires restent défilables sans élargir la page.
- `prefers-reduced-motion` réduit les transitions et animations.

## Avertissement légal

La similarité faciale n'est pas une preuve d'identité. Vérifiez les sources
avant toute conclusion.
