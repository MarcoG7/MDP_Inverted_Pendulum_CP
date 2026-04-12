import { Component, inject, output } from '@angular/core';
import { CsvExportService } from '../../services/csv-export.service';
import { ControlMethod, DataSource, IStartParams } from '../../models/start-params';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatDividerModule } from '@angular/material/divider';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';

@Component({
  selector: 'app-control-panel',
  imports: [
    FormsModule,
    MatCardModule,
    MatButtonModule,
    MatFormFieldModule,
    MatSelectModule,
    MatDividerModule,
  ],
  templateUrl: './control-panel.html',
  styleUrl: './control-panel.scss',
})
export class ControlPanel {
  private readonly csvExportService = inject(CsvExportService);

  selectedDataSource: DataSource = 'src-sim';
  selectedControlMethod: ControlMethod = 'default';

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
}
