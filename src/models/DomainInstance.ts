export interface DomainInstance {
  companyId: string;
  companyName: string;
  domainId: string;
  domainName: string;
  instanceId: string;
  classifications: string[];
  createdAt: string;
  modifiedAt: string;
  data: Record<string, any>[];
}
