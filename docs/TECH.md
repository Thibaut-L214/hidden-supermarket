# DERRIÈRE LE RAYON

**DOCUMENT 03 — ARCHITECTURE TECHNIQUE**

Pipeline Blender → glTF/GLB → Three.js, contrats logiciels et backlog de développement Claude Code.

*Statut : proposition de production — non validée par L214.*

Périmètre commun : supermarché FPS → scan d’un rayon → ouverture double → terrasse en hauteur → exploitation → transport → transformation/abattage suggérés → retour au magasin → sortie et ressources L214.

## 01 — Décisions d’architecture

Application web avec TypeScript, Vite et Three.js, scène FPS pilotée par machine à états. Blender est l’outil auteur des maillages, UV, caméras de cadrage et animations rigides ; Claude Code accélère le code et les outils de génération, mais les résultats artistiques et documentaires restent validés humainement.

- Trois environnements logiques : magasin toujours actif ; module de filière chargé à la demande ; parvis de sortie.
- Chaque rayon partage une interface commune, mais définit sa propre chronologie pédagogique.
- GLB pour les géométries, matériaux PBR et animations compatibles ; JSON/TS pour narration, points d’intérêt, timings et sources.
- Le navigateur reste propriétaire de la caméra FPS, des collisions, de l’UI et des transitions ; pas de physique complexe pour les camions de la V1.
## 02 — Organisation du dépôt

/

CLAUDE.md

docs/{DA,GDD,TECH,CONTENT_SCHEMA}.md

blender/{store.blend,terrace_eggs.blend,export.py}

public/assets/{store/,eggs/,shared/,audio/}

src/app/{bootstrap.ts,store.ts}

src/core/{EventBus.ts,GameState.ts,AssetManager.ts}

src/world/{StoreWorld.ts,FPSController.ts,CollisionWorld.ts}

src/features/scanner/{Scanner.ts,ScanTarget.ts}

src/features/portal/{ShelfDoor.ts,TerraceTransition.ts}

src/features/chains/{ChainModule.ts,TimelineDirector.ts}

src/features/content/{ContentRegistry.ts}

src/features/exit/{ExitScene.ts}

src/ui/{HUD.ts,AccessibilityMenu.ts,SourcePanel.ts}

src/data/chains/{eggs.ts,chicken.ts,pork.ts,fish.ts}

tests/{state.test.ts,timeline.test.ts,assets.test.ts}

## 03 — Conventions Blender / GLB

| Élément | Nom prescrit | Rôle |
| --- | --- | --- |
| Racine du rayon | SHELF_EGGS_ROOT | pivot et zone du rayon |
| Portes | DOOR_EGGS_L / DOOR_EGGS_R | rotation locale |
| Pivot | HINGE_EGGS_L / HINGE_EGGS_R | origine des portes |
| Cible scanner | SCAN_EGGS | raycast sans collision |
| Seuil | TRIGGER_EGGS_ENTRY | passage vers terrasse |
| Terrasse | TERRACE_EGGS_ROOT | module indépendant |
| Toit | ROOF_EGGS | animation de levée / dissolution |
| Observation | ANCHOR_EGGS_VIEW | point de cadrage indicatif |
| Camions | TRUCK_EGGS_* | suivi de trajectoire |
| Sources | ANCHOR_EGGS_INFO_* | placement de cartels |

- Unité de travail : mètre. Origine, orientation, échelle et sens des axes documentés ; transform appliqué avant export.
- Pivot des vantaux placé aux charnières ; animation des portes rigides en Three.js ou dans Blender, jamais les deux en conflit.
- Découper sol/colliders simplifiés des modèles visuels. Exporter en GLB et valider la scène après chaque changement.
- Matériaux GLB : base color, metallic/roughness, normal, emissive ; toute fonctionnalité spécifique Blender/Cycles doit être bakée ou recréée.
- Éviter l’export d’animations nécessitant contraintes non bakées ; préférer les clips de transformation et chemins calculés en temps réel.
## 04 — Contrats logiciels

