import { TestBed } from '@angular/core/testing';
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest';
import { CsvExportService } from './csv-export.service';
import { ApiService } from './api.service';

describe('CsvExportService', () => {
  let service: CsvExportService;
  let mockApiService: Partial<ApiService>;
  let clickSpy: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    clickSpy = vi.fn();

    vi.stubGlobal('URL', {
      createObjectURL: vi.fn().mockReturnValue('blob:mock-url'),
      revokeObjectURL: vi.fn(),
    });

    vi.spyOn(document, 'createElement').mockReturnValue({
      href: '',
      download: '',
      click: clickSpy,
    } as unknown as HTMLAnchorElement);

    mockApiService = { getExportData: vi.fn() };

    TestBed.configureTestingModule({
      providers: [{ provide: ApiService, useValue: mockApiService }],
    });

    service = TestBed.inject(CsvExportService);
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
    TestBed.resetTestingModule();
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  it('does nothing and warns when there is no data', () => {
    vi.mocked(mockApiService.getExportData!).mockReturnValue('');
    const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});

    service.export('test');

    expect(clickSpy).not.toHaveBeenCalled();
    expect(warnSpy).toHaveBeenCalledWith('No data to export.');
  });

  it('triggers a download when data is available', () => {
    vi.mocked(mockApiService.getExportData!).mockReturnValue('1,0.1,0.2,5,0.1,src-sim\n');

    service.export('my-session');

    expect(clickSpy).toHaveBeenCalled();
    expect(URL.revokeObjectURL).toHaveBeenCalledWith('blob:mock-url');
  });

  it('sets the correct filename on the anchor', () => {
    vi.mocked(mockApiService.getExportData!).mockReturnValue('1,0.1,0.2,5,0.1,src-sim\n');
    const anchor = { href: '', download: '', click: clickSpy } as unknown as HTMLAnchorElement;
    vi.spyOn(document, 'createElement').mockReturnValue(anchor);

    service.export('my-session');

    expect(anchor.download).toBe('my-session.csv');
  });

  it('includes the CSV header in the exported blob', () => {
    vi.mocked(mockApiService.getExportData!).mockReturnValue('1,0.1,0.2,5,0.1,src-sim\n');
    let capturedBlob: Blob | null = null;
    vi.mocked(URL.createObjectURL).mockImplementation((blob) => {
      capturedBlob = blob as Blob;
      return 'blob:mock-url';
    });

    service.export('test');

    expect(capturedBlob).not.toBeNull();
  });
});
