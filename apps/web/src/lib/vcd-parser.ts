export interface VcdSignal {
  id: string;
  name: string;
  width: number;
  path: string;
}

export interface VcdTransition {
  time: number;
  value: string;
}

export interface ParsedVcd {
  timescale: string;
  signals: VcdSignal[];
  transitions: Map<string, VcdTransition[]>;
  endTime: number;
}


function parseVarLine(line: string, scopeStack: string[]): VcdSignal | null {
  const match = line.match(/^\$var\s+\S+\s+(\d+)\s+(\S+)\s+(.+?)\s+\$end$/);
  if (!match) return null;

  const width = Number(match[1]);
  const id = match[2];
  const namePart = match[3].trim();
  const name = namePart.replace(/\s*\[[^\]]+\]\s*$/, '').trim();
  const path = [...scopeStack, name].join('.');

  return { id, name, width, path };
}

function parseValueLine(line: string): { id: string; value: string } | null {
  const binary = line.match(/^b([01xXzZ]+)\s+(\S+)$/);
  if (binary) {
    return { id: binary[2], value: binary[1].toLowerCase() };
  }

  const scalar = line.match(/^([01xXzZ])(\S+)$/);
  if (scalar) {
    return { id: scalar[2], value: scalar[1].toLowerCase() };
  }

  return null;
}

function appendTransition(
  transitions: Map<string, VcdTransition[]>,
  signalId: string,
  time: number,
  value: string,
): void {
  const series = transitions.get(signalId);
  if (!series) return;

  const last = series[series.length - 1];
  if (last && last.time === time && last.value === value) return;
  if (last && last.time === time) {
    last.value = value;
    return;
  }
  series.push({ time, value });
}

export function parseVcd(source: string): ParsedVcd {
  const lines = source.split(/\r?\n/);
  const scopeStack: string[] = [];
  const signals: VcdSignal[] = [];
  const transitions = new Map<string, VcdTransition[]>();
  let timescale = '1ns';
  let currentTime = 0;
  let endTime = 0;
  let inDefinitions = true;

  for (const rawLine of lines) {
    const line = rawLine.trim();
    if (!line) continue;

    if (inDefinitions) {
      if (line.startsWith('$timescale')) {
        timescale = line.replace('$timescale', '').replace('$end', '').trim() || '1ns';
        continue;
      }
      if (line.startsWith('$scope')) {
        const scopeName = line.replace('$scope', '').replace('$end', '').trim().split(/\s+/).pop();
        if (scopeName) scopeStack.push(scopeName);
        continue;
      }
      if (line === '$upscope $end') {
        scopeStack.pop();
        continue;
      }
      if (line.startsWith('$var')) {
        const signal = parseVarLine(line, scopeStack);
        if (signal) {
          signals.push(signal);
          transitions.set(signal.id, [{ time: 0, value: signal.width > 1 ? 'x'.repeat(signal.width) : 'x' }]);
        }
        continue;
      }
      if (line.includes('$enddefinitions')) {
        inDefinitions = false;
      }
      continue;
    }

    if (line.startsWith('#')) {
      currentTime = Number(line.slice(1));
      if (!Number.isNaN(currentTime)) {
        endTime = Math.max(endTime, currentTime);
      }
      continue;
    }

    const change = parseValueLine(line);
    if (change) {
      appendTransition(transitions, change.id, currentTime, change.value);
      endTime = Math.max(endTime, currentTime);
    }
  }

  return { timescale, signals, transitions, endTime };
}

export function formatSignalValue(signal: VcdSignal, value: string): string {
  if (signal.width === 1) {
    return value;
  }
  if (!/^[01]+$/.test(value)) {
    return value;
  }
  const numeric = Number.parseInt(value, 2);
  return `0x${numeric.toString(16).toUpperCase()}`;
}

export function valueAtTime(series: VcdTransition[], time: number): string {
  if (series.length === 0) return 'x';
  let current = series[0].value;
  for (const point of series) {
    if (point.time > time) break;
    current = point.value;
  }
  return current;
}
