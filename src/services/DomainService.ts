import { Domain } from '../models/Domain';
import { FileService } from './FileService';

export class DomainService {
  private fileService: FileService;

  constructor(fileService: FileService) {
    this.fileService = fileService;
  }

  list(): Domain[] {
    const domainDir = this.fileService.getInputPath('domains');
    const files = this.fileService.listFiles(domainDir);
    
    return files.map(file => this.fileService.readJSON<Domain>(file));
  }

  get(id: string): Domain {
    const files = this.fileService.listFiles(this.fileService.getInputPath('domains'));
    const file = files.find(f => {
      const domain = this.fileService.readJSON<Domain>(f);
      return domain.id === id;
    });

    if (!file) {
      throw new Error(`Domain with id '${id}' not found`);
    }

    return this.fileService.readJSON<Domain>(file);
  }

  create(domain: Domain): void {
    const fileName = domain.name.replace(/\s+/g, '') + '.json';
    const filePath = this.fileService.getInputPath('domains', fileName);
    
    if (this.fileService.fileExists(filePath)) {
      throw new Error(`Domain file '${fileName}' already exists`);
    }

    domain.createdAt = new Date().toISOString();
    domain.modifiedAt = domain.createdAt;
    
    this.fileService.writeJSON(filePath, domain);
  }

  update(id: string, updates: Partial<Domain>): Domain {
    const files = this.fileService.listFiles(this.fileService.getInputPath('domains'));
    const file = files.find(f => {
      const domain = this.fileService.readJSON<Domain>(f);
      return domain.id === id;
    });

    if (!file) {
      throw new Error(`Domain with id '${id}' not found`);
    }

    const domain = this.fileService.readJSON<Domain>(file);
    const updated = {
      ...domain,
      ...updates,
      id: domain.id,
      modifiedAt: new Date().toISOString()
    };
    
    this.fileService.writeJSON(file, updated);
    return updated;
  }

  delete(id: string): void {
    const files = this.fileService.listFiles(this.fileService.getInputPath('domains'));
    const file = files.find(f => {
      const domain = this.fileService.readJSON<Domain>(f);
      return domain.id === id;
    });

    if (!file) {
      throw new Error(`Domain with id '${id}' not found`);
    }

    this.fileService.deleteFile(file);
  }
}
