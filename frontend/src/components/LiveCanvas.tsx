import { Line, OrbitControls } from "@react-three/drei";
import { Canvas } from "@react-three/fiber";
import { useMemo } from "react";
import type { Point2D } from "../types/live";

interface LiveCanvasProps {
  readonly generated: readonly Point2D[];
  readonly target: readonly Point2D[];
}

const UNIT_FRAME_POINTS = [
  [-0.5, -0.5, 0],
  [0.5, -0.5, 0],
  [0.5, 0.5, 0],
  [-0.5, 0.5, 0],
  [-0.5, -0.5, 0]
] as const;

const HORIZONTAL_AXIS_POINTS = [
  [-0.55, 0, 0.005],
  [0.55, 0, 0.005]
] as const;

const VERTICAL_AXIS_POINTS = [
  [0, -0.55, 0.005],
  [0, 0.55, 0.005]
] as const;

export function LiveCanvas({ generated, target }: LiveCanvasProps): JSX.Element {
  const generatedPoints = useMemo(() => generated.map((point) => [point.x, point.y, 0.02] as const), [generated]);
  const targetPoints = useMemo(() => target.map((point) => [point.x, point.y, -0.02] as const), [target]);

  return (
    <div className="canvas-shell">
      <Canvas camera={{ position: [0, 0, 2.1], zoom: 300 }} orthographic>
        <color attach="background" args={["#f6f7f8"]} />
        <ambientLight intensity={1.4} />
        <gridHelper args={[1.2, 12, "#cfd6dc", "#e4e8ec"]} rotation={[Math.PI / 2, 0, 0]} />
        <Line points={UNIT_FRAME_POINTS} color="#9aa9b2" lineWidth={1.5} />
        <Line points={HORIZONTAL_AXIS_POINTS} color="#d0d7dc" lineWidth={1} />
        <Line points={VERTICAL_AXIS_POINTS} color="#d0d7dc" lineWidth={1} />
        {targetPoints.length > 1 ? <Line points={targetPoints} color="#2f4658" lineWidth={2} /> : null}
        {generatedPoints.length > 1 ? <Line points={generatedPoints} color="#bf3f3f" lineWidth={3} /> : null}
        <OrbitControls enablePan={false} enableRotate={false} minZoom={0.9} maxZoom={4} />
      </Canvas>
    </div>
  );
}
