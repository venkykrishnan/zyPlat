import { Command } from 'commander';
import chalk from 'chalk';
import { DomainInstanceService } from '../services/DomainInstanceService';
import { FileService } from '../services/FileService';

const fileService = new FileService();
const instanceService = new DomainInstanceService(fileService);

export const instanceCommand = new Command('instance')
  .alias('inst')
  .description('Manage domain instances');

instanceCommand
  .command('list')
  .description('List all domain instances')
  .option('-c, --company <companyId>', 'Filter by company ID')
  .option('-d, --domain <domainId>', 'Filter by domain ID')
  .action((options) => {
    try {
      const instances = instanceService.list(options.company, options.domain);
      
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
      console.error(chalk.red('Error:'), error.message);
      process.exit(1);
    }
  });

instanceCommand
  .command('get <instanceId>')
  .description('Get a domain instance by id')
  .option('-d, --data', 'Show data')
  .option('-l, --limit <limit>', 'Limit data rows', '10')
  .action((instanceId: string, options) => {
    try {
      const instance = instanceService.get(instanceId);
      
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
      console.error(chalk.red('Error:'), error.message);
      process.exit(1);
    }
  });

instanceCommand
  .command('delete <instanceId>')
  .description('Delete a domain instance')
  .action((instanceId: string) => {
    try {
      instanceService.delete(instanceId);
      console.log(chalk.green(`✓ Domain instance '${instanceId}' deleted successfully`));
    } catch (error: any) {
      console.error(chalk.red('Error:'), error.message);
      process.exit(1);
    }
  });
