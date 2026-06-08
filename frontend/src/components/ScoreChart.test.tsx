import { render } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { ScoreChart } from "./ScoreChart";

interface ChartDataset {
  readonly label: string;
  readonly data: readonly number[];
  readonly borderColor?: string;
  readonly backgroundColor?: string;
  readonly pointRadius?: number;
  readonly borderWidth: number;
  readonly tension?: number;
}

interface ChartData {
  readonly labels: readonly string[];
  readonly datasets: readonly ChartDataset[];
}

interface ChartScaleOptions {
  readonly display?: boolean;
  readonly min?: number;
  readonly suggestedMax?: number;
  readonly ticks?: {
    readonly maxRotation: number;
    readonly autoSkip: boolean;
  };
}

interface ChartOptions {
  readonly animation: boolean;
  readonly responsive: boolean;
  readonly maintainAspectRatio: boolean;
  readonly scales: {
    readonly x: ChartScaleOptions;
    readonly y: ChartScaleOptions;
  };
  readonly plugins: {
    readonly tooltip: {
      readonly enabled: boolean;
    };
  };
}

interface ChartProps {
  readonly data: ChartData;
  readonly options: ChartOptions;
}

const lineCalls = vi.hoisted((): ChartProps[] => []);
const barCalls = vi.hoisted((): ChartProps[] => []);

vi.mock("react-chartjs-2", () => ({
  Line: (props: ChartProps) => {
    lineCalls.push(props);
    return <div data-testid="line-chart" />;
  },
  Bar: (props: ChartProps) => {
    barCalls.push(props);
    return <div data-testid="bar-chart" />;
  }
}));

describe("ScoreChart", () => {
  beforeEach(() => {
    lineCalls.length = 0;
    barCalls.length = 0;
  });

  it("renders score history and latest per-letter distances into chart datasets", () => {
    render(
      <ScoreChart
        history={[
          { atMs: 100001, distance: 0.5, letter: "bet" },
          { atMs: 100120, distance: 0.3, letter: "aleph" },
          { atMs: 100240, distance: 0.2, letter: "bet" }
        ]}
      />
    );

    expect(lineCalls).toHaveLength(1);
    expect(lineCalls[0].data).toEqual({
      labels: ["1", "120", "240"],
      datasets: [
        {
          label: "shape distance",
          data: [0.5, 0.3, 0.2],
          borderColor: "#bf3f3f",
          backgroundColor: "#bf3f3f",
          pointRadius: 0,
          borderWidth: 2,
          tension: 0.2
        }
      ]
    });
    expect(lineCalls[0].options).toMatchObject({
      animation: false,
      responsive: true,
      maintainAspectRatio: false,
      scales: { x: { display: false }, y: { min: 0, suggestedMax: 1 } },
      plugins: { tooltip: { enabled: true } }
    });

    expect(barCalls).toHaveLength(1);
    expect(barCalls[0].data).toEqual({
      labels: ["aleph", "bet"],
      datasets: [
        {
          label: "latest by letter",
          data: [0.3, 0.2],
          backgroundColor: "#2f6f8f",
          borderWidth: 0
        }
      ]
    });
    expect(barCalls[0].options).toMatchObject({
      animation: false,
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        x: { ticks: { maxRotation: 0, autoSkip: true } },
        y: { min: 0, suggestedMax: 1 }
      },
      plugins: { tooltip: { enabled: true } }
    });
  });

  it("keeps stable empty chart datasets when no score history exists", () => {
    render(<ScoreChart history={[]} />);

    expect(lineCalls[0].data.labels).toEqual([]);
    expect(lineCalls[0].data.datasets[0].data).toEqual([]);
    expect(barCalls[0].data.labels).toEqual([]);
    expect(barCalls[0].data.datasets[0].data).toEqual([]);
  });
});