### Interface de module

Les filières disponibles et leurs identifiants figurent dans [le registre](../src/data/chains/index.ts) et [ChainId](../src/core/chain.ts). [ChainConfig et TimelineStep](../src/features/chains/ChainModule.ts) définissent les contenus, le contrat du modèle 3D et les événements de chaque parcours.

L’événement `walk` déplace des animaux entre deux groupes, via des points de passage au sol ou sur rampe. Les groupes conservent le même ordre et les origines des animaux se placent au niveau des sabots. Le moteur recalcule le départ après les déplacements précédents du camion, puis restaure positions et articulations au rejeu. La réduction des mouvements désactive l’animation des pattes tout en conservant le déplacement nécessaire à la compréhension du parcours.

### Règle de dépendances

Le moteur de timeline ne connaît que les interfaces de module ; chaque filière injecte ses objets et événements. Le système de scanner ne décide pas du contenu pédagogique. Un état global contrôle l’interruption et la reprise.

## 05 — Séquence et gestion des états

STORE -> SCANNING -> OPENING -> TERRACE

TERRACE -> REVEAL -> CHAIN -> RECAP

RECAP -> RETURN -> STORE

STORE -> EXIT -> END_MENU

ERROR -> SAFE_RETURN -> STORE

- Ouverture : attendre fin de chargement du module et disponibilité des collisions avant d’autoriser le passage.
- Conserver un objet session explorés = Set<ChainId> ; sessionStorage facultatif et activable uniquement selon politique de confidentialité.
- Émission d’événements typés (SCAN_CONFIRMED, DOORS_OPEN, TERRACE_ENTERED, ROOF_REVEALED, TIMELINE_DONE, RETURN_REQUESTED).
- En cas d’onglet inactif : suspendre horloge, audio et timeline ; reprendre sans saut temporel.
- Replay : réinitialiser les transforms par rapport à un état de référence, pas d’accumulation de rotations/déplacements.
## 06 — Animation des transports

Prototyper une scène en diorama visible depuis la terrasse. Les camions empruntent des courbes 3D préétablies ; orientation dans le sens de la tangente. Chargement et déchargement sont des changements d’états scénarisés et des animations simples. Le trajet est volontairement compressé dans l’espace et dans le temps : afficher « représentation schématique ».

- Toit : translation/rotation ou uniform d’opacité avec solution de repli ; rendre le dessous et les détails intérieurs visibles.
- Camion animaux : utilisé uniquement pour les filières où le scénario vérifié l’exige ; pas pour le circuit principal des œufs.
- Scène abattoir : transformation par fermeture/ouverture du bâtiment ou changement de chargement hors champ ; aucun acte graphique.
- Timing de référence : portes 2,5 s ; toit 3 s ; chaîne 45 s (à ajuster aux tests).
## 07 — Performance et qualité web

| Budget initial indicatif | Desktop prototype | Adaptation |
| --- | --- | --- |
| Fluidité visée | 60 fps cible, p95 frame < 25 ms | viser 30 fps stable sur matériel plus faible |
| Ressources scènes | chargement différé + cache limité | décharger textures inactives |
| Textures | KTX2 / tailles contrôlées | LOD et atlas |
| Géométrie | instancing pour objets répétés | LOD et occlusion sélective |
| Effets | bloom parcimonieux | désactivables en qualité basse |

Ces chiffres sont des cibles de prototype, non des garanties. Mesurer JS heap, draw calls, triangles, temps de chargement, FPS et absence de crash sur les appareils réellement visés. Éviter de garder quatre exploitations simultanément en GPU.

