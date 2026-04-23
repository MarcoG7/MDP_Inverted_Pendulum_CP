import { NgClass } from '@angular/common';
import { Component, effect, input, signal, viewChild } from '@angular/core';
import { Chart, ChartConfiguration, ChartData, registerables } from 'chart.js';
import { BaseChartDirective } from 'ng2-charts';
import { IGraphConfig } from '../../models/graph-config';

Chart.register(...registerables);

@Component({
  selector: 'app-realtime-graph',
  imports: [NgClass, BaseChartDirective],
  templateUrl: './realtime-graph.html',
  styleUrl: './realtime-graph.scss',
})
export class RealtimeGraph {
  config = input.required<IGraphConfig>();
  size = input<'large' | 'small'>('large');

  private chart = viewChild(BaseChartDirective);

  currentValue = signal<number | null>(null);
  minValue = signal<number | null>(null);
  maxValue = signal<number | null>(null);
  meanValue = signal<number | null>(null);

  chartData: ChartData<'line'> = {
    datasets: [
      {
        data: [],
        label: '',
        borderColor: '',
        backgroundColor: 'transparent',
        tension: 0.1,
        pointRadius: 0,
      },
    ],
    labels: [],
  };

  private readonly INITIAL_WINDOW = 10; // seconds shown before the axis starts expanding

  private _pendingRender = false;
  private _latestTimestamp = 0;
  private _maxWindow = 60;

  chartOptions: ChartConfiguration<'line'>['options'] = {
    responsive: true,
    maintainAspectRatio: false,
    animation: false,
    scales: {
      x: {
        type: 'linear',
        min: 0,
        max: this.INITIAL_WINDOW,
        title: { display: false, text: 'Time (seconds)' },
        ticks: { callback: (value) => Number(value).toFixed(1) + 's' },
      },
      y: {
        type: 'linear',
        title: { display: true, text: '' },
        min: undefined,
        max: undefined,
      },
    },
    plugins: {
      legend: { display: false },
    },
  };

  constructor() {
    // Runs whenever config() changes to apply title, color, axis labels
    effect(() => this.applyConfiguration());
  }

  addDataPoint(timestamp: number, value: number): void {
    const maxWindow = this.config().windowSeconds ?? 60;
    const data = this.chartData.datasets[0].data as { x: number; y: number }[];

    data.push({ x: timestamp, y: value });

    // Drop points that have fallen outside the rolling window
    const cutoff = timestamp - maxWindow;
    while (data.length > 0 && data[0].x < cutoff) data.shift();

    this._latestTimestamp = timestamp;
    this._maxWindow = maxWindow;
    this.updateStatistics();

    // Coalesce rapid updates — render at most once per animation frame (~60 fps)
    if (!this._pendingRender) {
      this._pendingRender = true;
      requestAnimationFrame(() => {
        this._flushRender();
        this._pendingRender = false;
      });
    }
  }

  private _flushRender(): void {
    const chartInstance = this.chart()?.chart;
    if (chartInstance) {
      const xScale = chartInstance.options.scales?.['x'] as any;
      const timestamp = this._latestTimestamp;
      const maxWindow = this._maxWindow;
      if (timestamp <= maxWindow) {
        xScale.min = 0;
        xScale.max = Math.max(timestamp, this.INITIAL_WINDOW);
      } else {
        xScale.min = timestamp - maxWindow;
        xScale.max = timestamp;
      }
    }
    this.chart()?.update();
  }

  clearData(): void {
    this.chartData.datasets[0].data = [];
    // Reset axis to the initial fixed window
    const chartInstance = this.chart()?.chart;
    if (chartInstance) {
      const xScale = chartInstance.options.scales?.['x'] as any;
      xScale.min = 0;
      xScale.max = this.INITIAL_WINDOW;
    }
    this.currentValue.set(null);
    this.minValue.set(null);
    this.maxValue.set(null);
    this.meanValue.set(null);
    this.chart()?.update();
  }

  private applyConfiguration(): void {
    const config = this.config();
    this.chartData.datasets[0].label = config.title;
    this.chartData.datasets[0].borderColor = config.lineColor;

    const yScale = this.chartOptions?.scales?.['y'];
    if (yScale) {
      yScale.title = { display: true, text: config.yAxisLabel };
      if (config.yMin !== undefined) yScale.min = config.yMin;
      if (config.yMax !== undefined) yScale.max = config.yMax;
    }
  }

  private updateStatistics(): void {
    const data = this.chartData.datasets[0].data as { x: number; y: number }[];

    if (data.length === 0) {
      this.currentValue.set(null);
      this.minValue.set(null);
      this.maxValue.set(null);
      this.meanValue.set(null);
      return;
    }

    const values = data.map((p) => p.y);
    this.currentValue.set(values[values.length - 1]);
    this.minValue.set(Math.min(...values));
    this.maxValue.set(Math.max(...values));
    this.meanValue.set(values.reduce((sum, v) => sum + v, 0) / values.length);
  }
}
