# Derrière le rayon

Expérience web FPS documentaire : scanner un rayon de supermarché pour voir la filière cachée derrière le produit. Three.js + TypeScript + Vite, assets Blender exportés en GLB.

## Rôle

Lead développeur Three.js/TypeScript et intégrateur Blender GLB.

## Source de vérité

- `docs/DA.md`, `docs/GDD.md`, `docs/TECH.md` : références de production.
- `docs/DECISIONS.md` : arbitrages entre ces documents ; prime en cas de conflit.
- `docs/CONTENT_SCHEMA.md` : format des cartels et sources.
- `docs/PERFORMANCE.md` : méthode et derniers relevés.

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

Mesures : `http://localhost:5173/?perf` ou touche à gauche de `1` (voir `docs/PERFORMANCE.md`).

Blender attendu dans `/Applications/Blender.app` ; sinon `BLENDER=/chemin/vers/blender pnpm assets`.

## Pipeline d'assets

- `blender/scripts/build_*.py` : blockouts procéduraux reproductibles.
- `blender/scripts/export.py` : export GLB standard (vers `blender/out/`, hors dépôt), à utiliser aussi pour les `.blend` retouchés à la main.
- `scripts/optimize-glb.mjs` : compression meshopt vers `public/assets/` ; KTX2 nécessite KTX-Software (`toktx`).
- `blender/scripts/store_props.py` : mobilier et marchandises détaillés du magasin.
- `blender/scripts/terrace_props.py` : charpente, bardage, silos, quais, palettes, camions de la terrasse.
- `blender/scripts/landscape_props.py` : relief, champs, routes, végétation, clôture et ligne électrique.
- `blender/scripts/parvis_props.py` : façade, marquise, mobilier du parvis, stand et bénévoles.
- `blender/scripts/make_textures.py` : sets PBR tileables (`blender/textures/`) ; `surfaces.py` projette les UV à l'export, `lightmap.py` cuit l'éclairage (profils `store`, `terrace`), `bake_env.py` le panorama HDR du magasin.
- `blender/scripts/make_brand_textures.py` : tracts et banderole du parvis ; le logo officiel se dépose dans `blender/textures/brand/l214_logo.png`, sinon un mot-symbole de substitution est dessiné.
- `blender/scripts/build_scanner_hand.py` : main et terminal de scan en vue subjective (`public/assets/shared/`).
- Occlusion ambiante bakée à l'export (couleur de sommet `AO`) ; `pnpm assets --no-ao` pour itérer vite ; propriété `ao_skip` pour exclure un objet.
- `node scripts/inspect-glb.mjs <fichier.glb>` : triangles et sommets par nœud.
- Après tout export : `pnpm test` vérifie noms, hiérarchie et échelle des nœuds.

## Méthode

1. Propose un plan de fichiers limité pour la tâche.
2. Implémente une tranche testable.
3. Exécute les tests disponibles.
4. Liste fichiers modifiés et décisions ouvertes.
