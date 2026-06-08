import { render, screen } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { LiveCanvas } from "./LiveCanvas";

interface MockCanvasProps {
  readonly children: ReactNode;
  readonly camera: {
    readonly position: readonly number[];
    readonly zoom: number;
  };
  readonly orthographic?: boolean;
}

interface MockLineProps {
  readonly points: readonly (readonly number[])[];
  readonly color: string;
  readonly lineWidth: number;
}

interface MockOrbitControlsProps {
  readonly enablePan: boolean;
  readonly enableRotate: boolean;
  readonly minZoom: number;
  readonly maxZoom: number;
}

const lineCalls = vi.hoisted((): MockLineProps[] => []);
const orbitCalls = vi.hoisted((): MockOrbitControlsProps[] => []);

vi.mock("@react-three/fiber", () => ({
  Canvas: ({ children, camera, orthographic }: MockCanvasProps) => (
    <div data-camera={JSON.stringify(camera)} data-orthographic={String(orthographic)} data-testid="canvas">
      {children}
    </div>
  )
}));

vi.mock("@react-three/drei", () => ({
  Line: (props: MockLineProps) => {
    lineCalls.push(props);
    return <div data-color={props.color} data-testid="line" />;
  },
  OrbitControls: (props: MockOrbitControlsProps) => {
    orbitCalls.push(props);
    return <div data-testid="orbit-controls" />;
  }
}));

describe("LiveCanvas", () => {
  beforeEach(() => {
    lineCalls.length = 0;
    orbitCalls.length = 0;
  });

  it("renders target and generated contours as separated overlay lines", () => {
    render(
      <LiveCanvas
        generated={[
          { x: -0.25, y: 0.1 },
          { x: 0.25, y: 0.2 }
        ]}
        target={[
          { x: -0.2, y: -0.1 },
          { x: 0.2, y: -0.15 }
        ]}
      />
    );

    expect(screen.getByTestId("canvas")).toHaveAttribute(
      "data-camera",
      JSON.stringify({ position: [0, 0, 2.1], zoom: 300 })
    );
    expect(screen.getByTestId("canvas")).toHaveAttribute("data-orthographic", "true");
    expect(screen.getByTestId("orbit-controls")).toBeInTheDocument();
    expect(orbitCalls).toEqual([{ enablePan: false, enableRotate: false, minZoom: 0.9, maxZoom: 4 }]);

    const targetLine = lineCalls.find((line) => line.color === "#2f4658");
    const generatedLine = lineCalls.find((line) => line.color === "#bf3f3f");
    expect(targetLine).toEqual({
      color: "#2f4658",
      lineWidth: 2,
      points: [
        [-0.2, -0.1, -0.02],
        [0.2, -0.15, -0.02]
      ]
    });
    expect(generatedLine).toEqual({
      color: "#bf3f3f",
      lineWidth: 3,
      points: [
        [-0.25, 0.1, 0.02],
        [0.25, 0.2, 0.02]
      ]
    });
  });

  it("does not render data contours until each contour has at least two points", () => {
    render(<LiveCanvas generated={[{ x: 0, y: 0 }]} target={[]} />);

    expect(lineCalls.map((line) => line.color)).toEqual(["#9aa9b2", "#d0d7dc", "#d0d7dc"]);
  });
});
