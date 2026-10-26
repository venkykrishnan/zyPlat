import { Command } from 'commander';
import chalk from 'chalk';
import { ApiClient } from '../client/ApiClient';
import { FileService } from '../services/FileService';
import { Domain } from '../models/Domain';
import * as path from 'path';

const getApiClient = (apiUrl?: string) => new ApiClient(apiUrl);
const fileService = new FileService();

export const domainCommand = new Command('domain')
  .alias('dom')
  .description('Manage domains')
  .option('--api-url <url>', 'API base URL', 'http://localhost:3000/api');

domainCommand
  .command('list')
  .description('List all domains')
  .action(async (options, command) => {
    try {
      const apiUrl = command.parent.opts().apiUrl;
      const client = getApiClient(apiUrl);
      const domains = await client.listDomains();
      
      if (domains.length === 0) {
        console.log(chalk.yellow('No domains found'));
        return;
      }

      console.log(chalk.bold('\nDomains:\n'));
      domains.forEach(domain => {
        console.log(chalk.cyan(`  ${domain.id}`) + chalk.gray(` (${domain.name})`));
        console.log(chalk.gray(`    Time Series: ${domain.isTimeSeries}, Configurable: ${domain.isConfigurable}, Version: ${domain.version}`));
      });
      console.log('');
    } catch (error: any) {
      console.error(chalk.red('Error:'), error.response?.data?.error || error.message);
      process.exit(1);
    }
  });

domainCommand
  .command('get <id>')
  .description('Get a domain by id')
  .option('-s, --schema', 'Show data schema')
  .action(async (id: string, options, command) => {
    try {
      const apiUrl = command.parent.parent.opts().apiUrl;
      const client = getApiClient(apiUrl);
      const domain = await client.getDomain(id);
      
      console.log(chalk.bold(`\nDomain: ${domain.name}\n`));
      console.log(chalk.gray(`ID: ${domain.id}`));
      console.log(chalk.gray(`Description: ${domain.description}`));
      console.log(chalk.gray(`Time Series: ${domain.isTimeSeries}`));
      console.log(chalk.gray(`Configurable: ${domain.isConfigurable}`));
      console.log(chalk.gray(`Version: ${domain.version}`));

      if (options.schema) {
        console.log(chalk.bold('\nDimensions:\n'));
        domain.dataSchema.dimensions.forEach(dim => {
          console.log(chalk.cyan(`  ${dim.name}`) + chalk.gray(` (${dim.type})`));
          if (dim.taxonomyRef) {
            console.log(chalk.gray(`    Taxonomy: ${dim.taxonomyRef.taxonomyId} v${dim.taxonomyRef.version}`));
          }
        });

        console.log(chalk.bold('\nMetrics:\n'));
        domain.dataSchema.metrics.forEach(metric => {
          console.log(chalk.cyan(`  ${metric.name}`) + chalk.gray(` (${metric.type})`));
          console.log(chalk.gray(`    Point in Time: ${metric.isPointInTime}`));
        });
      }
      console.log('');
    } catch (error: any) {
      console.error(chalk.red('Error:'), error.response?.data?.error || error.message);
      process.exit(1);
    }
  });

domainCommand
  .command('import')
  .description('Import domains from file')
  .option('-f, --file <path>', 'Path to domain JSON file')
  .option('-d, --dir <path>', 'Directory containing domain files', 'input/domains')
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

      console.log(chalk.bold(`\nImporting domains from ${files.length} file(s)...\n`));

      let imported = 0;
      let errors = 0;

      for (const file of files) {
        try {
          const domain = fileService.readJSON<Domain>(file);
          await client.createDomain(domain);
          console.log(chalk.green(`✓ Imported domain: ${domain.id}`));
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

domainCommand
  .command('delete <id>')
  .description('Delete a domain')
  .action(async (id: string, options, command) => {
    try {
      const apiUrl = command.parent.parent.opts().apiUrl;
      const client = getApiClient(apiUrl);

      await client.deleteDomain(id);
      console.log(chalk.green(`✓ Domain '${id}' deleted successfully`));
    } catch (error: any) {
      console.error(chalk.red('Error:'), error.response?.data?.error || error.message);
      process.exit(1);
    }
  });
