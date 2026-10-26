export interface TaxonomyEntity {
  id: string;
  value: string;
  description: string;
  displayName: string;
  classifications: string[];
  aliases: string[];
  keywords: string[];
  parent: string | null;
  isRoot: boolean;
}

export interface Taxonomy {
  id: string;
  name: string;
  description: string;
  isHierarchical: boolean;
  classifications: string[];
  version: string;
  isPublished: boolean;
  createdAt: string;
  modifiedAt: string;
  entities: TaxonomyEntity[];
}
