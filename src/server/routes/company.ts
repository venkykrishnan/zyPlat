import { Router } from 'express';
import { CompanyService } from '../../services/CompanyService';
import { FileService } from '../../services/FileService';
import { NotFoundError, ValidationError } from '../middleware/errorHandler';

const router = Router();
const fileService = new FileService();
const companyService = new CompanyService(fileService);

router.get('/', (req, res, next) => {
  try {
    const type = req.query.type as 'lender' | 'borrower' | undefined;
    const companies = companyService.list(type);
    res.json(companies);
  } catch (error) {
    next(error);
  }
});

router.get('/:id', (req, res, next) => {
  try {
    const company = companyService.get(req.params.id);
    res.json(company);
  } catch (error: any) {
    next(new NotFoundError(error.message));
  }
});

router.post('/', (req, res, next) => {
  try {
    companyService.create(req.body);
    res.status(201).json({ 
      message: 'Company created successfully',
      id: req.body.id 
    });
  } catch (error: any) {
    next(new ValidationError(error.message));
  }
});

router.put('/:id', (req, res, next) => {
  try {
    const updated = companyService.update(req.params.id, req.body);
    res.json(updated);
  } catch (error: any) {
    next(new NotFoundError(error.message));
  }
});

router.delete('/:id', (req, res, next) => {
  try {
    companyService.delete(req.params.id);
    res.json({ message: 'Company deleted successfully' });
  } catch (error: any) {
    next(new NotFoundError(error.message));
  }
});

export { router as companyRouter };
