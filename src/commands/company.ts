import { Command } from 'commander';
import chalk from 'chalk';
import { ApiClient } from '../client/ApiClient';
import { FileService } from '../services/FileService';
import { Company } from '../models/Company';
import * as path from 'path';

const getApiClient = (apiUrl?: string) => new ApiClient(apiUrl);
const fileService = new FileService();

export const companyCommand = new Command('company')
  .alias('co')
  .description('Manage companies')
  .option('--api-url <url>', 'API base URL', 'http://localhost:3000/api');

companyCommand
  .command('list')
  .description('List all companies')
  .option('-t, --type <type>', 'Filter by type (lender or borrower)')
  .action(async (options, command) => {
    try {
      const apiUrl = command.parent.opts().apiUrl;
      const client = getApiClient(apiUrl);
      const type = options.type as 'lender' | 'borrower' | undefined;
      const companies = await client.listCompanies(type);
      
      if (companies.length === 0) {
        console.log(chalk.yellow('No companies found'));
        return;
      }

      console.log(chalk.bold('\nCompanies:\n'));
      
      const lenders = companies.filter(c => c.type === 'lender');
      const borrowers = companies.filter(c => c.type === 'borrower');

      if (lenders.length > 0 && (!type || type === 'lender')) {
        console.log(chalk.bold('Lenders:'));
        lenders.forEach(company => {
          console.log(chalk.cyan(`  ${company.id}`) + chalk.gray(` - ${company.name}`));
          console.log(chalk.gray(`    Industry: ${company.industry}`));
        });
        console.log('');
      }

      if (borrowers.length > 0 && (!type || type === 'borrower')) {
        console.log(chalk.bold('Borrowers:'));
        borrowers.forEach(company => {
          console.log(chalk.cyan(`  ${company.id}`) + chalk.gray(` - ${company.name}`));
          console.log(chalk.gray(`    Industry: ${company.industry}`));
        });
        console.log('');
      }
    } catch (error: any) {
      console.error(chalk.red('Error:'), error.response?.data?.error || error.message);
      process.exit(1);
    }
  });

companyCommand
  .command('get <id>')
  .description('Get a company by id')
  .action(async (id: string, options, command) => {
    try {
      const apiUrl = command.parent.parent.opts().apiUrl;
      const client = getApiClient(apiUrl);
      const company = await client.getCompany(id);
      
      console.log(chalk.bold(`\nCompany: ${company.name}\n`));
      console.log(chalk.gray(`ID: ${company.id}`));
      console.log(chalk.gray(`Type: ${company.type}`));
      console.log(chalk.gray(`Description: ${company.description}`));
      console.log(chalk.gray(`Industry: ${company.industry}`));
      
      console.log(chalk.bold('\nMetadata:\n'));
      Object.entries(company.metadata).forEach(([key, value]) => {
        console.log(chalk.gray(`  ${key}: ${JSON.stringify(value)}`));
      });
      console.log('');
    } catch (error: any) {
      console.error(chalk.red('Error:'), error.response?.data?.error || error.message);
      process.exit(1);
    }
  });

companyCommand
  .command('import')
  .description('Import companies from file')
  .option('-f, --file <path>', 'Path to companies JSON file', 'input/companies/companies.json')
  .action(async (options, command) => {
    try {
      const apiUrl = command.parent.opts().apiUrl;
      const client = getApiClient(apiUrl);

      const file = path.resolve(options.file);
      const companies = fileService.readJSON<Company[]>(file);

      console.log(chalk.bold(`\nImporting ${companies.length} companies from ${path.basename(file)}...\n`));

      let imported = 0;
      let errors = 0;

      for (const company of companies) {
        try {
          await client.createCompany(company);
          console.log(chalk.green(`✓ Imported company: ${company.id} (${company.name})`));
          imported++;
        } catch (error: any) {
          console.log(chalk.red(`✗ Failed to import ${company.id}: ${error.response?.data?.error || error.message}`));
          errors++;
        }
      }

      console.log(chalk.bold(`\nImport complete: ${imported} succeeded, ${errors} failed\n`));
    } catch (error: any) {
      console.error(chalk.red('Error:'), error.message);
      process.exit(1);
    }
  });

companyCommand
  .command('create')
  .description('Create a new company')
  .requiredOption('-i, --id <id>', 'Company ID')
  .requiredOption('-n, --name <name>', 'Company name')
  .requiredOption('-t, --type <type>', 'Company type (lender or borrower)')
  .requiredOption('-d, --description <description>', 'Company description')
  .requiredOption('--industry <industry>', 'Industry')
  .action(async (options, command) => {
    try {
      const apiUrl = command.parent.opts().apiUrl;
      const client = getApiClient(apiUrl);

      if (options.type !== 'lender' && options.type !== 'borrower') {
        throw new Error('Type must be either "lender" or "borrower"');
      }

      const company: Company = {
        id: options.id,
        name: options.name,
        type: options.type,
        description: options.description,
        industry: options.industry,
        createdAt: '',
        modifiedAt: '',
        metadata: {}
      };

      await client.createCompany(company);
      console.log(chalk.green(`✓ Company '${company.id}' created successfully`));
    } catch (error: any) {
      console.error(chalk.red('Error:'), error.response?.data?.error || error.message);
      process.exit(1);
    }
  });

companyCommand
  .command('update <id>')
  .description('Update a company')
  .option('-n, --name <name>', 'Company name')
  .option('-d, --description <description>', 'Company description')
  .option('--industry <industry>', 'Industry')
  .action(async (id: string, options, command) => {
    try {
      const apiUrl = command.parent.parent.opts().apiUrl;
      const client = getApiClient(apiUrl);

      const updates: Partial<Company> = {};
      if (options.name) updates.name = options.name;
      if (options.description) updates.description = options.description;
      if (options.industry) updates.industry = options.industry;

      const updated = await client.updateCompany(id, updates);
      console.log(chalk.green(`✓ Company '${updated.id}' updated successfully`));
    } catch (error: any) {
      console.error(chalk.red('Error:'), error.response?.data?.error || error.message);
      process.exit(1);
    }
  });

companyCommand
  .command('delete <id>')
  .description('Delete a company')
  .action(async (id: string, options, command) => {
    try {
      const apiUrl = command.parent.parent.opts().apiUrl;
      const client = getApiClient(apiUrl);

      await client.deleteCompany(id);
      console.log(chalk.green(`✓ Company '${id}' deleted successfully`));
    } catch (error: any) {
      console.error(chalk.red('Error:'), error.response?.data?.error || error.message);
      process.exit(1);
    }
  });
