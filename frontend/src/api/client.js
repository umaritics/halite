// Barrel kept so existing imports and test mocks of '../api/client' keep working.
import api from './http';
import { assetsAPI } from '../features/assets/api';
import { integrityAPI } from '../features/integrity/api';
import { intakeAPI } from '../features/intake/api';

export {
  setSessionTokenGetter,
  setRefreshSessionHandler,
  resolveClientBearerToken,
  applyAuthHeaders,
} from './http';
export { graphAPI } from '../features/graph/api';
export { authAPI } from '../features/auth/api';
export { adminAPI, healthAPI } from '../features/admin/api';

export const maintenanceAPI = {
  ingest: intakeAPI.ingest,
  ingestFile: intakeAPI.ingestFile,
  submitRecord: intakeAPI.submitRecord,
  records: assetsAPI.records,
  getRecord: integrityAPI.getRecord,
  assets: assetsAPI.assets,
  assetHistory: assetsAPI.assetHistory,
  reviewQueue: integrityAPI.reviewQueue,
  analysisStatus: integrityAPI.analysisStatus,
  corrections: integrityAPI.corrections,
  accept: integrityAPI.accept,
  reject: integrityAPI.reject,
};

export default api;
