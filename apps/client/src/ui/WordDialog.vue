<script setup lang="ts">
// A word opened from a list: a window over the page (the same on Windows and Android).
// Closes with its button, the Escape key or a click outside it.
import { onBeforeUnmount, onMounted, ref } from "vue";

const emit = defineEmits<{ close: [] }>();
const box = ref<HTMLElement | null>(null);

function onKey(e: KeyboardEvent): void {
  if (e.key === "Escape") emit("close");
}

onMounted(() => {
  document.addEventListener("keydown", onKey);
  document.body.style.overflow = "hidden";
  box.value?.focus();
});
onBeforeUnmount(() => {
  document.removeEventListener("keydown", onKey);
  document.body.style.overflow = "";
});
</script>

<template>
  <Teleport to="body">
    <div class="backdrop" @click.self="emit('close')">
      <div ref="box" class="dialog" role="dialog" aria-modal="true" tabindex="-1">
        <slot />
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.backdrop {
  position: fixed;
  inset: 0;
  z-index: 100;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding: 4vh 1rem;
  background: rgb(0 0 0 / 0.45);
  overflow-y: auto;
}
.dialog {
  width: min(820px, 100%);
  outline: none;
}
.dialog :deep(.card) {
  box-shadow: 0 12px 40px rgb(0 0 0 / 0.25);
}
@media (max-width: 600px) {
  .backdrop {
    padding: 0;
    align-items: stretch;
  }
  .dialog {
    min-height: 100%;
  }
  .dialog :deep(.card) {
    min-height: 100%;
    border-radius: 0;
  }
}
</style>
