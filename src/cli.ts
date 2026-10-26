#!/usr/bin/env node

import { Command } from 'commander';
import { taxonomyCommand } from './commands/taxonomy';
import { domainCommand } from './commands/domain';
import { companyCommand } from './commands/company';
import { instanceCommand } from './commands/instance';

const program = new Command();

program
  .name('zyplat')
  .description('CLI tool for managing taxonomies, domains, companies, and domain instances')
  .version('1.0.0');

program.addCommand(taxonomyCommand);
program.addCommand(domainCommand);
program.addCommand(companyCommand);
program.addCommand(instanceCommand);

program.parse(process.argv);
