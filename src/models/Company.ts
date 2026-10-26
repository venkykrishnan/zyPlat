export interface Company {
  id: string;
  name: string;
  type: 'lender' | 'borrower';
  description: string;
  industry: string;
  createdAt: string;
  modifiedAt: string;
  metadata: Record<string, any>;
}
