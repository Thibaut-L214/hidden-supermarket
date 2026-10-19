# DERRIÈRE LE RAYON

**DOCUMENT 01 — DIRECTION ARTISTIQUE**

Charte créative, esthétique et sensorielle pour une expérience documentaire immersive.

*Statut : proposition de production — non validée par L214.*

Périmètre commun : supermarché FPS → scan d’un rayon → ouverture double → terrasse en hauteur → exploitation → transport → transformation/abattage suggérés → retour au magasin → sortie et ressources L214.

## 01 — Intention et principes

Créer une expérience documentaire et interactive qui déplace le regard : du produit ordinaire, facilement identifiable, vers les systèmes d’élevage, de transport et de transformation qu’il rend invisibles. Le joueur n’est ni juge ni combattant : il observe, relie et comprend.

- Émotion recherchée : curiosité → surprise → compréhension → réflexion → capacité d’agir.
- Interdit créatif : gore, blessures explicites, souffrance spectaculaire, jump scares, caricature des personnes ou de leurs métiers.
- Exigence de justesse : séparer scènes symboliques, faits documentés et cas particuliers ; signaler les simplifications de la filière.
- Tonalité : grave mais accessible, sans culpabilisation directe du joueur ni infantilisation.
## 02 — Concept visuel : deux réalités

### A. Le supermarché / surface

Architecture reconnaissable, hauteurs crédibles, rayons construits en modules cohérents. Sol clair légèrement satiné ; éclairage large uniforme ; signalétique sobre et fictive ; produits stylisés mais identifiables. Aucun emballage imitant une marque réelle sans autorisation.

### B. La terrasse / seuil

Espace architectural de transition immédiatement accessible après l’ouverture en deux vantaux du rayon. Garde-corps, zone de marche limitée, horizon et profondeur. Cadrage dominant permettant de suivre visuellement l’élevage, la route et l’usine. Le joueur reste observateur, jamais placé à l’intérieur des opérations d’abattage.

### C. Les bâtiments / sous la surface

Volumes industriels crédibles, matériaux industriels simplifiés, volumes répétitifs et planification spatiale lisible. Quand le toit s’efface, la coupe révèle une organisation réelle ou illustrée et légendée — pas une fantaisie montrée comme documentaire.

## 03 — Palette et colorimétrie

| Zone | Palette indicative | Traitement |
| --- | --- | --- |
| Magasin | ivoire, beige, vert doux | exposition haute, saturation modérée |
| Terrasse | béton clair, gris bleuté | contre-jour contrôlé, horizon brumeux |
| Élevage | gris chaud, ocre désaturé | ombres directionnelles, contraste local |
| Abattoir/usine | acier, ardoise, blanc froid | intérieur non explicite, géométrie lisible |
| Sortie L214 | lumière naturelle et tonalités humaines | retour progressif à la chaleur |

Référence de production : gérer la couleur dans Three.js avec une chaîne cohérente (textures sRGB pour la couleur, tone mapping et exposition explicites). Le rendu de Cycles ne se transfère pas tel quel par GLB.

## 04 — Formes, textures et lumière

- Supermarché : étagères répétées mais variées, surfaces propres, affichage commercial générique et lisible.
- Élevages : densité et répétition exprimées par de grandes masses et des unités régulières ; ne pas exagérer artificiellement les installations.
- Animaux : modèles stylisés crédibles, gestes sobres, animation discrète, pas de réactions anthropomorphiques.
- Lumière : éclairage statique précalculé si pertinent ; lumières dynamiques réservées au scan, aux portes et aux points d’attention.
- Textures : atlas réutilisables, détails via normal maps ; pas de surcharge de microdétails invisibles depuis la terrasse.
- Toit : dissociation en objet animé, levée verticale ou dissolution contrôlée ; disparition lisible en 2–4 secondes, sans effet magique gratuit.
## 05 — Signature des interactions et transitions

### Scanner

Outil lisible en premier plan, non militarisé ; rayon ciblé par contour discret ou motifs de lignes. Bip de confirmation court ; retour haptique uniquement si disponible. L’interface indique clairement le rayon sélectionné et l’action possible.

### Ouverture du rayon

Deux parties rigides pivotent autour de charnières latérales. La largeur doit permettre le passage du joueur ; laisser une collision cohérente et une marge de sécurité. Accompagner l’ouverture de sons mécaniques feutrés et d’une baisse légère de l’ambiance commerciale.

### Séquence extérieure

Un mouvement de caméra facultatif attire d’abord le regard vers l’exploitation ; le toit se retire puis le transport se déroule en trajet visible. Des repères graphiques discrets relient bâtiments et véhicules sans transformer le monde en interface de statistiques.

## 06 — Identités spécifiques des filières

| Rayon | Site observé | Signature de mise en scène |
| --- | --- | --- |
| Œufs | bâtiment de poules pondeuses en cages | volumes en série ; poules visibles une fois le toit levé ; chargement des poules ; collecte des œufs |
| Viande bovine | engraissement en bâtiment, abattoir et ateliers | bovins à pied dans les couloirs ; attente visible ; mise à mort hors champ ; transport frigorifique distinct |
| Volaille | élevage avicole et abattoir | régularité des groupes ; étapes de transport |
| Porc | bâtiments porcins et abattoir | cloisons, circulation, chaîne logistique |
| Poisson | site aquacole OU pêche, selon scénario | eau, bacs, réseau de transport adapté |

Ne pas imposer le même flux « animaux vivants → abattoir → camion de produits » à toutes les filières : les œufs nécessitent un centre de conditionnement, et la pêche maritime n’est pas un élevage. Les scénarios doivent respecter ces différences.

## 07 — Son et musique

- Magasin : ventilation discrète, musique d’ambiance non reconnaissable, pas de foule imposée.
- Transition : le bip du scanner fait glisser l’environnement sonore vers des basses mécaniques.
- Terrasse : vent, ambiance distante, sons localisés correspondant aux objets réellement visibles.
- Chaîne logistique : bruit du moteur proportionné, aucune simulation réaliste de cris traumatisants.
- Sortie : sonore plus doux et humain ; limiter les contrastes brusques ; activer sous-titres et réglages audio.
## 08 — Accessibilité et confort

- Sous-titres et textes alternatifs aux informations audio ; contraste suffisant ; typographie minimale lisible.
- Réglages : sensibilité souris, vitesse de déplacement, volume, qualité graphique, réduction des mouvements, désactivation du flou.
- Pas de secousses caméra forcées ; éviter les flashs ; verrouillage du pointeur annoncé et sortie possible via Échap.
- Privilégier l’accès clavier/souris au prototype ; alternative tactile ou mode guidé à décider pour mobile.
## 09 — Livrables artistiques et validation

- Moodboard par zone, charte palette/matériaux, sheet de bâtiments, références audio, liste d’assets et storyboard de l’ouverture.
- Tests comparatifs : coupe de toit opaque vs dissolution ; réalisme stylisé vs rendu plus abstrait ; lisibilité depuis la terrasse.
- Validation éditoriale L214 et spécialistes des filières pour les scènes factuelles ; validation droits/logo/identité avant tout usage public.
Critère de réussite : un utilisateur comprend la transformation du rayon en parcours de production sans devoir lire un long bloc de texte.
