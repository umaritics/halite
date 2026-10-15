# Frontend owner handoff: Review Queue test gate

Date reproduced: 2026-10-15<br>
Reporter: Muhammad Usman Al Haq<br>
Required owner: Shahmeer Atif<br>
Branch/SHA tested: `usman` / `e569ea881470ab6166e0d6e6888b60b8db66763b`<br>
Status: **OPEN - mandatory CI failure**

## Failure

- Test: `frontend/src/test/ReviewQueue.test.jsx` - `ReviewQueue > renders queued item and pruning line`
- Exact root error: `TypeError: maintenanceAPI.getRecord is not a function`
- Call site: `frontend/src/pages/ReviewQueue.jsx:52`
- Downstream assertion failure: `Unable to find an element with the text: INCOMING RECORD`
- Local result: 12 passed, 1 failed; one unhandled error.
- Hosted result: [frontend job 116589585616](https://github.com/umaritics/halite/actions/runs/38783534592/job/116589585616) failed.

## Cause and expected contract

The test replaces the complete `maintenanceAPI` object but its mock defines `reviewQueue`, `submitRecord`, `assetHistory`, `accept`, and `reject` only. The page now also calls:

```js
maintenanceAPI.getRecord(activeRecord.record_id)
```

The real adapter contract in `frontend/src/api/client.js` is `getRecord(id) -> GET /maintenance/records/{id}`. The mock must therefore provide a resolved Axios-like object `{ data: <record-detail> }`. The detail used by the page must contain the incoming record and the conflict fields rendered by the current component; preserve the existing mocked candidate count, prior record, classification/rationale, and history count expectations.

## Reproduction

```powershell
cd frontend
npm ci
npm test -- --run
```

## Required owner action

1. In Shahmeer's frontend branch, add `getRecord: vi.fn()` to the mocked `maintenanceAPI`.
2. Configure `getRecord.mockResolvedValue({ data: ... })` with the response shape consumed by `ReviewQueue.jsx`.
3. Do not remove, skip, weaken, or quarantine the test.
4. Run the complete frontend suite and `npm run build`.
5. Integrate through the team's normal reviewed branch process and rerun hosted CI.

## Acceptance criteria

- No unhandled exception is emitted.
- `INCOMING RECORD`, the pruning line, and the rationale render from mocked API responses.
- All 13 current frontend tests pass.
- The production build passes.
- The GitHub frontend job and overall required workflow are green.

No Shahmeer-owned frontend source, adapter, or test file was modified during Usman's audit.
