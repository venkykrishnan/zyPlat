import { Router } from 'express';
import { TaxonomyService } from '../../services/TaxonomyService';
import { FileService } from '../../services/FileService';
import { NotFoundError, ValidationError } from '../middleware/errorHandler';

const router = Router();
const fileService = new FileService();
const taxonomyService = new TaxonomyService(fileService);

router.get('/', (req, res, next) => {
  try {
    const taxonomies = taxonomyService.list();
    res.json(taxonomies);
  } catch (error) {
    next(error);
  }
});

router.get('/:id', (req, res, next) => {
  try {
    const taxonomy = taxonomyService.get(req.params.id);
    res.json(taxonomy);
  } catch (error: any) {
    next(new NotFoundError(error.message));
  }
});

router.post('/', (req, res, next) => {
  try {
    taxonomyService.create(req.body);
    res.status(201).json({ 
      message: 'Taxonomy created successfully',
      id: req.body.id 
    });
  } catch (error: any) {
    next(new ValidationError(error.message));
  }
});

router.put('/:id', (req, res, next) => {
  try {
    const updated = taxonomyService.update(req.params.id, req.body);
    res.json(updated);
  } catch (error: any) {
    next(new NotFoundError(error.message));
  }
});

router.delete('/:id', (req, res, next) => {
  try {
    taxonomyService.delete(req.params.id);
    res.json({ message: 'Taxonomy deleted successfully' });
  } catch (error: any) {
    next(new NotFoundError(error.message));
  }
});

router.post('/:id/entities', (req, res, next) => {
  try {
    const taxonomy = taxonomyService.addEntity(req.params.id, req.body);
    res.status(201).json(taxonomy);
  } catch (error: any) {
    next(new ValidationError(error.message));
  }
});

router.put('/:taxonomyId/entities/:entityId', (req, res, next) => {
  try {
    const taxonomy = taxonomyService.updateEntity(
      req.params.taxonomyId,
      req.params.entityId,
      req.body
    );
    res.json(taxonomy);
  } catch (error: any) {
    next(new NotFoundError(error.message));
  }
});

router.delete('/:taxonomyId/entities/:entityId', (req, res, next) => {
  try {
    const taxonomy = taxonomyService.deleteEntity(
      req.params.taxonomyId,
      req.params.entityId
    );
    res.json(taxonomy);
  } catch (error: any) {
    next(new ValidationError(error.message));
  }
});

export { router as taxonomyRouter };
