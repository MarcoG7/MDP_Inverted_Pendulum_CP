import { ComponentFixture, TestBed } from '@angular/core/testing';
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest';
import { ControlPanel } from './control-panel';
import { CsvExportService } from '../../services/csv-export.service';
import { IStartParams } from '../../models/start-params';

describe('ControlPanel', () => {
  let component: ControlPanel;
  let fixture: ComponentFixture<ControlPanel>;
  let mockCsvExport: Partial<CsvExportService>;

  beforeEach(async () => {
    mockCsvExport = { export: vi.fn() };

    await TestBed.configureTestingModule({
      imports: [ControlPanel],
      providers: [{ provide: CsvExportService, useValue: mockCsvExport }],
    }).compileComponents();

    fixture = TestBed.createComponent(ControlPanel);
    component = fixture.componentInstance;
    fixture.detectChanges();
    await fixture.whenStable();
  });

  afterEach(() => {
    TestBed.resetTestingModule();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('default selected source is src-sim', () => {
    expect(component.selectedDataSource).toBe('src-sim');
  });

  it('default selected method is default', () => {
    expect(component.selectedControlMethod).toBe('default');
  });

  it('onStart emits start event with selected source and method', () => {
    let emitted: IStartParams | undefined;
    component.start.subscribe((params) => (emitted = params));

    component.selectedDataSource = 'src-matlab';
    component.selectedControlMethod = 'default';
    component.onStart();

    expect(emitted).toEqual({ data_source: 'src-matlab', ctrl_method: 'default' });
  });

  it('onStop emits stop event', () => {
    let emitted = false;
    component.stop.subscribe(() => (emitted = true));

    component.onStop();

    expect(emitted).toBe(true);
  });

  it('onReset emits reset event', () => {
    let emitted = false;
    component.reset.subscribe(() => (emitted = true));

    component.onReset();

    expect(emitted).toBe(true);
  });

  it('onExport calls CsvExportService.export with correct filename', () => {
    component.onExport();
    expect(mockCsvExport.export).toHaveBeenCalledWith('pendulum-session');
  });
});
