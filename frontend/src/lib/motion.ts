import type { Variants } from "motion/react";

export const spring = { type: "spring", stiffness: 400, damping: 30 } as const;

export const fadeUp: Variants = {
  hidden: { opacity: 0, y: 16 },
  visible: { opacity: 1, y: 0, transition: spring },
  exit: { opacity: 0, y: -8, transition: { duration: 0.15 } },
};

export const slideRight: Variants = {
  hidden: { opacity: 0, x: "100%" },
  visible: { opacity: 1, x: 0, transition: spring },
  exit: { opacity: 0, x: "100%", transition: { duration: 0.2 } },
};

export const slideUp: Variants = {
  hidden: { opacity: 0, y: "100%" },
  visible: { opacity: 1, y: 0, transition: spring },
  exit: { opacity: 0, y: "100%", transition: { duration: 0.2 } },
};

export const staggerList: Variants = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.04, delayChildren: 0.05 } },
};

export const staggerItem: Variants = {
  hidden: { opacity: 0, y: 12 },
  visible: { opacity: 1, y: 0, transition: spring },
};
export default {
  spring,
  fadeUp,
  slideRight,
  slideUp,
  staggerList,
  staggerItem,
};
