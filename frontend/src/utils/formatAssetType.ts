/**
 * Format asset type from snake_case to Title Case
 */
export function formatAssetType(assetType: string | null | undefined): string {
  if (!assetType) return 'Other';

  // Convert snake_case to Title Case
  return assetType
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}
