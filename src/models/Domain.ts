export interface TaxonomyReference {
  taxonomyId: string;
  version: string;
}

export interface DimensionField {
  name: string;
  type: 'String' | 'Integer' | 'Number' | 'Boolean' | 'DateTime' | 'Taxonomy';
  displayName: string;
  isFilter: boolean;
  required: boolean;
  taxonomyRef?: TaxonomyReference;
  dateTimeScope?: 'DateTime' | 'DateMonthYear' | 'MonthYear';
}

export interface MetricField {
  name: string;
  type: 'Number' | 'Integer';
  displayName: string;
  isPointInTime: boolean;
  required: boolean;
}

export interface DataSchema {
  dimensions: DimensionField[];
  metrics: MetricField[];
}

export interface Domain {
  id: string;
  name: string;
  description: string;
  isTimeSeries: boolean;
  isConfigurable: boolean;
  version: string;
  createdAt: string;
  modifiedAt: string;
  dataSchema: DataSchema;
}
