<script setup lang="ts">
// A Go to page tile with its icon alone (display icon, catalogue/screen.yaml navigation), as the screen draws it: the icon
// in the largest circle the card holds up to a whole page's, in the middle of the card, in the face the glass gives it
// there (useTileCard iconAlone, tall_tile::icon_only). No name, line or chevron: the card says its name to a screen
// reader and in its title, and a click is the same as on the standard face.
import { glyph } from "../../model/topbar";
import type { TileCardView } from "../../composables/useTileCard";

const props = defineProps<{ card: TileCardView }>();
// The same card for as long as this face stands (useTileCard): read without going through the props each time.
const card = props.card;
</script>

<template>
  <span v-if="card.iconAlone" class="icon-alone" :style="card.iconAlone.box">
    <span class="ic mdi" :class="{ lit: card.lit }" :style="card.iconAlone.circle">{{ glyph(card.icon) }}</span>
  </span>
  <!-- A card the glass's sizes do not reach (another screen's on the overview): the icon in the middle all the same. -->
  <span v-else class="icon-alone loose"><span class="ic mdi" :class="{ lit: card.lit }">{{ glyph(card.icon) }}</span></span>
</template>

<style scoped src="./parts.css"></style>
<style scoped>
.icon-alone { position: absolute; }
.icon-alone .ic { position: absolute; display: grid; place-items: center; margin: 0; padding: 0; line-height: 1; }
.icon-alone.loose { inset: 0; display: grid; place-items: center; }
.icon-alone.loose .ic { position: static; width: 60%; aspect-ratio: 1; max-height: 80%; font-size: 1.9em; }
</style>
