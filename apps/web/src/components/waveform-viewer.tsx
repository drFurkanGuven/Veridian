'use client';

import { useEffect, useMemo, useRef, useState } from 'react';

import {
  formatSignalValue,
  parseVcd,
  valueAtTime,
  type ParsedVcd,
  type VcdSignal,
} from '@/lib/vcd-parser';

const ROW_HEIGHT = 28;
const LABEL_WIDTH = 200;
const TIME_AXIS_HEIGHT = 28;
const MAX_SIGNALS = 64;
const COLORS = {
  high: '#4ade80',
  low: '#475569',
  unknown: '#facc15',
  grid: '#3c3c3c',
  text: '#cccccc',
  muted: '#858585',
  bus: '#38bdf8',
};

interface WaveformViewerProps {
  source: string;
  className?: string;
}

function isHigh(value: string): boolean {
  return value === '1' || (/^[01]+$/.test(value) && !/^0+$/.test(value));
}

function isUnknown(value: string): boolean {
  return /[xz]/i.test(value);
}

function drawSignalRow(
  ctx: CanvasRenderingContext2D,
  signal: VcdSignal,
  parsed: ParsedVcd,
  rowIndex: number,
  width: number,
  timeScale: number,
  offsetX: number,
): void {
  const y = TIME_AXIS_HEIGHT + rowIndex * ROW_HEIGHT;
  const series = parsed.transitions.get(signal.id) ?? [];
  const midY = y + ROW_HEIGHT / 2;
  const highY = y + 6;
  const lowY = y + ROW_HEIGHT - 6;

  ctx.fillStyle = COLORS.text;
  ctx.font = '11px JetBrains Mono, monospace';
  ctx.textAlign = 'left';
  ctx.textBaseline = 'middle';
  ctx.fillText(signal.path, 8, midY);

  const plotLeft = LABEL_WIDTH;
  const plotWidth = width - LABEL_WIDTH;

  ctx.save();
  ctx.beginPath();
  ctx.rect(plotLeft, y, plotWidth, ROW_HEIGHT);
  ctx.clip();

  if (signal.width === 1) {
    let prevTime = 0;
    let prevHigh = isHigh(series[0]?.value ?? 'x');

    for (let index = 1; index < series.length; index += 1) {
      const point = series[index];
      const x1 = plotLeft + prevTime * timeScale - offsetX;
      const x2 = plotLeft + point.time * timeScale - offsetX;
      const levelY = prevHigh ? highY : lowY;
      const color = isUnknown(series[index - 1]?.value ?? 'x') ? COLORS.unknown : prevHigh ? COLORS.high : COLORS.low;

      ctx.strokeStyle = color;
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.moveTo(x1, levelY);
      ctx.lineTo(x2, levelY);
      ctx.stroke();

      const nextHigh = isHigh(point.value);
      if (nextHigh !== prevHigh) {
        ctx.beginPath();
        ctx.moveTo(x2, prevHigh ? highY : lowY);
        ctx.lineTo(x2, nextHigh ? highY : lowY);
        ctx.stroke();
      }

      prevTime = point.time;
      prevHigh = nextHigh;
    }

    const lastPoint = series[series.length - 1];
    if (lastPoint) {
      const x1 = plotLeft + lastPoint.time * timeScale - offsetX;
      const x2 = plotLeft + parsed.endTime * timeScale - offsetX;
      const levelY = prevHigh ? highY : lowY;
      ctx.strokeStyle = prevHigh ? COLORS.high : COLORS.low;
      ctx.beginPath();
      ctx.moveTo(x1, levelY);
      ctx.lineTo(x2, levelY);
      ctx.stroke();
    }
  } else {
    let prevTime = 0;
    for (let index = 1; index < series.length; index += 1) {
      const point = series[index];
      const x1 = plotLeft + prevTime * timeScale - offsetX;
      const x2 = plotLeft + point.time * timeScale - offsetX;
      const prevValue = series[index - 1]?.value ?? 'x';
      ctx.fillStyle = isUnknown(prevValue) ? COLORS.unknown : COLORS.bus;
      ctx.fillRect(x1, y + 5, Math.max(x2 - x1, 1), ROW_HEIGHT - 10);

      if (x2 - x1 > 36) {
        ctx.fillStyle = COLORS.text;
        ctx.font = '10px JetBrains Mono, monospace';
        ctx.fillText(formatSignalValue(signal, prevValue), x1 + 4, midY);
      }

      prevTime = point.time;
    }
  }

  ctx.restore();
}

function drawTimeAxis(
  ctx: CanvasRenderingContext2D,
  width: number,
  endTime: number,
  timeScale: number,
  offsetX: number,
  timescale: string,
): void {
  ctx.fillStyle = '#252526';
  ctx.fillRect(0, 0, width, TIME_AXIS_HEIGHT);

  ctx.strokeStyle = COLORS.grid;
  ctx.beginPath();
  ctx.moveTo(LABEL_WIDTH, TIME_AXIS_HEIGHT);
  ctx.lineTo(width, TIME_AXIS_HEIGHT);
  ctx.stroke();

  const plotWidth = width - LABEL_WIDTH;
  const tickCount = Math.max(4, Math.floor(plotWidth / 100));
  const tickStep = Math.max(1, Math.ceil(endTime / tickCount));

  ctx.fillStyle = COLORS.muted;
  ctx.font = '10px JetBrains Mono, monospace';
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';

  for (let tick = 0; tick <= endTime; tick += tickStep) {
    const x = LABEL_WIDTH + tick * timeScale - offsetX;
    if (x < LABEL_WIDTH || x > width) continue;
    ctx.strokeStyle = COLORS.grid;
    ctx.beginPath();
    ctx.moveTo(x, 0);
    ctx.lineTo(x, TIME_AXIS_HEIGHT);
    ctx.stroke();
    ctx.fillText(`${tick}`, x, TIME_AXIS_HEIGHT / 2);
  }

  ctx.textAlign = 'left';
  ctx.fillText(timescale, 8, TIME_AXIS_HEIGHT / 2);
}

