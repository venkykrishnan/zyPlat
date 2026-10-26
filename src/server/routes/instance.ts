import { Router } from 'express';
import { DomainInstanceService } from '../../services/DomainInstanceService';
import { FileService } from '../../services/FileService';
import { NotFoundError, ValidationError } from '../middleware/errorHandler';

const router = Router();
const fileService = new FileService();
const instanceService = new DomainInstanceService(fileService);

router.get('/', (req, res, next) => {
  try {
    const companyId = req.query.companyId as string | undefined;
    const domainId = req.query.domainId as string | undefined;
    const instances = instanceService.list(companyId, domainId);
    res.json(instances);
  } catch (error) {
    next(error);
  }
});

router.get('/:id', (req, res, next) => {
  try {
    const instance = instanceService.get(req.params.id);
    res.json(instance);
  } catch (error: any) {
    next(new NotFoundError(error.message));
  }
});

router.post('/', (req, res, next) => {
  try {
    instanceService.create(req.body);
    res.status(201).json({ 
      message: 'Domain instance created successfully',
      instanceId: req.body.instanceId 
    });
  } catch (error: any) {
    next(new ValidationError(error.message));
  }
});

router.put('/:id', (req, res, next) => {
  try {
    const updated = instanceService.update(req.params.id, req.body);
    res.json(updated);
  } catch (error: any) {
    next(new NotFoundError(error.message));
  }
});

router.delete('/:id', (req, res, next) => {
  try {
    instanceService.delete(req.params.id);
    res.json({ message: 'Domain instance deleted successfully' });
  } catch (error: any) {
    next(new NotFoundError(error.message));
  }
});

router.post('/:id/data', (req, res, next) => {
  try {
    const instance = instanceService.addData(req.params.id, req.body);
    res.json(instance);
  } catch (error: any) {
    next(new ValidationError(error.message));
  }
});

export { router as instanceRouter };
