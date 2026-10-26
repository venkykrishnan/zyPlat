import { Router } from 'express';
import { DomainService } from '../../services/DomainService';
import { FileService } from '../../services/FileService';
import { NotFoundError, ValidationError } from '../middleware/errorHandler';

const router = Router();
const fileService = new FileService();
const domainService = new DomainService(fileService);

router.get('/', (req, res, next) => {
  try {
    const domains = domainService.list();
    res.json(domains);
  } catch (error) {
    next(error);
  }
});

router.get('/:id', (req, res, next) => {
  try {
    const domain = domainService.get(req.params.id);
    res.json(domain);
  } catch (error: any) {
    next(new NotFoundError(error.message));
  }
});

router.post('/', (req, res, next) => {
  try {
    domainService.create(req.body);
    res.status(201).json({ 
      message: 'Domain created successfully',
      id: req.body.id 
    });
  } catch (error: any) {
    next(new ValidationError(error.message));
  }
});

router.put('/:id', (req, res, next) => {
  try {
    const updated = domainService.update(req.params.id, req.body);
    res.json(updated);
  } catch (error: any) {
    next(new NotFoundError(error.message));
  }
});

router.delete('/:id', (req, res, next) => {
  try {
    domainService.delete(req.params.id);
    res.json({ message: 'Domain deleted successfully' });
  } catch (error: any) {
    next(new NotFoundError(error.message));
  }
});

export { router as domainRouter };
