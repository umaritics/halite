const CONDITION_PATTERNS = [
  { label: 'excessive play', pattern: /\bexcessive\s+play\b/i },
  { label: 'crack', pattern: /\bcrack(?:ed|ing|s)?\b/i },
  { label: 'fracture', pattern: /\bfractur(?:e|ed|es|ing)\b/i },
  { label: 'corrosion', pattern: /\bcorro(?:sion|ded|sive)\b/i },
  { label: 'leak', pattern: /\bleak(?:age|ed|ing|s)?\b/i },
  { label: 'loose', pattern: /\bloos(?:e|eness|ened)\b/i },
  { label: 'wear', pattern: /\b(?:wear|worn)\b/i },
  { label: 'deformation', pattern: /\bdeform(?:ation|ed|ing)?\b/i },
  { label: 'damage', pattern: /\bdamag(?:e|ed|ing)\b/i },
];

export function evidenceKey(record) {
  return String(record?.record_id ?? record?.id ?? '');
}

function normalizedIdentifier(value) {
  return String(value ?? '').trim().toUpperCase();
}

function exactIdentifiers(values) {
  return new Set(values.map(normalizedIdentifier).filter(Boolean));
}

export function resolveRecordAircraft(record, assets = []) {
  const supplied = [record?.tail_number, record?.asset_id, record?.asset_key]
    .map(value => String(value ?? '').trim())
    .filter(Boolean);
  const suppliedIds = exactIdentifiers(supplied);
  const matchedAsset = assets.find(asset => {
    const knownIds = exactIdentifiers([asset?.id, asset?.tail_number]);
    return [...suppliedIds].some(identifier => knownIds.has(identifier));
  });

  return {
    assetId: matchedAsset?.id ?? '',
    label: matchedAsset?.tail_number ?? supplied[0] ?? '',
    identifiers: exactIdentifiers([
      ...supplied,
      matchedAsset?.id,
      matchedAsset?.tail_number,
    ]),
  };
}

export function classifyEvidenceProvenance(record, selectedAssetId, assets = []) {
  const recordAircraft = resolveRecordAircraft(record, assets);
  if (!selectedAssetId) {
    return {
      kind: 'unknown',
      aircraftLabel: recordAircraft.label,
      selectedAircraftLabel: '',
    };
  }

  const selectedAsset = assets.find(asset => normalizedIdentifier(asset?.id) === normalizedIdentifier(selectedAssetId));
  const selectedIdentifiers = exactIdentifiers([
    selectedAssetId,
    selectedAsset?.id,
    selectedAsset?.tail_number,
  ]);
  const sameAircraft = [...recordAircraft.identifiers]
    .some(identifier => selectedIdentifiers.has(identifier));

  if (sameAircraft) {
    return {
      kind: 'same',
      aircraftLabel: recordAircraft.label || selectedAsset?.tail_number || String(selectedAssetId),
      selectedAircraftLabel: selectedAsset?.tail_number || String(selectedAssetId),
    };
  }

  // If the selected UUID has not resolved to an asset, a tail-like record value
  // cannot safely be called a mismatch. We wait for exact known identifiers.
  if (!selectedAsset || recordAircraft.identifiers.size === 0) {
    return {
      kind: 'unknown',
      aircraftLabel: recordAircraft.label,
      selectedAircraftLabel: selectedAsset?.tail_number || String(selectedAssetId),
    };
  }

  return {
    kind: 'other',
    aircraftLabel: recordAircraft.label,
    selectedAircraftLabel: selectedAsset.tail_number || String(selectedAssetId),
  };
}

export function issueLabelsFromText(value) {
  const text = String(value ?? '');
  return CONDITION_PATTERNS
    .filter(({ pattern }) => {
      const match = text.match(pattern);
      if (!match) return false;
      const prefix = text.slice(Math.max(0, (match.index ?? 0) - 32), match.index);
      return !/\b(?:no|not|without|absence\s+of)\s+(?:\w+\s+){0,3}$/i.test(prefix);
    })
    .map(({ label }) => label);
}

export function caseIssueLabels(caseState = {}) {
  return [...new Set([
    ...(caseState.symptoms ?? []),
    ...(caseState.observations ?? []),
  ].flatMap(issueLabelsFromText))];
}

export function recordCondition(record) {
  const supplied = String(record?.part_condition ?? '').trim();
  if (supplied) return supplied;
  return issueLabelsFromText(record?.text).join(' / ');
}

function safeGroupValue(value) {
  return String(value ?? '').trim().toUpperCase();
}

export function groupEvidenceRecords(recordIds, recordsById, selectedAssetId, assets = []) {
  const groups = new Map();

  recordIds.map(String).forEach((recordId, index) => {
    const record = recordsById.get(recordId) ?? null;
    const provenance = classifyEvidenceProvenance(record, selectedAssetId, assets);
    const component = String(record?.part_name ?? '').trim();
    const condition = recordCondition(record);
    const aircraft = provenance.aircraftLabel;
    const hasGroundedGroupFields = Boolean(record && aircraft && component && condition);
    const groupKey = hasGroundedGroupFields
      ? [provenance.kind, safeGroupValue(aircraft), safeGroupValue(component), safeGroupValue(condition)].join('|')
      : `ungrouped|${recordId}`;

    if (!groups.has(groupKey)) {
      groups.set(groupKey, {
        key: groupKey,
        firstIndex: index,
        provenance,
        aircraft,
        component,
        condition,
        records: [],
      });
    }
    groups.get(groupKey).records.push({ recordId, record });
  });

  const provenanceOrder = { same: 0, other: 1, unknown: 2 };
  return [...groups.values()].sort((left, right) => (
    (provenanceOrder[left.provenance.kind] - provenanceOrder[right.provenance.kind])
    || left.firstIndex - right.firstIndex
  ));
}

export function historicalIssueDiff(condition, currentIssues) {
  const historicalIssues = issueLabelsFromText(condition);
  if (historicalIssues.length === 0 || currentIssues.length === 0) return null;
  if (historicalIssues.some(issue => currentIssues.includes(issue))) return null;
  return {
    historical: historicalIssues,
    current: currentIssues,
  };
}
