import { Command } from 'commander';
import chalk from 'chalk';
import { TaxonomyService } from '../services/TaxonomyService';
import { FileService } from '../services/FileService';
import { Taxonomy, TaxonomyEntity } from '../models/Taxonomy';

const fileService = new FileService();
const taxonomyService = new TaxonomyService(fileService);

export const taxonomyCommand = new Command('taxonomy')
  .alias('tax')
  .description('Manage taxonomies');

taxonomyCommand
  .command('list')
  .description('List all taxonomies')
  .action(() => {
    try {
      const taxonomies = taxonomyService.list();
      
      if (taxonomies.length === 0) {
        console.log(chalk.yellow('No taxonomies found'));
        return;
      }

      console.log(chalk.bold('\nTaxonomies:\n'));
      taxonomies.forEach(tax => {
        console.log(chalk.cyan(`  ${tax.id}`) + chalk.gray(` (${tax.name})`));
        console.log(chalk.gray(`    Hierarchical: ${tax.isHierarchical}, Entities: ${tax.entities.length}, Version: ${tax.version}`));
      });
      console.log('');
    } catch (error: any) {
      console.error(chalk.red('Error:'), error.message);
      process.exit(1);
    }
  });

taxonomyCommand
  .command('get <id>')
  .description('Get a taxonomy by id')
  .option('-e, --entities', 'Show entities')
  .action((id: string, options) => {
    try {
      const taxonomy = taxonomyService.get(id);
      
      console.log(chalk.bold(`\nTaxonomy: ${taxonomy.name}\n`));
      console.log(chalk.gray(`ID: ${taxonomy.id}`));
      console.log(chalk.gray(`Description: ${taxonomy.description}`));
      console.log(chalk.gray(`Hierarchical: ${taxonomy.isHierarchical}`));
      console.log(chalk.gray(`Classifications: ${taxonomy.classifications.join(', ')}`));
      console.log(chalk.gray(`Version: ${taxonomy.version}`));
      console.log(chalk.gray(`Published: ${taxonomy.isPublished}`));
      console.log(chalk.gray(`Entities: ${taxonomy.entities.length}`));

      if (options.entities) {
        console.log(chalk.bold('\nEntities:\n'));
        taxonomy.entities.forEach(entity => {
          const indent = entity.parent ? '  ' : '';
          console.log(chalk.cyan(`${indent}${entity.id}`) + chalk.gray(` - ${entity.displayName}`));
          if (entity.parent) {
            console.log(chalk.gray(`${indent}  Parent: ${entity.parent}`));
          }
          if (entity.classifications.length > 0) {
            console.log(chalk.gray(`${indent}  Classifications: ${entity.classifications.join(', ')}`));
          }
        });
      }
      console.log('');
    } catch (error: any) {
      console.error(chalk.red('Error:'), error.message);
      process.exit(1);
    }
  });

taxonomyCommand
  .command('create')
  .description('Create a new taxonomy')
  .requiredOption('-i, --id <id>', 'Taxonomy ID')
  .requiredOption('-n, --name <name>', 'Taxonomy name')
  .requiredOption('-d, --description <description>', 'Taxonomy description')
  .option('-h, --hierarchical', 'Is hierarchical', false)
  .option('-c, --classifications <classifications>', 'Comma-separated classifications', 'CIQ')
  .action((options) => {
    try {
      const taxonomy: Taxonomy = {
        id: options.id,
        name: options.name,
        description: options.description,
        isHierarchical: options.hierarchical,
        classifications: options.classifications.split(',').map((s: string) => s.trim()),
        version: '1.0.0',
        isPublished: true,
        createdAt: '',
        modifiedAt: '',
        entities: []
      };

      taxonomyService.create(taxonomy);
      console.log(chalk.green(`✓ Taxonomy '${taxonomy.id}' created successfully`));
    } catch (error: any) {
      console.error(chalk.red('Error:'), error.message);
      process.exit(1);
    }
  });

taxonomyCommand
  .command('update <id>')
  .description('Update a taxonomy')
  .option('-n, --name <name>', 'Taxonomy name')
  .option('-d, --description <description>', 'Taxonomy description')
  .option('-p, --publish', 'Publish taxonomy')
  .action((id: string, options) => {
    try {
      const updates: Partial<Taxonomy> = {};
      
      if (options.name) updates.name = options.name;
      if (options.description) updates.description = options.description;
      if (options.publish !== undefined) updates.isPublished = true;

      const updated = taxonomyService.update(id, updates);
      console.log(chalk.green(`✓ Taxonomy '${updated.id}' updated successfully`));
    } catch (error: any) {
      console.error(chalk.red('Error:'), error.message);
      process.exit(1);
    }
  });

taxonomyCommand
  .command('delete <id>')
  .description('Delete a taxonomy')
  .action((id: string) => {
    try {
      taxonomyService.delete(id);
      console.log(chalk.green(`✓ Taxonomy '${id}' deleted successfully`));
    } catch (error: any) {
      console.error(chalk.red('Error:'), error.message);
      process.exit(1);
    }
  });

taxonomyCommand
  .command('add-entity <taxonomyId>')
  .description('Add an entity to a taxonomy')
  .requiredOption('-i, --id <id>', 'Entity ID')
  .requiredOption('-v, --value <value>', 'Entity value')
  .requiredOption('-n, --name <name>', 'Display name')
  .option('-d, --description <description>', 'Description', '')
  .option('-p, --parent <parent>', 'Parent entity ID')
  .option('-c, --classifications <classifications>', 'Comma-separated classifications')
  .action((taxonomyId: string, options) => {
    try {
      const taxonomy = taxonomyService.get(taxonomyId);
      
      const entity: TaxonomyEntity = {
        id: options.id,
        value: options.value,
        description: options.description,
        displayName: options.name,
        classifications: options.classifications 
          ? options.classifications.split(',').map((s: string) => s.trim())
          : taxonomy.classifications,
        aliases: [],
        keywords: [],
        parent: options.parent || null,
        isRoot: !options.parent
      };

      taxonomyService.addEntity(taxonomyId, entity);
      console.log(chalk.green(`✓ Entity '${entity.id}' added to taxonomy '${taxonomyId}'`));
    } catch (error: any) {
      console.error(chalk.red('Error:'), error.message);
      process.exit(1);
    }
  });

taxonomyCommand
  .command('delete-entity <taxonomyId> <entityId>')
  .description('Delete an entity from a taxonomy')
  .action((taxonomyId: string, entityId: string) => {
    try {
      taxonomyService.deleteEntity(taxonomyId, entityId);
      console.log(chalk.green(`✓ Entity '${entityId}' deleted from taxonomy '${taxonomyId}'`));
    } catch (error: any) {
      console.error(chalk.red('Error:'), error.message);
      process.exit(1);
    }
  });
