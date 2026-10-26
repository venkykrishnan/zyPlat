import { Command } from 'commander';
import chalk from 'chalk';
import { ApiClient } from '../client/ApiClient';
import { FileService } from '../services/FileService';
import { DomainInstance } from '../models/DomainInstance';
import * as path from 'path';

const getApiClient = (apiUrl?: string) => new ApiClient(apiUrl);
const fileService = new FileService();

export const instanceCommand = new Command('instance')
  .alias('inst')
  .description('Manage domain instances')
  .option('--api-url <url>', 'API base URL', 'http://localhost:3000/api');

instanceCommand
  .command('list')
  .description('List all domain instances')
  .option('-c, --company <companyId>', 'Filter by company ID')
  .option('-d, --domain <domainId>', 'Filter by domain ID')
  .action(async (options, command) => {
    try {
      const apiUrl = command.parent.opts().apiUrl;
      const client = getApiClient(apiUrl);
      const instances = await client.listInstances(options.company, options.domain);
      
      if (instances.length === 0) {
        console.log(chalk.yellow('No domain instances found'));
        return;
      }

      console.log(chalk.bold('\nDomain Instances:\n'));
      instances.forEach(instance => {
        console.log(chalk.cyan(`  ${instance.instanceId}`));
        console.log(chalk.gray(`    Company: ${instance.companyName} (${instance.companyId})`));
        console.log(chalk.gray(`    Domain: ${instance.domainName} (${instance.domainId})`));
        console.log(chalk.gray(`    Data rows: ${instance.data.length}`));
        console.log(chalk.gray(`    Classifications: ${instance.classifications.join(', ')}`));
      });
      console.log('');
    } catch (error: any) {
      console.error(chalk.red('Error:'), error.response?.data?.error || error.message);
      process.exit(1);
    }
  });

instanceCommand
  .command('get <instanceId>')
  .description('Get a domain instance by id')
  .option('-d, --data', 'Show data')
  .option('-l, --limit <limit>', 'Limit data rows', '10')
  .action(async (instanceId: string, options, command) => {
    try {
      const apiUrl = command.parent.parent.opts().apiUrl;
      const client = getApiClient(apiUrl);
      const instance = await client.getInstance(instanceId);
      
      console.log(chalk.bold(`\nDomain Instance: ${instance.instanceId}\n`));
      console.log(chalk.gray(`Company: ${instance.companyName} (${instance.companyId})`));
      console.log(chalk.gray(`Domain: ${instance.domainName} (${instance.domainId})`));
      console.log(chalk.gray(`Classifications: ${instance.classifications.join(', ')}`));
      console.log(chalk.gray(`Data rows: ${instance.data.length}`));

      if (options.data && instance.data.length > 0) {
        const limit = parseInt(options.limit);
        const dataToShow = instance.data.slice(0, limit);
        
        console.log(chalk.bold('\nData (sample):\n'));
        console.log(JSON.stringify(dataToShow, null, 2));
        
        if (instance.data.length > limit) {
          console.log(chalk.gray(`\n... and ${instance.data.length - limit} more rows`));
        }
      }
      console.log('');
    } catch (error: any) {
      console.error(chalk.red('Error:'), error.response?.data?.error || error.message);
      process.exit(1);
    }
  });

instanceCommand
  .command('import')
  .description('Import domain instances from file')
  .option('-f, --file <path>', 'Path to instance JSON file')
  .option('-d, --dir <path>', 'Directory containing instance files', 'input/domain-instances')
  .action(async (options, command) => {
    try {
      const apiUrl = command.parent.opts().apiUrl;
      const client = getApiClient(apiUrl);

      let files: string[] = [];
      if (options.file) {
        files = [path.resolve(options.file)];
      } else {
        const dir = path.resolve(options.dir);
        files = fileService.listFiles(dir);
      }

      console.log(chalk.bold(`\nImporting domain instances from ${files.length} file(s)...\n`));

      let imported = 0;
      let errors = 0;

      for (const file of files) {
        try {
          const instance = fileService.readJSON<DomainInstance>(file);
          await client.createInstance(instance);
          console.log(chalk.green(`✓ Imported instance: ${instance.instanceId}`));
          imported++;
        } catch (error: any) {
          console.log(chalk.red(`✗ Failed to import ${path.basename(file)}: ${error.response?.data?.error || error.message}`));
          errors++;
        }
      }

      console.log(chalk.bold(`\nImport complete: ${imported} succeeded, ${errors} failed\n`));
    } catch (error: any) {
      console.error(chalk.red('Error:'), error.message);
      process.exit(1);
    }
  });

instanceCommand
  .command('delete <instanceId>')
  .description('Delete a domain instance')
  .action(async (instanceId: string, options, command) => {
    try {
      const apiUrl = command.parent.parent.opts().apiUrl;
      const client = getApiClient(apiUrl);

      await client.deleteInstance(instanceId);
      console.log(chalk.green(`✓ Domain instance '${instanceId}' deleted successfully`));
    } catch (error: any) {
      console.error(chalk.red('Error:'), error.response?.data?.error || error.message);
      process.exit(1);
    }
  });
