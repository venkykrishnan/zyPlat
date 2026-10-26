import { Command } from 'commander';
import chalk from 'chalk';
import { DomainService } from '../services/DomainService';
import { FileService } from '../services/FileService';
import { Domain } from '../models/Domain';

const fileService = new FileService();
const domainService = new DomainService(fileService);

export const domainCommand = new Command('domain')
  .alias('dom')
  .description('Manage domains');

domainCommand
  .command('list')
  .description('List all domains')
  .action(() => {
    try {
      const domains = domainService.list();
      
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
      console.error(chalk.red('Error:'), error.message);
      process.exit(1);
    }
  });

domainCommand
  .command('get <id>')
  .description('Get a domain by id')
  .option('-s, --schema', 'Show data schema')
  .action((id: string, options) => {
    try {
      const domain = domainService.get(id);
      
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
      console.error(chalk.red('Error:'), error.message);
      process.exit(1);
    }
  });

domainCommand
  .command('delete <id>')
  .description('Delete a domain')
  .action((id: string) => {
    try {
      domainService.delete(id);
      console.log(chalk.green(`✓ Domain '${id}' deleted successfully`));
    } catch (error: any) {
      console.error(chalk.red('Error:'), error.message);
      process.exit(1);
    }
  });
