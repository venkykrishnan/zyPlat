import { Company } from '../models/Company';
import { FileService } from './FileService';

export class CompanyService {
  private fileService: FileService;
  private companiesFile: string;

  constructor(fileService: FileService) {
    this.fileService = fileService;
    this.companiesFile = fileService.getInputPath('companies', 'companies.json');
  }

  private loadCompanies(): Company[] {
    if (!this.fileService.fileExists(this.companiesFile)) {
      return [];
    }
    return this.fileService.readJSON<Company[]>(this.companiesFile);
  }

  private saveCompanies(companies: Company[]): void {
    this.fileService.writeJSON(this.companiesFile, companies);
  }

  list(type?: 'lender' | 'borrower'): Company[] {
    const companies = this.loadCompanies();
    
    if (type) {
      return companies.filter(c => c.type === type);
    }
    
    return companies;
  }

  get(id: string): Company {
    const companies = this.loadCompanies();
    const company = companies.find(c => c.id === id);
    
    if (!company) {
      throw new Error(`Company with id '${id}' not found`);
    }
    
    return company;
  }

  create(company: Company): void {
    const companies = this.loadCompanies();
    
    const exists = companies.some(c => c.id === company.id);
    if (exists) {
      throw new Error(`Company with id '${company.id}' already exists`);
    }

    company.createdAt = new Date().toISOString();
    company.modifiedAt = company.createdAt;
    
    companies.push(company);
    this.saveCompanies(companies);
  }

  update(id: string, updates: Partial<Company>): Company {
    const companies = this.loadCompanies();
    const index = companies.findIndex(c => c.id === id);
    
    if (index === -1) {
      throw new Error(`Company with id '${id}' not found`);
    }

    const updated = {
      ...companies[index],
      ...updates,
      id: companies[index].id,
      modifiedAt: new Date().toISOString()
    };
    
    companies[index] = updated;
    this.saveCompanies(companies);
    
    return updated;
  }

  delete(id: string): void {
    const companies = this.loadCompanies();
    const filtered = companies.filter(c => c.id !== id);
    
    if (filtered.length === companies.length) {
      throw new Error(`Company with id '${id}' not found`);
    }
    
    this.saveCompanies(filtered);
  }
}
