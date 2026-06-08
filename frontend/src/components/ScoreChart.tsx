import {
  BarElement,
  CategoryScale,
  Chart as ChartJS,
  LinearScale,
  LineElement,
  PointElement,
  Tooltip
} from "chart.js";
import { Bar, Line } from "react-chartjs-2";
import { latestDistanceByLetter, type ScoreSample } from "../utils/scoreHistory";

ChartJS.register(BarElement, CategoryScale, LinearScale, LineElement, PointElement, Tooltip);

interface ScoreChartProps {
  readonly history: readonly ScoreSample[];
}

export function ScoreChart({ history }: ScoreChartProps): JSX.Element {
  const latestByLetter = [...latestDistanceByLetter(history).entries()].sort(([left], [right]) =>
    left.localeCompare(right)
  );
  return (
    <div className="chart-shell">
      <div className="chart-pane">
        <Line
          data={{
            labels: history.map((sample) => `${Math.round(sample.atMs % 100000)}`),
            datasets: [
              {
                label: "shape distance",
                data: history.map((sample) => sample.distance),
                borderColor: "#bf3f3f",
                backgroundColor: "#bf3f3f",
                pointRadius: 0,
                borderWidth: 2,
                tension: 0.2
              }
            ]
          }}
          options={{
            animation: false,
            responsive: true,
            maintainAspectRatio: false,
            scales: {
              x: { display: false },
              y: { min: 0, suggestedMax: 1 }
            },
            plugins: {
              tooltip: { enabled: true }
            }
          }}
        />
      </div>
      <div className="chart-pane chart-pane-compact">
        <Bar
          data={{
            labels: latestByLetter.map(([letter]) => letter),
            datasets: [
              {
                label: "latest by letter",
                data: latestByLetter.map(([, distance]) => distance),
                backgroundColor: "#2f6f8f",
                borderWidth: 0
              }
            ]
          }}
          options={{
            animation: false,
            responsive: true,
            maintainAspectRatio: false,
            scales: {
              x: { ticks: { maxRotation: 0, autoSkip: true } },
              y: { min: 0, suggestedMax: 1 }
            },
            plugins: {
              tooltip: { enabled: true }
            }
          }}
        />
      </div>
    </div>
  );
}
