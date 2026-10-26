import { DomainInstance } from '../models/DomainInstance';
import { FileService } from './FileService';
import * as path from 'path';

export class DomainInstanceService {
  private fileService: FileService;

  constructor(fileService: FileService) {
    this.fileService = fileService;
  }

  list(companyId?: string, domainId?: string): DomainInstance[] {
    const instanceDir = this.fileService.getInputPath('domain-instances');
    const files = this.fileService.listFiles(instanceDir);
    
    let instances = files.map(file => this.fileService.readJSON<DomainInstance>(file));
    
    if (companyId) {
      instances = instances.filter(i => i.companyId === companyId);
    }
    
    if (domainId) {
      instances = instances.filter(i => i.domainId === domainId);
    }
    
    return instances;
  }

  get(instanceId: string): DomainInstance {
    const instanceDir = this.fileService.getInputPath('domain-instances');
    const files = this.fileService.listFiles(instanceDir);
    
    for (const file of files) {
      const instance = this.fileService.readJSON<DomainInstance>(file);
      if (instance.instanceId === instanceId) {
        return instance;
      }
    }
    
    throw new Error(`Domain instance with id '${instanceId}' not found`);
  }

  create(instance: DomainInstance): void {
    const fileName = `${instance.companyId}_${instance.domainId}.json`;
    const filePath = this.fileService.getInputPath('domain-instances', fileName);
    
    if (this.fileService.fileExists(filePath)) {
      throw new Error(`Domain instance for company '${instance.companyId}' and domain '${instance.domainId}' already exists`);
    }

    instance.createdAt = new Date().toISOString();
    instance.modifiedAt = instance.createdAt;
    
    this.fileService.writeJSON(filePath, instance);
  }

  update(instanceId: string, updates: Partial<DomainInstance>): DomainInstance {
    const instanceDir = this.fileService.getInputPath('domain-instances');
    const files = this.fileService.listFiles(instanceDir);
    
    for (const file of files) {
      const instance = this.fileService.readJSON<DomainInstance>(file);
      if (instance.instanceId === instanceId) {
        const updated = {
          ...instance,
          ...updates,
          instanceId: instance.instanceId,
          modifiedAt: new Date().toISOString()
        };
        
        this.fileService.writeJSON(file, updated);
        return updated;
      }
    }
    
    throw new Error(`Domain instance with id '${instanceId}' not found`);
  }

  delete(instanceId: string): void {
    const instanceDir = this.fileService.getInputPath('domain-instances');
    const files = this.fileService.listFiles(instanceDir);
    
    for (const file of files) {
      const instance = this.fileService.readJSON<DomainInstance>(file);
      if (instance.instanceId === instanceId) {
        this.fileService.deleteFile(file);
        return;
      }
    }
    
    throw new Error(`Domain instance with id '${instanceId}' not found`);
  }

  addData(instanceId: string, data: Record<string, any>): DomainInstance {
    const instance = this.get(instanceId);
    instance.data.push(data);
    instance.modifiedAt = new Date().toISOString();
    
    const fileName = `${instance.companyId}_${instance.domainId}.json`;
    const filePath = this.fileService.getInputPath('domain-instances', fileName);
    this.fileService.writeJSON(filePath, instance);
    
    return instance;
  }
}
