import { NgClass } from '@angular/common';
import { Component, DestroyRef, effect, inject, signal, viewChild } from '@angular/core';
import { MatButtonToggleModule } from '@angular/material/button-toggle';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatTooltipModule } from '@angular/material/tooltip';
import { ApiService } from '../../services/api.service';
import { ControlPanel } from '../control-panel/control-panel';
import { RealtimeGraph } from '../realtime-graph/realtime-graph';
import { IGraphConfig } from '../../models/graph-config';
import { IStartParams } from '../../models/start-params';
import { LayoutType } from '../../models/layout';

@Component({
  selector: 'app-dashboard',
  imports: [NgClass, ControlPanel, RealtimeGraph, MatCardModule, MatButtonToggleModule, MatIconModule, MatTooltipModule],
  templateUrl: './dashboard.html',
  styleUrl: './dashboard.scss',
})
export class Dashboard {
  private readonly api = inject(ApiService);
  private readonly destroyRef = inject(DestroyRef);

  readonly loadingStage = this.api.loadingStage;
  readonly loadingMessage = this.api.loadingMessage;
  readonly engineReady = this.api.engineReady;
  readonly simulationReady = this.api.simulationReady;

  elapsedTime = signal(0);
  layout = signal<LayoutType>('graph-focus');

  private readonly angleGraph = viewChild<RealtimeGraph>('angleGraph');
  private readonly angularVelocityGraph = viewChild<RealtimeGraph>('angularVelocityGraph');
  private readonly positionGraph = viewChild<RealtimeGraph>('positionGraph');
  private readonly velocityGraph = viewChild<RealtimeGraph>('velocityGraph');

  private readonly GRAPH_WINDOW_SECONDS = 60;

  readonly angleConfig: IGraphConfig = {
    title: 'Pendulum Angle',
    yAxisLabel: 'θ (degrees)',
    lineColor: '#3b82f6',
    windowSeconds: this.GRAPH_WINDOW_SECONDS,
  };

  readonly angularVelocityConfig: IGraphConfig = {
    title: 'Angular Velocity',
    yAxisLabel: "θ' (rad/s)",
    lineColor: '#3b82f6',
    windowSeconds: this.GRAPH_WINDOW_SECONDS,
  };

  readonly positionConfig: IGraphConfig = {
    title: 'Cart Position',
    yAxisLabel: 'x (m)',
    lineColor: '#3b82f6',
    windowSeconds: this.GRAPH_WINDOW_SECONDS,
  };

  readonly velocityConfig: IGraphConfig = {
    title: 'Cart Velocity',
    yAxisLabel: "x' (m/s)",
    lineColor: '#3b82f6',
    windowSeconds: this.GRAPH_WINDOW_SECONDS,
  };

  constructor() {
    this.destroyRef.onDestroy(() => this.api.disconnect());

    effect(() => {
      const data = this.api.telemetry();
      if (!data) return;
      this.elapsedTime.set(data.timestamp);

      this.angleGraph()?.addDataPoint?.(data.timestamp, data.angle);
      this.angularVelocityGraph()?.addDataPoint?.(data.timestamp, data.angular_velocity);
      this.positionGraph()?.addDataPoint?.(data.timestamp, data.position);
      this.velocityGraph()?.addDataPoint?.(data.timestamp, data.velocity);
    });
  }

  start(params: IStartParams): void {
    this.api.start(params.data_source, params.ctrl_method);
  }

  stop(): void {
    this.api.stop();
  }

  reset(): void {
    this.elapsedTime.set(0);
    this.api.reset();
    this.angleGraph()?.clearData?.();
    this.angularVelocityGraph()?.clearData?.();
    this.positionGraph()?.clearData?.();
    this.velocityGraph()?.clearData?.();
  }

  formatTime(seconds: number): string {
    const totalMs = Math.round(seconds * 1000);
    const ms = (totalMs % 1000).toString().padStart(3, '0');
    const totalSecs = Math.floor(totalMs / 1000);
    const s = (totalSecs % 60).toString().padStart(2, '0');
    const m = Math.floor(totalSecs / 60).toString().padStart(2, '0');
    return `${m}:${s}.${ms}`;
  }
}
