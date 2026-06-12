import createGlobe, { type COBEOptions } from "cobe";
import { useMotionValue, useSpring } from "motion/react";
import { useLayoutEffect, useRef } from "react";

import { cn } from "@/lib/utils";

const MOVEMENT_DAMPING = 1400;

const GLOBE_CONFIG: COBEOptions = {
  width: 800,
  height: 800,
  phi: 0,
  theta: 0.3,
  devicePixelRatio: 2,
  dark: 0,
  diffuse: 0.4,
  mapSamples: 16000,
  mapBrightness: 1.2,
  baseColor: [1, 1, 1],
  markerColor: [1, 1, 1],
  glowColor: [1, 1, 1],
  markers: [],
};

export function Globe({
  className,
  config = GLOBE_CONFIG,
}: {
  className?: string;
  config?: COBEOptions;
}) {
  const wrapperRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const phiRef = useRef(0);
  const widthRef = useRef(0);
  const pointerInteracting = useRef<number | null>(null);
  const rafRef = useRef<number>(0);

  const r = useMotionValue(0);
  const rs = useSpring(r, { mass: 1, damping: 30, stiffness: 100 });

  const updatePointerInteraction = (value: number | null) => {
    pointerInteracting.current = value;
    if (canvasRef.current) {
      canvasRef.current.style.cursor = value !== null ? "grabbing" : "grab";
    }
  };

  const updateMovement = (clientX: number) => {
    if (pointerInteracting.current !== null) {
      const delta = clientX - pointerInteracting.current;
      r.set(r.get() + delta / MOVEMENT_DAMPING);
    }
  };

  useLayoutEffect(() => {
    const wrapper = wrapperRef.current;
    const canvas = canvasRef.current;
    if (!wrapper || !canvas) return;

    if (canvas.parentElement !== wrapper) {
      const stale = canvas.parentElement;
      wrapper.appendChild(canvas);
      stale?.remove();
    }

    const w = wrapper.offsetWidth;
    if (w === 0) return;
    widthRef.current = w;

    const globe = createGlobe(canvas, {
      ...config,
      width: w * 2,
      height: w * 2,
    });

    let running = true;
    const animate = () => {
      if (!running) return;
      if (!pointerInteracting.current) phiRef.current += 0.005;
      globe.update({
        phi: phiRef.current + rs.get(),
        width: widthRef.current * 2,
        height: widthRef.current * 2,
      });
      rafRef.current = requestAnimationFrame(animate);
    };
    rafRef.current = requestAnimationFrame(animate);
    canvas.style.opacity = "1";

    const observer = new ResizeObserver((entries) => {
      const rw = Math.floor(entries[0]?.contentRect.width ?? 0);
      if (rw > 0) {
        widthRef.current = rw;
        globe.update({ width: rw * 2, height: rw * 2 });
      }
    });
    observer.observe(wrapper);

    return () => {
      running = false;
      cancelAnimationFrame(rafRef.current);
      globe.destroy();
      observer.disconnect();
    };
  }, [rs, config]);

  return (
    <div
      ref={wrapperRef}
      className={cn(
        "absolute inset-0 mx-auto aspect-square w-full max-w-150",
        className,
      )}
    >
      <canvas
        className="size-full opacity-0 transition-opacity duration-500"
        ref={canvasRef}
        onPointerDown={(e) => updatePointerInteraction(e.clientX)}
        onPointerUp={() => updatePointerInteraction(null)}
        onPointerOut={() => updatePointerInteraction(null)}
        onMouseMove={(e) => updateMovement(e.clientX)}
        onTouchMove={(e) =>
          e.touches[0] && updateMovement(e.touches[0].clientX)
        }
      />
    </div>
  );
}
