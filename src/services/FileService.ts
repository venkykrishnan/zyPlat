import * as fs from 'fs';
import * as path from 'path';

export class FileService {
  private inputDir: string;

  constructor(inputDir: string = './input') {
    this.inputDir = path.resolve(process.cwd(), inputDir);
  }

  readJSON<T>(filePath: string): T {
    const fullPath = path.resolve(filePath);
    if (!fs.existsSync(fullPath)) {
      throw new Error(`File not found: ${fullPath}`);
    }
    const content = fs.readFileSync(fullPath, 'utf-8');
    return JSON.parse(content) as T;
  }

  writeJSON<T>(filePath: string, data: T): void {
    const fullPath = path.resolve(filePath);
    const dir = path.dirname(fullPath);
    
    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true });
    }
    
    fs.writeFileSync(fullPath, JSON.stringify(data, null, 2), 'utf-8');
  }

  deleteFile(filePath: string): void {
    const fullPath = path.resolve(filePath);
    if (fs.existsSync(fullPath)) {
      fs.unlinkSync(fullPath);
    } else {
      throw new Error(`File not found: ${fullPath}`);
    }
  }

  listFiles(directory: string, extension: string = '.json'): string[] {
    const fullPath = path.resolve(directory);
    if (!fs.existsSync(fullPath)) {
      return [];
    }
    
    return fs.readdirSync(fullPath)
      .filter(file => file.endsWith(extension))
      .map(file => path.join(fullPath, file));
  }

  fileExists(filePath: string): boolean {
    return fs.existsSync(path.resolve(filePath));
  }

  getInputPath(...parts: string[]): string {
    return path.join(this.inputDir, ...parts);
  }
}
