// Juno crest — two modern laurel sprigs with bold, pointed geometric leaves.
// The wreath opens wide at the top (and parts at the base) so it reads as an
// emblem rather than a closed ring / loading spinner.

import type { SVGProps } from "react";

const CX = 50;
const CY = 50;
const R = 33;

export type Leaf = { x: number; y: number; angle: number; scale: number };

// dir: +1 branch sweeps clockwise (left side), -1 counter-clockwise (right side)
function branch(startDeg: number, endDeg: number, count: number): Leaf[] {
  const leaves: Leaf[] = [];
  for (let i = 0; i < count; i++) {
    const t = i / (count - 1);
    const deg = startDeg + t * (endDeg - startDeg);
    const a = (deg * Math.PI) / 180;
    leaves.push({
      x: CX + R * Math.cos(a),
      y: CY + R * Math.sin(a),
      angle: deg + 90,
      scale: 0.72 + 0.28 * Math.sin(t * Math.PI),
    });
  }
  return leaves;
}

// Left sprig: from just left of the base up to the upper-left (open top).
export const LEFT = branch(102, 214, 6);
// Right sprig mirrors: from just right of the base up to the upper-right.
export const RIGHT = branch(78, -34, 6);

function arcPath(startDeg: number, endDeg: number, sweep: 0 | 1): string {
  const a0 = (startDeg * Math.PI) / 180;
  const a1 = (endDeg * Math.PI) / 180;
  const x0 = (CX + R * Math.cos(a0)).toFixed(1);
  const y0 = (CY + R * Math.sin(a0)).toFixed(1);
  const x1 = (CX + R * Math.cos(a1)).toFixed(1);
  const y1 = (CY + R * Math.sin(a1)).toFixed(1);
  return `M${x0} ${y0} A ${R} ${R} 0 0 ${sweep} ${x1} ${y1}`;
}

// The two stem arcs that tie each sprig together.
export const STEMS = [arcPath(102, 214, 0), arcPath(78, -34, 1)];

// A single pointed geometric leaf, drawn pointing "up" from the origin.
export const LEAF_PATH = "M0 -9 C3.4 -3.6 3.4 3 0 5.4 C-3.4 3 -3.4 -3.6 0 -9 Z";

function Leaf({ leaf }: { leaf: Leaf }) {
  return (
    <path
      d={LEAF_PATH}
      fill="currentColor"
      transform={`translate(${leaf.x.toFixed(1)} ${leaf.y.toFixed(1)}) rotate(${leaf.angle.toFixed(
        1,
      )}) scale(${leaf.scale.toFixed(2)})`}
    />
  );
}

export function LaurelWreath({ className, ...rest }: SVGProps<SVGSVGElement>) {
  return (
    <svg
      viewBox="0 0 100 100"
      className={className}
      fill="none"
      aria-hidden
      {...rest}
    >
      {/* subtle stems that tie each sprig together */}
      {STEMS.map((d, i) => (
        <path key={i} d={d} stroke="currentColor" strokeWidth={1.4} opacity={0.45} />
      ))}

      {[...LEFT, ...RIGHT].map((leaf, i) => (
        <Leaf key={i} leaf={leaf} />
      ))}
    </svg>
  );
}

export default LaurelWreath;
