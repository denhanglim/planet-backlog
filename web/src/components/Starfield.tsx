"use client";

import { Canvas, useFrame } from "@react-three/fiber";
import { useMemo, useRef, useState, useEffect } from "react";
import * as THREE from "three";

/**
 * WebGL starfield: two depth layers of points with slow drift + gentle pointer
 * parallax. Deterministic star positions (seeded LCG) so renders are stable.
 * Fully inert under prefers-reduced-motion (static single frame).
 */

function lcg(seed: number) {
  let s = seed >>> 0;
  return () => {
    s = (s * 1664525 + 1013904223) >>> 0;
    return s / 4294967296;
  };
}

let spriteCache: THREE.Texture | null = null;

/** Soft circular sprite so points render as stars, not squares. */
function starSprite(): THREE.Texture {
  if (spriteCache) return spriteCache;
  const c = document.createElement("canvas");
  c.width = c.height = 64;
  const ctx = c.getContext("2d")!;
  const g = ctx.createRadialGradient(32, 32, 0, 32, 32, 32);
  g.addColorStop(0, "rgba(255,255,255,1)");
  g.addColorStop(0.35, "rgba(255,255,255,0.7)");
  g.addColorStop(1, "rgba(255,255,255,0)");
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, 64, 64);
  spriteCache = new THREE.CanvasTexture(c);
  return spriteCache;
}

function StarLayer({
  count,
  radius,
  size,
  speed,
  seed,
  reduced,
}: {
  count: number;
  radius: number;
  size: number;
  speed: number;
  seed: number;
  reduced: boolean;
}) {
  const ref = useRef<THREE.Points>(null);
  const sprite = useMemo(() => starSprite(), []);
  const { positions, colors } = useMemo(() => {
    const rand = lcg(seed);
    const pos = new Float32Array(count * 3);
    const col = new Float32Array(count * 3);
    const phosphor = new THREE.Color("#5ef2c8");
    const white = new THREE.Color("#dfe8e3");
    const amber = new THREE.Color("#ffb24d");
    for (let i = 0; i < count; i++) {
      // uniform-ish shell distribution
      const r = radius * (0.5 + 0.5 * rand());
      const theta = rand() * Math.PI * 2;
      const phi = Math.acos(2 * rand() - 1);
      pos[i * 3] = r * Math.sin(phi) * Math.cos(theta);
      pos[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta) * 0.6;
      pos[i * 3 + 2] = r * Math.cos(phi);
      const roll = rand();
      const c = roll < 0.06 ? phosphor : roll < 0.09 ? amber : white;
      const dim = 0.35 + 0.65 * rand();
      col[i * 3] = c.r * dim;
      col[i * 3 + 1] = c.g * dim;
      col[i * 3 + 2] = c.b * dim;
    }
    return { positions: pos, colors: col };
  }, [count, radius, seed]);

  useFrame((state, delta) => {
    if (reduced || !ref.current) return;
    ref.current.rotation.y += delta * speed;
    const px = state.pointer.x * 0.04;
    const py = state.pointer.y * 0.04;
    ref.current.rotation.x += (py - ref.current.rotation.x) * 0.02;
    ref.current.rotation.z += (px - ref.current.rotation.z) * 0.02;
  });

  return (
    <points ref={ref} frustumCulled={false}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[positions, 3]} />
        <bufferAttribute attach="attributes-color" args={[colors, 3]} />
      </bufferGeometry>
      <pointsMaterial
        size={size}
        sizeAttenuation
        vertexColors
        transparent
        map={sprite}
        alphaTest={0.01}
        opacity={0.85}
        depthWrite={false}
        blending={THREE.AdditiveBlending}
      />
    </points>
  );
}

export function Starfield({ className = "" }: { className?: string }) {
  const [reduced, setReduced] = useState(false);
  const [visible, setVisible] = useState(true);
  const holder = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    setReduced(mq.matches);
    const onChange = (e: MediaQueryListEvent) => setReduced(e.matches);
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, []);

  useEffect(() => {
    if (!holder.current) return;
    const io = new IntersectionObserver(([e]) => setVisible(e.isIntersecting), {
      threshold: 0,
    });
    io.observe(holder.current);
    return () => io.disconnect();
  }, []);

  return (
    <div ref={holder} className={className} aria-hidden="true">
      <Canvas
        camera={{ position: [0, 0, 14], fov: 55 }}
        dpr={[1, 2]}
        frameloop={reduced || !visible ? "demand" : "always"}
        gl={{ antialias: false, powerPreference: "high-performance" }}
      >
        <StarLayer count={4200} radius={28} size={0.06} speed={0.008} seed={7} reduced={reduced} />
        <StarLayer count={2200} radius={14} size={0.11} speed={0.016} seed={31} reduced={reduced} />
      </Canvas>
    </div>
  );
}
