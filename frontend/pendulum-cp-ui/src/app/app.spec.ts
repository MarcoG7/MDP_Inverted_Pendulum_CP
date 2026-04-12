import { TestBed } from '@angular/core/testing';
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest';
import { NO_ERRORS_SCHEMA } from '@angular/core';
import { App } from './app';

describe('App', () => {
  beforeEach(async () => {
    vi.stubGlobal(
      'WebSocket',
      class {
        static OPEN = 1;
        onopen: any;
        onmessage: any;
        onclose: any;
        onerror: any;
        constructor() {
          setTimeout(() => this.onopen?.(), 0);
        }
        close() {}
      },
    );
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true }));

    await TestBed.configureTestingModule({
      imports: [App],
      schemas: [NO_ERRORS_SCHEMA],
    }).compileComponents();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    TestBed.resetTestingModule();
  });

  it('should create the app', () => {
    const fixture = TestBed.createComponent(App);
    expect(fixture.componentInstance).toBeTruthy();
  });
});
