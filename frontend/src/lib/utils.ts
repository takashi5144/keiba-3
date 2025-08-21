export function formatCurrency(value: number): string {
  if (value === null || value === undefined || isNaN(value)) return '-';
  return new Intl.NumberFormat('ja-JP', { style: 'currency', currency: 'JPY', maximumFractionDigits: 0 }).format(value);
}

export function formatPercentage(value: number, digits: number = 1): string {
  if (value === null || value === undefined || isNaN(value)) return '-';
  return `${(value * 100).toFixed(digits)}%`;
}

export function getColorByProbability(probability: number): string {
  if (probability >= 0.4) return 'text-green-600';
  if (probability >= 0.25) return 'text-yellow-600';
  return 'text-gray-700';
}

// Merge classnames utility
export function cn(
  ...classes: Array<string | undefined | null | false>
): string {
  return classes.filter(Boolean).join(' ');
}

// Expected value color helper for badges/labels
export function getColorByExpectedValue(expectedValue: number): string {
  if (expectedValue >= 1.5) return 'bg-green-100 text-green-800';
  if (expectedValue >= 1.2) return 'bg-yellow-100 text-yellow-800';
  return 'bg-gray-100 text-gray-800';
}


