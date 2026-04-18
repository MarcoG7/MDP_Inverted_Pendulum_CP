import { Component, inject, input, output } from '@angular/core';
import { CsvExportService } from '../../services/csv-export.service';
import { ApiService } from '../../services/api.service';
import { ControlMethod, DataSource, IStartParams } from '../../models/start-params';
import { LoadingStage } from '../../models/system-status';
import { DEFAULT_SIMULATION_PARAMS, ISimulationParams } from '../../models/simulation-params';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatDividerModule } from '@angular/material/divider';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatSelectModule } from '@angular/material/select';

@Component({
  selector: 'app-control-panel',
  imports: [
    FormsModule,
    MatCardModule,
    MatButtonModule,
    MatFormFieldModule,
    MatInputModule,
    MatProgressBarModule,
    MatSelectModule,
    MatDividerModule,
  ],
  templateUrl: './control-panel.html',
  styleUrl: './control-panel.scss',
})
export class ControlPanel {
  private readonly csvExportService = inject(CsvExportService);
  private readonly api = inject(ApiService);

  selectedDataSource: DataSource = 'src-sim';
  selectedControlMethod: ControlMethod = 'default';

  // Simulation parameters — editable copy, sent on Save
  params: ISimulationParams = { ...DEFAULT_SIMULATION_PARAMS };

  loadingStage = input<LoadingStage>(null);
  loadingMessage = input<string>('');
  engineReady = input<boolean>(true);
  simulationReady = input<boolean>(false);

  private readonly MATLAB_SOURCES: DataSource[] = ['src-simulink', 'src-matlab'];

  get isSimulink(): boolean {
    return this.selectedDataSource === 'src-simulink';
  }

  get requiresEngine(): boolean {
    return this.MATLAB_SOURCES.includes(this.selectedDataSource);
  }

  get isLoading(): boolean {
    return (
      this.loadingStage() !== null ||
      (this.requiresEngine && !this.engineReady()) ||
      (this.isSimulink && !this.simulationReady())
    );
  }

  get activeLoadingMessage(): string {
    if (this.loadingStage()) return this.loadingMessage();
    if (this.requiresEngine && !this.engineReady()) return 'MATLAB engine loading in background...';
    if (this.isSimulink && !this.simulationReady()) return 'Compiling Simulink model...';
    return '';
  }

  start = output<IStartParams>();
  stop = output<void>();
  reset = output<void>();

  onStart(): void {
    this.start.emit({
      data_source: this.selectedDataSource,
      ctrl_method: this.selectedControlMethod,
    });
  }

  onStop(): void {
    this.stop.emit();
  }

  onReset(): void {
    this.reset.emit();
  }

  onExport(): void {
    this.csvExportService.export('pendulum-session');
  }

  onSaveParams(): void {
    this.api.recompile(this.params);
  }

  onResetParams(): void {
    this.params = { ...DEFAULT_SIMULATION_PARAMS };
  }
}
