import { ComponentFixture, TestBed } from '@angular/core/testing';
import { describe, it, expect, beforeEach } from 'vitest';
import { NO_ERRORS_SCHEMA } from '@angular/core';
import { RealtimeGraph } from './realtime-graph';
import { IGraphConfig } from '../../models/graph-config';
import { BaseChartDirective } from 'ng2-charts';

const MOCK_CONFIG: IGraphConfig = {
  title: 'Test Graph',
  yAxisLabel: 'Value',
  lineColor: '#ff0000',
  windowSeconds: 10,
};

describe('RealtimeGraph', () => {
  let component: RealtimeGraph;
  let fixture: ComponentFixture<RealtimeGraph>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [RealtimeGraph],
    })
      .overrideComponent(RealtimeGraph, {
        remove: { imports: [BaseChartDirective] },
        add: { schemas: [NO_ERRORS_SCHEMA] },
      })
      .compileComponents();

    fixture = TestBed.createComponent(RealtimeGraph);
    fixture.componentRef.setInput('config', MOCK_CONFIG);
    component = fixture.componentInstance;
    fixture.detectChanges();
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('statistics are null before any data', () => {
    expect(component.currentValue()).toBeNull();
    expect(component.minValue()).toBeNull();
  });

  it('addDataPoint updates currentValue', () => {
    component.addDataPoint(1.0, 42.0);
    expect(component.currentValue()).toBe(42.0);
  });

  it('addDataPoint calculates min and max', () => {
    component.addDataPoint(1.0, 10.0);
    component.addDataPoint(2.0, 30.0);
    component.addDataPoint(3.0, 20.0);
    expect(component.minValue()).toBe(10.0);
    expect(component.maxValue()).toBe(30.0);
  });

  it('addDataPoint calculates mean', () => {
    component.addDataPoint(1.0, 10.0);
    component.addDataPoint(2.0, 20.0);
    expect(component.meanValue()).toBe(15.0);
  });

  it('addDataPoint drops points outside the time window', () => {
    component.addDataPoint(0.0, 1.0); // will be dropped when t=15
    component.addDataPoint(5.0, 2.0);
    component.addDataPoint(15.0, 3.0); // cutoff = 15 - 10 = 5, so t=0 is dropped

    const data = component.chartData.datasets[0].data as { x: number; y: number }[];
    expect(data.find((p) => p.x === 0.0)).toBeUndefined();
    expect(data.length).toBe(2);
  });

  it('clearData resets all statistics to null', () => {
    component.addDataPoint(1.0, 42.0);
    component.clearData();
    expect(component.currentValue()).toBeNull();
    expect(component.minValue()).toBeNull();
    expect(component.maxValue()).toBeNull();
    expect(component.meanValue()).toBeNull();
  });

  it('clearData empties the dataset', () => {
    component.addDataPoint(1.0, 42.0);
    component.clearData();
    expect(component.chartData.datasets[0].data).toHaveLength(0);
  });
});
