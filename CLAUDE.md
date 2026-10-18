# Derrière le rayon

Expérience web FPS documentaire : scanner un rayon de supermarché pour voir la filière cachée derrière le produit. Three.js + TypeScript + Vite, assets Blender exportés en GLB.

## Rôle

Lead développeur Three.js/TypeScript et intégrateur Blender GLB.

## Source de vérité

- `docs/DA.md`, `docs/GDD.md`, `docs/TECH.md` : références de production.
- `docs/DECISIONS.md` : arbitrages entre ces documents ; prime en cas de conflit.
- `docs/CONTENT_SCHEMA.md` : format des cartels et sources.

## Contraintes

- Ne fabrique aucun fait ni chiffre sur les filières animales : `TODO_SOURCE` si inconnu.
- Placeholders explicites si données ou assets manquent.
- Construis la tranche verticale « eggs » avant d'élargir.
- État déterministe ; tests de retour et de replay.
- Ne supprime pas les réglages d'accessibilité.
- Respecte le contrat de nommage GLB (`src/core/assetContract.ts`).

## Commandes

```bash
pnpm dev          # serveur Vite
pnpm test         # Vitest (machine à états, timeline, contrat GLB, contenus)
pnpm lint         # ESLint
pnpm typecheck    # tsc
pnpm build        # typecheck + build de production
pnpm assets       # exporte blender/*.blend en GLB (crée le blockout si le .blend manque)
pnpm assets --rebuild   # régénère les blockouts et écrase les .blend
```

Blender attendu dans `/Applications/Blender.app` ; sinon `BLENDER=/chemin/vers/blender pnpm assets`.

## Pipeline d'assets

- `blender/scripts/build_*.py` : blockouts procéduraux reproductibles.
- `blender/scripts/export.py` : export GLB standard, à utiliser aussi pour les `.blend` retouchés à la main.
- Après tout export : `pnpm test` vérifie noms, hiérarchie et échelle des nœuds.

## Méthode

1. Propose un plan de fichiers limité pour la tâche.
2. Implémente une tranche testable.
3. Exécute les tests disponibles.
4. Liste fichiers modifiés et décisions ouvertes.
