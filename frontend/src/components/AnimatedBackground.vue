<template>
  <div class="bg-root" aria-hidden="true">
    <!-- Layer 0: Solid base -->
    <div class="bg-base" />

    <!-- Layer 1: Animated gradient -->
    <div class="bg-gradient" />

    <!-- Layer 2: Floating light fields -->
    <div class="bg-fields">
      <div class="field field-1" />
      <div class="field field-2" />
      <div class="field field-3" />
    </div>

    <!-- Layer 3: Subtle pattern overlay -->
    <div class="bg-grid" />
    <div class="bg-noise" />
  </div>
</template>

<style scoped>
.bg-root {
  position: fixed;
  inset: 0;
  z-index: -50;
  pointer-events: none;
  overflow: hidden;
}

/* Solid base */
.bg-base {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(circle at 18% 12%, rgba(255,255,255,0.9), transparent 28%),
    radial-gradient(circle at 82% 6%, rgba(147,197,253,0.24), transparent 28%),
    var(--color-bg);
  transition: background-color 0.6s ease;
}

/* Animated gradient layer */
.bg-gradient {
  position: absolute;
  inset: -50%;
  opacity: 0.42;
  background: linear-gradient(
    120deg,
    #ccfbf1,
    #e0f2fe,
    #fff7ed,
    #fdf2f8,
    #ccfbf1
  );
  background-size: 400% 400%;
  animation: gradientMove 28s ease infinite;
  transition: opacity 0.6s ease;
}

[data-theme="dark"] .bg-gradient {
  opacity: 0.2;
  background: linear-gradient(
    120deg,
    #042f2e,
    #071313,
    #172554,
    #2e1065,
    #071313
  );
  background-size: 400% 400%;
}

/* Floating light fields */
.bg-fields {
  position: absolute;
  inset: 0;
}

.field {
  position: absolute;
  border-radius: 999px;
  filter: blur(72px);
  opacity: 0.34;
  transition: opacity 0.6s ease;
}

.field-1 {
  width: 42vw;
  height: 42vw;
  top: -14%;
  left: -9%;
  background: #54d6c7;
  animation: floatBlob1 20s ease-in-out infinite;
}

.field-2 {
  width: 34vw;
  height: 34vw;
  bottom: -14%;
  right: -7%;
  background: #93c5fd;
  animation: floatBlob2 25s ease-in-out infinite;
}

.field-3 {
  width: 26vw;
  height: 26vw;
  top: 38%;
  left: 48%;
  background: #fb7185;
  animation: floatBlob3 22s ease-in-out infinite;
}

[data-theme="dark"] .field {
  opacity: 0.15;
}

[data-theme="dark"] .field-1 { background: #14b8a6; }
[data-theme="dark"] .field-2 { background: #3b82f6; }
[data-theme="dark"] .field-3 { background: #8b5cf6; }

.bg-grid {
  position: absolute;
  inset: 0;
  opacity: 0.18;
  background-image:
    linear-gradient(rgba(15, 23, 42, 0.06) 1px, transparent 1px),
    linear-gradient(90deg, rgba(15, 23, 42, 0.06) 1px, transparent 1px);
  background-size: 64px 64px;
  mask-image: radial-gradient(circle at 50% 18%, black, transparent 72%);
}

[data-theme="dark"] .bg-grid {
  opacity: 0.12;
  background-image:
    linear-gradient(rgba(148, 211, 205, 0.12) 1px, transparent 1px),
    linear-gradient(90deg, rgba(148, 211, 205, 0.12) 1px, transparent 1px);
}

/* Noise texture overlay */
.bg-noise {
  position: absolute;
  inset: 0;
  opacity: 0.018;
  background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='0.5'/%3E%3C/svg%3E");
  background-size: 256px 256px;
}

@media (prefers-reduced-motion: reduce) {
  .bg-gradient, .field {
    animation: none !important;
  }
}
</style>
