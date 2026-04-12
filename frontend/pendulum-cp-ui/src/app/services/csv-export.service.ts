import { inject, Injectable } from '@angular/core';
import { ApiService } from './api.service';

const CSV_HEADER = 'timestamp,position,velocity,angle,angular_velocity,data_source\n';

@Injectable({ providedIn: 'root' })
export class CsvExportService {
  private readonly api = inject(ApiService);

  export(filename: string): void {
    const rows = this.api.getExportData();

    if (!rows) {
      console.warn('No data to export.');
      return;
    }

    const blob = new Blob([CSV_HEADER + rows], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${filename}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }
}
