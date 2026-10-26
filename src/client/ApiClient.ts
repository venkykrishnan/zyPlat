import axios, { AxiosInstance } from 'axios';
import { Taxonomy, TaxonomyEntity } from '../models/Taxonomy';
import { Domain } from '../models/Domain';
import { Company } from '../models/Company';
import { DomainInstance } from '../models/DomainInstance';

export class ApiClient {
  private client: AxiosInstance;
  private baseURL: string;

  constructor(baseURL: string = 'http://localhost:3000/api') {
    this.baseURL = baseURL;
    this.client = axios.create({
      baseURL,
      timeout: 10000,
      headers: {
        'Content-Type': 'application/json'
      }
    });
  }

  async listTaxonomies(): Promise<Taxonomy[]> {
    const response = await this.client.get('/taxonomies');
    return response.data;
  }

  async getTaxonomy(id: string): Promise<Taxonomy> {
    const response = await this.client.get(`/taxonomies/${id}`);
    return response.data;
  }

  async createTaxonomy(taxonomy: Taxonomy): Promise<void> {
    await this.client.post('/taxonomies', taxonomy);
  }

  async updateTaxonomy(id: string, updates: Partial<Taxonomy>): Promise<Taxonomy> {
    const response = await this.client.put(`/taxonomies/${id}`, updates);
    return response.data;
  }

  async deleteTaxonomy(id: string): Promise<void> {
    await this.client.delete(`/taxonomies/${id}`);
  }

  async addTaxonomyEntity(taxonomyId: string, entity: TaxonomyEntity): Promise<Taxonomy> {
    const response = await this.client.post(`/taxonomies/${taxonomyId}/entities`, entity);
    return response.data;
  }

  async updateTaxonomyEntity(
    taxonomyId: string,
    entityId: string,
    updates: Partial<TaxonomyEntity>
  ): Promise<Taxonomy> {
    const response = await this.client.put(
      `/taxonomies/${taxonomyId}/entities/${entityId}`,
      updates
    );
    return response.data;
  }

  async deleteTaxonomyEntity(taxonomyId: string, entityId: string): Promise<Taxonomy> {
    const response = await this.client.delete(`/taxonomies/${taxonomyId}/entities/${entityId}`);
    return response.data;
  }

  async listDomains(): Promise<Domain[]> {
    const response = await this.client.get('/domains');
    return response.data;
  }

  async getDomain(id: string): Promise<Domain> {
    const response = await this.client.get(`/domains/${id}`);
    return response.data;
  }

  async createDomain(domain: Domain): Promise<void> {
    await this.client.post('/domains', domain);
  }

  async updateDomain(id: string, updates: Partial<Domain>): Promise<Domain> {
    const response = await this.client.put(`/domains/${id}`, updates);
    return response.data;
  }

  async deleteDomain(id: string): Promise<void> {
    await this.client.delete(`/domains/${id}`);
  }

  async listCompanies(type?: 'lender' | 'borrower'): Promise<Company[]> {
    const response = await this.client.get('/companies', {
      params: type ? { type } : {}
    });
    return response.data;
  }

  async getCompany(id: string): Promise<Company> {
    const response = await this.client.get(`/companies/${id}`);
    return response.data;
  }

  async createCompany(company: Company): Promise<void> {
    await this.client.post('/companies', company);
  }

  async updateCompany(id: string, updates: Partial<Company>): Promise<Company> {
    const response = await this.client.put(`/companies/${id}`, updates);
    return response.data;
  }

  async deleteCompany(id: string): Promise<void> {
    await this.client.delete(`/companies/${id}`);
  }

  async listInstances(companyId?: string, domainId?: string): Promise<DomainInstance[]> {
    const response = await this.client.get('/instances', {
      params: { companyId, domainId }
    });
    return response.data;
  }

  async getInstance(id: string): Promise<DomainInstance> {
    const response = await this.client.get(`/instances/${id}`);
    return response.data;
  }

  async createInstance(instance: DomainInstance): Promise<void> {
    await this.client.post('/instances', instance);
  }

  async updateInstance(id: string, updates: Partial<DomainInstance>): Promise<DomainInstance> {
    const response = await this.client.put(`/instances/${id}`, updates);
    return response.data;
  }

  async deleteInstance(id: string): Promise<void> {
    await this.client.delete(`/instances/${id}`);
  }

  async addInstanceData(id: string, data: Record<string, any>): Promise<DomainInstance> {
    const response = await this.client.post(`/instances/${id}/data`, data);
    return response.data;
  }

  async healthCheck(): Promise<{ status: string; timestamp: string }> {
    const response = await this.client.get('/health', { baseURL: this.baseURL.replace('/api', '') });
    return response.data;
  }
}
