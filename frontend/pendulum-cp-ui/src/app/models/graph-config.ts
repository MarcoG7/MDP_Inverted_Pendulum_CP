export interface IGraphConfig {
  title: string;
  yAxisLabel: string;
  yMin?: number; // defaults to auto
  yMax?: number; // defaults to auto
  lineColor: string;
  windowSeconds?: number; // defaults to 30
}