- Configurer renderer outputColorSpace, toneMapping et exposition explicitement ; vérifier toutes les textures de couleur.
- Éviter les ombres dynamiques massives sur chaque animal. Préférer géométries instanciées et lightmaps pour scènes statiques.
- Tester Chrome, Firefox, Safari sur ordinateur ; décider du support mobile après test de performance et ergonomie.
## 08 — Contenus, sources et sécurité

- Chaque cartel possède id, titre, texte court, texte détaillé, référence, date de consultation, échelle géographique et statut de validation.
- Aucun chiffre inventé par Claude Code. Données inconnues stockées comme TODO_SOURCE, bloquantes à la publication.
- Séparer illustrations schématiques et affirmations de terrain ; validation éditoriale et juridique requise.
- Liens vers L214 uniquement depuis domaines officiels confirmés ; ouverture externe via interaction explicite ; ne jamais demander les données de paiement dans l’expérience.
- Limiter la collecte de données. Aucune analytique nominative par défaut ; conformité RGPD à examiner avant diffusion.
- Utiliser les textes alternatifs, un mode sans audio, contrôle clavier et réglage de mouvement.
## 09 — Plan d’implémentation avec Claude Code

1. Sprint 0 : initialiser Vite + TypeScript + Three.js, lint/tests et CLAUDE.md ; charger le magasin placeholder.
2. Sprint 1 : FPS, collisions simples, réticule, scanner et tests de ciblage.
3. Sprint 2 : pivots du rayon, ouverture double, zone d’entrée, retour sans blocage.
4. Sprint 3 : terrasse modulaire, bâtiment et toit animé avec placeholders.
5. Sprint 4 : timeline de la filière œufs, camion des produits, légendes et rejouabilité.
6. Sprint 5 : intégration GLB Blender définitifs, matériaux, audio, optimisations.
7. Sprint 6 : sortie parvis, interface de ressources, accessibilité, tests utilisateur et validation éditoriale.
### Definition of done technique

Démarrage sans erreurs console ; rayon œufs jouable sans assets manquants ; retour depuis tous les états ; replay déterministe ; absence de collision piégeante ; tests automatiques de la machine à états ; mesures de performance documentées ; aucune source TODO au build de publication.

## 10 — Instructions de démarrage à copier dans CLAUDE.md

# Rôle

Tu es lead développeur Three.js/TypeScript et intégrateur Blender GLB.

# Source de vérité

Respecte docs/DA.md, docs/GDD.md et docs/TECH.md.

# Contraintes

Ne fabrique pas de faits sur les filières animales.

Utilise des placeholders explicites si données/assets manquent.

Construis une scène verticale « eggs » avant d’élargir.

Maintiens un état déterministe et des tests de retour/replay.

Ne supprime pas les réglages d’accessibilité.

# Méthode

1. Propose un plan de fichiers limité pour la tâche.

2. Implémente une tranche testable.

3. Exécute les tests disponibles.

4. Liste fichiers modifiés et éventuelles décisions ouvertes.

### Premier prompt de travail

« Initialise un prototype Three.js/TypeScript/Vite de Derrière le rayon, avec primitives temporaires. Implémente le magasin FPS, un rayon Œufs scannable, deux vantaux qui s’ouvrent, une terrasse accessible, un bâtiment à toit amovible, une timeline schématique de collecte/conditionnement/livraison d’œufs, le retour au magasin et une sortie L214 fictive. Sépare les données de filière du code, écris les tests d’états et n’invente aucun chiffre. »

## 11 — Sources techniques de référence

- Three.js GLTFLoader : https://threejs.org/docs/pages/GLTFLoader.html
- Blender glTF I/O actuel (Khronos) : https://github.com/KhronosGroup/glTF-Blender-IO/blob/main/docs/blender_docs/scene_gltf2.rst
- Site officiel L214, à confirmer pour les parcours éditoriaux et dons : https://www.l214.com/
Les hyperliens finaux, la marque, les chiffres et les représentations d’élevage devront être revus lors de la phase de validation. Ce document n’atteste pas d’un partenariat officiel.
