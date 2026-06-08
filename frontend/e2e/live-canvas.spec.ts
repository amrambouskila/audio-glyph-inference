import { encode } from "@msgpack/msgpack";
import { expect, test, type Page } from "@playwright/test";
import { PNG } from "pngjs";

interface PixelCounts {
  readonly red: number;
  readonly dark: number;
  readonly varied: number;
}

interface SocketFrames {
  readonly configuredBytes: number[];
  readonly scoreFrameBytes: readonly number[][];
}

const TARGET_CONTOUR = ellipsePoints(0.36, 0.24, 72);
const GENERATED_CONTOUR = ellipsePoints(0.24, 0.36, 72);

test("renders live target and generated geometry on a real R3F canvas", async ({ page }) => {
  await mockCatalog(page);
  await installMockLiveSocket(page, {
    configuredBytes: bytesFor({ type: "configured", candidate_id: "candidate-1", glyph_target_id: "glyph-1" }),
    scoreFrameBytes: Array.from({ length: 4 }, () =>
      bytesFor({
        type: "score",
        shape_distance: 0.125,
        contours: GENERATED_CONTOUR,
        target_contours: TARGET_CONTOUR
      })
    )
  });

  await page.goto("/");
  await expect(page.getByLabel("Candidate")).toHaveValue("candidate-1");
  await expect(page.getByLabel("Glyph target")).toHaveValue("glyph-1");
  await page.getByRole("button", { name: "Connect" }).click();
  await expect(page.getByText("STREAMING")).toBeVisible();
  await expect(page.getByText("0.12500")).toBeVisible();
  await expect(page.getByText("10.0 Hz")).toBeVisible();

  const canvas = page.locator('canvas[data-engine^="three.js"]');
  await expect(canvas).toBeVisible();
  const box = await canvas.boundingBox();
  expect(box?.width).toBeGreaterThan(300);
  expect(box?.height).toBeGreaterThan(300);

  await expect.poll(async () => minVisiblePixels(await canvas.screenshot()), { timeout: 10_000 }).toBeGreaterThan(50);
  const counts = pixelCounts(await canvas.screenshot());
  expect(counts.red).toBeGreaterThan(50);
  expect(counts.dark).toBeGreaterThan(50);
  expect(counts.varied).toBeGreaterThan(500);
});

async function mockCatalog(page: Page): Promise<void> {
  await page.route("**/api/datasets/glyphs?limit=500", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify([{ id: "glyph-1", letter: "\u05d0", glyph_form: "\u05d0", font_name: "StamAshkenazCLM.ttf", num_contours: 1 }])
    });
  });
  await page.route("**/api/experiments?status=completed&limit=50", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify([
        {
          id: "run-1",
          name: "browser-smoke",
          family: "lissajous",
          search_strategy: "grid",
          completed_at: "2026-06-04T00:00:00Z",
          best_candidate_id: "candidate-1"
        }
      ])
    });
  });
  await page.route("**/api/experiments/run-1", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        run: {
          id: "run-1",
          name: "browser-smoke",
          family: "lissajous",
          search_strategy: "grid",
          completed_at: "2026-06-04T00:00:00Z",
          best_candidate_id: "candidate-1"
        },
        best_candidate: {
          id: "candidate-1",
          family: "lissajous",
          mean_shape_distance: 0.125,
          lookup_ratio: 0.75
        },
        candidate_count: 1
      })
    });
  });
}

async function installMockLiveSocket(page: Page, frames: SocketFrames): Promise<void> {
  await page.addInitScript(({ configuredBytes, scoreFrameBytes }: SocketFrames) => {
    let nowMs = 100_000;
    Object.defineProperty(Date, "now", {
      configurable: true,
      value: () => {
        nowMs += 100;
        return nowMs;
      }
    });

    class MockWebSocket extends EventTarget {
      static readonly CONNECTING = 0;
      static readonly OPEN = 1;
      static readonly CLOSING = 2;
      static readonly CLOSED = 3;

      binaryType: BinaryType = "blob";
      readyState = MockWebSocket.CONNECTING;
      onopen: ((event: Event) => void) | null = null;
      onmessage: ((event: MessageEvent<ArrayBuffer>) => void) | null = null;
      onerror: ((event: Event) => void) | null = null;
      onclose: ((event: CloseEvent) => void) | null = null;
      readonly url: string;

      constructor(url: string | URL) {
        super();
        this.url = String(url);
        window.setTimeout(() => {
          this.readyState = MockWebSocket.OPEN;
          const event = new Event("open");
          this.onopen?.(event);
          this.dispatchEvent(event);
        }, 0);
      }

      send(data: string | ArrayBufferLike | Blob | ArrayBufferView): void {
        void data;
        window.setTimeout(() => {
          this.emitMessage(configuredBytes);
          scoreFrameBytes.forEach((scoreBytes) => this.emitMessage(scoreBytes));
        }, 0);
      }

      close(): void {
        this.readyState = MockWebSocket.CLOSED;
        const event = new CloseEvent("close");
        this.onclose?.(event);
        this.dispatchEvent(event);
      }

      private emitMessage(bytes: number[]): void {
        const buffer = new Uint8Array(bytes).buffer;
        const event = new MessageEvent<ArrayBuffer>("message", { data: buffer });
        this.onmessage?.(event);
        this.dispatchEvent(event);
      }
    }

    Object.defineProperty(window, "WebSocket", { configurable: true, value: MockWebSocket });
  }, frames);
}

function bytesFor(value: unknown): number[] {
  return Array.from(encode(value));
}

function ellipsePoints(rx: number, ry: number, size: number): number[][] {
  return Array.from({ length: size }, (_value, index) => {
    const angle = (2 * Math.PI * index) / (size - 1);
    return [rx * Math.cos(angle), ry * Math.sin(angle)];
  });
}

function pixelCounts(buffer: Buffer): PixelCounts {
  const png = PNG.sync.read(buffer);
  let red = 0;
  let dark = 0;
  let varied = 0;
  for (let offset = 0; offset < png.data.length; offset += 4) {
    const r = png.data[offset];
    const g = png.data[offset + 1];
    const b = png.data[offset + 2];
    if (r > 150 && g < 110 && b < 110) {
      red += 1;
    }
    if (r < 90 && g < 110 && b < 130) {
      dark += 1;
    }
    if (Math.abs(r - 246) + Math.abs(g - 247) + Math.abs(b - 248) > 30) {
      varied += 1;
    }
  }
  return { red, dark, varied };
}

function minVisiblePixels(buffer: Buffer): number {
  const counts = pixelCounts(buffer);
  return Math.min(counts.red, counts.dark);
}