export function WaveformViewer({ source, className = '' }: WaveformViewerProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [offsetX, setOffsetX] = useState(0);
  const [cursorTime, setCursorTime] = useState<number | null>(null);

  const parsed = useMemo(() => {
    try {
      return parseVcd(source);
    } catch {
      return null;
    }
  }, [source]);

  const visibleSignals = useMemo(() => {
    if (!parsed) return [];
    return parsed.signals.slice(0, MAX_SIGNALS);
  }, [parsed]);

  useEffect(() => {
    const canvas = canvasRef.current;
    const container = containerRef.current;
    if (!canvas || !container || !parsed) return;

    const render = () => {
      const width = container.clientWidth;
      if (width <= 0) return;

      const height = TIME_AXIS_HEIGHT + visibleSignals.length * ROW_HEIGHT;
      const dpr = window.devicePixelRatio || 1;

      canvas.width = width * dpr;
      canvas.height = height * dpr;
      canvas.style.width = `${width}px`;
      canvas.style.height = `${height}px`;

      const ctx = canvas.getContext('2d');
      if (!ctx) return;

      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.clearRect(0, 0, width, height);
      ctx.fillStyle = '#1e1e1e';
      ctx.fillRect(0, 0, width, height);

      const plotWidth = Math.max(width - LABEL_WIDTH, 1);
      const timeScale = parsed.endTime > 0 ? plotWidth / parsed.endTime : 1;

      drawTimeAxis(ctx, width, parsed.endTime, timeScale, offsetX, parsed.timescale);

      visibleSignals.forEach((signal, index) => {
        if (index % 2 === 0) {
          ctx.fillStyle = '#252526';
          ctx.fillRect(0, TIME_AXIS_HEIGHT + index * ROW_HEIGHT, width, ROW_HEIGHT);
        }
        drawSignalRow(ctx, signal, parsed, index, width, timeScale, offsetX);
      });

      if (cursorTime !== null) {
        const x = LABEL_WIDTH + cursorTime * timeScale - offsetX;
        ctx.strokeStyle = '#007acc';
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, height);
        ctx.stroke();
      }
    };

    render();
    const observer = new ResizeObserver(() => render());
    observer.observe(container);
    return () => observer.disconnect();
  }, [parsed, visibleSignals, offsetX, cursorTime]);

  if (!parsed) {
    return (
      <div className={`rounded border border-ide-border bg-ide-bg p-4 text-sm text-red-400 ${className}`}>
        Failed to parse VCD waveform.
      </div>
    );
  }

  if (parsed.signals.length === 0) {
    return (
      <div className={`rounded border border-ide-border bg-ide-bg p-4 text-sm text-ide-muted ${className}`}>
        No signals found in VCD file.
      </div>
    );
  }

  if (parsed.endTime === 0) {
    return (
      <div className={`rounded border border-ide-border bg-ide-bg p-4 text-sm text-yellow-400 ${className}`}>
        VCD loaded but contains no time steps. Ensure your testbench runs long enough and calls $dumpvars.
      </div>
    );
  }

  const plotWidth = Math.max((containerRef.current?.clientWidth ?? 800) - LABEL_WIDTH, 1);
  const timeScale = parsed.endTime > 0 ? plotWidth / parsed.endTime : 1;

  function handlePointerMove(event: React.PointerEvent<HTMLCanvasElement>) {
    if (!parsed) return;
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const time = Math.max(0, Math.min(parsed.endTime, (x - LABEL_WIDTH + offsetX) / timeScale));
    setCursorTime(Math.round(time));
  }

  return (
    <div className={`flex min-h-0 flex-col ${className}`}>
      <div className="mb-2 flex flex-wrap items-center gap-3 text-xs text-ide-muted">
        <span>{parsed.signals.length} signals</span>
        <span>End: {parsed.endTime} {parsed.timescale}</span>
        {parsed.signals.length > MAX_SIGNALS && (
          <span className="text-yellow-400">Showing first {MAX_SIGNALS} signals</span>
        )}
        {cursorTime !== null && (
          <span className="text-ide-text">
            t={cursorTime}
            {visibleSignals.slice(0, 4).map((signal) => {
              const series = parsed.transitions.get(signal.id) ?? [];
              const value = valueAtTime(series, cursorTime);
              return (
                <span key={signal.id} className="ml-2 font-mono">
                  {signal.name}={formatSignalValue(signal, value)}
                </span>
              );
            })}
          </span>
        )}
        <div className="ml-auto flex gap-2">
          <button
            type="button"
            onClick={() => setOffsetX((value) => Math.max(0, value - 80))}
            className="rounded border border-ide-border px-2 py-0.5 hover:bg-ide-sidebar"
          >
            ←
          </button>
          <button
            type="button"
            onClick={() => setOffsetX((value) => value + 80)}
            className="rounded border border-ide-border px-2 py-0.5 hover:bg-ide-sidebar"
          >
            →
          </button>
        </div>
      </div>
      <div ref={containerRef} className="min-h-0 flex-1 overflow-auto rounded border border-ide-border bg-ide-bg">
        <canvas
          ref={canvasRef}
          onPointerMove={handlePointerMove}
          onPointerLeave={() => setCursorTime(null)}
          className="block"
        />
      </div>
    </div>
  );
}
