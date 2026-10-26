import { Taxonomy, TaxonomyEntity } from '../models/Taxonomy';
import { FileService } from './FileService';
import * as path from 'path';

export class TaxonomyService {
  private fileService: FileService;

  constructor(fileService: FileService) {
    this.fileService = fileService;
  }

  list(): Taxonomy[] {
    const taxonomyDir = this.fileService.getInputPath('taxonomies');
    const files = this.fileService.listFiles(taxonomyDir);
    
    return files.map(file => this.fileService.readJSON<Taxonomy>(file));
  }

  get(id: string): Taxonomy {
    const filePath = this.fileService.getInputPath('taxonomies', `${id}.json`);
    return this.fileService.readJSON<Taxonomy>(filePath);
  }

  create(taxonomy: Taxonomy): void {
    const filePath = this.fileService.getInputPath('taxonomies', `${taxonomy.id}.json`);
    
    if (this.fileService.fileExists(filePath)) {
      throw new Error(`Taxonomy with id '${taxonomy.id}' already exists`);
    }

    taxonomy.createdAt = new Date().toISOString();
    taxonomy.modifiedAt = taxonomy.createdAt;
    
    this.fileService.writeJSON(filePath, taxonomy);
  }

  update(id: string, updates: Partial<Taxonomy>): Taxonomy {
    const filePath = this.fileService.getInputPath('taxonomies', `${id}.json`);
    const taxonomy = this.fileService.readJSON<Taxonomy>(filePath);
    
    const updated = {
      ...taxonomy,
      ...updates,
      id: taxonomy.id,
      modifiedAt: new Date().toISOString()
    };
    
    this.fileService.writeJSON(filePath, updated);
    return updated;
  }

  delete(id: string): void {
    const filePath = this.fileService.getInputPath('taxonomies', `${id}.json`);
    this.fileService.deleteFile(filePath);
  }

  addEntity(taxonomyId: string, entity: TaxonomyEntity): Taxonomy {
    const taxonomy = this.get(taxonomyId);
    
    const exists = taxonomy.entities.some(e => e.id === entity.id);
    if (exists) {
      throw new Error(`Entity with id '${entity.id}' already exists in taxonomy '${taxonomyId}'`);
    }

    if (entity.parent) {
      const parentExists = taxonomy.entities.some(e => e.id === entity.parent);
      if (!parentExists) {
        throw new Error(`Parent entity '${entity.parent}' not found in taxonomy '${taxonomyId}'`);
      }
    }

    taxonomy.entities.push(entity);
    taxonomy.modifiedAt = new Date().toISOString();
    
    const filePath = this.fileService.getInputPath('taxonomies', `${taxonomyId}.json`);
    this.fileService.writeJSON(filePath, taxonomy);
    
    return taxonomy;
  }

  updateEntity(taxonomyId: string, entityId: string, updates: Partial<TaxonomyEntity>): Taxonomy {
    const taxonomy = this.get(taxonomyId);
    
    const index = taxonomy.entities.findIndex(e => e.id === entityId);
    if (index === -1) {
      throw new Error(`Entity with id '${entityId}' not found in taxonomy '${taxonomyId}'`);
    }

    taxonomy.entities[index] = {
      ...taxonomy.entities[index],
      ...updates,
      id: taxonomy.entities[index].id
    };
    
    taxonomy.modifiedAt = new Date().toISOString();
    
    const filePath = this.fileService.getInputPath('taxonomies', `${taxonomyId}.json`);
    this.fileService.writeJSON(filePath, taxonomy);
    
    return taxonomy;
  }

  deleteEntity(taxonomyId: string, entityId: string): Taxonomy {
    const taxonomy = this.get(taxonomyId);
    
    const hasChildren = taxonomy.entities.some(e => e.parent === entityId);
    if (hasChildren) {
      throw new Error(`Cannot delete entity '${entityId}' because it has child entities`);
    }

    taxonomy.entities = taxonomy.entities.filter(e => e.id !== entityId);
    taxonomy.modifiedAt = new Date().toISOString();
    
    const filePath = this.fileService.getInputPath('taxonomies', `${taxonomyId}.json`);
    this.fileService.writeJSON(filePath, taxonomy);
    
    return taxonomy;
  }
}
