// The history endpoint is keyed by the asset's UUID, not its tail number. Callers
// must only build a link when they hold the UUID; a tail-based link would land on
// "Aircraft not found".
export default function historyLink(assetUuid, recordId) {
  return `/app/asset-history/${encodeURIComponent(assetUuid)}#${encodeURIComponent(recordId)}`;
}
