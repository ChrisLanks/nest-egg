/**
 * Holdings Detail Table Component
 *
 * Displays all portfolio holdings in a sortable table with:
 * - Sort by any column
 * - Filter by asset type
 * - Search by ticker/name
 * - Export to CSV
 */

import {
  Box,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Text,
  Badge,
  HStack,
  Input,
  Select,
  Button,
  Icon,
  InputGroup,
  InputLeftElement,
} from '@chakra-ui/react';
import { useState, useMemo } from 'react';
import { FiDownload, FiSearch, FiChevronUp, FiChevronDown } from 'react-icons/fi';
import { formatAssetType } from '../../../utils/formatAssetType';

interface Holding {
  ticker: string;
  name: string | null;
  total_shares: number;
  current_price_per_share: number | null;
  current_total_value: number | null;
  total_cost_basis: number | null;
  gain_loss: number | null;
  gain_loss_percent: number | null;
  asset_type: string | null;
  expense_ratio: number | null;
  annual_fee: number | null;
}

interface HoldingsDetailTableProps {
  holdings: Holding[];
}

type SortField =
  | 'ticker'
  | 'name'
  | 'total_shares'
  | 'current_price_per_share'
  | 'current_total_value'
  | 'total_cost_basis'
  | 'gain_loss'
  | 'gain_loss_percent'
  | 'asset_type'
  | 'expense_ratio'
  | 'annual_fee';

type SortDirection = 'asc' | 'desc';

export const HoldingsDetailTable = ({ holdings }: HoldingsDetailTableProps) => {
  const [sortField, setSortField] = useState<SortField>('current_total_value');
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc');
  const [searchQuery, setSearchQuery] = useState('');
  const [assetTypeFilter, setAssetTypeFilter] = useState<string>('all');

  // Format functions
  const formatCurrency = (amount: number | null) => {
    if (amount === null || amount === undefined) return 'N/A';
    const num = Number(amount);
    if (isNaN(num)) return 'N/A';
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(num);
  };

  const formatPercent = (percent: number | null) => {
    if (percent === null || percent === undefined) return 'N/A';
    const num = Number(percent);
    if (isNaN(num)) return 'N/A';
    return `${num >= 0 ? '+' : ''}${num.toFixed(2)}%`;
  };

  const formatShares = (shares: number) => {
    const num = Number(shares);
    if (isNaN(num)) return '0';
    return new Intl.NumberFormat('en-US', {
      minimumFractionDigits: 0,
      maximumFractionDigits: 6,
    }).format(num);
  };

  // Handle sort
  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      // Default to desc for numeric fields, asc for text fields
      setSortDirection(
        ['ticker', 'name', 'asset_type'].includes(field) ? 'asc' : 'desc'
      );
    }
  };

  // Get unique asset types for filter
  const assetTypes = useMemo(() => {
    const types = new Set(holdings.map((h) => h.asset_type).filter(Boolean));
    return Array.from(types).sort();
  }, [holdings]);

  // Filter and sort holdings
  const processedHoldings = useMemo(() => {
    let filtered = holdings;

    // Apply search filter
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(
        (h) =>
          h.ticker.toLowerCase().includes(query) ||
          h.name?.toLowerCase().includes(query)
      );
    }

    // Apply asset type filter
    if (assetTypeFilter !== 'all') {
      filtered = filtered.filter((h) => h.asset_type === assetTypeFilter);
    }

    // Sort
    const sorted = [...filtered].sort((a, b) => {
      let aVal: any;
      let bVal: any;

      switch (sortField) {
        case 'ticker':
          aVal = a.ticker.toLowerCase();
          bVal = b.ticker.toLowerCase();
          break;
        case 'name':
          aVal = a.name?.toLowerCase() || '';
          bVal = b.name?.toLowerCase() || '';
          break;
        case 'total_shares':
          aVal = Number(a.total_shares);
          bVal = Number(b.total_shares);
          break;
        case 'current_price_per_share':
          aVal = Number(a.current_price_per_share || 0);
          bVal = Number(b.current_price_per_share || 0);
          break;
        case 'current_total_value':
          aVal = Number(a.current_total_value || 0);
          bVal = Number(b.current_total_value || 0);
          break;
        case 'total_cost_basis':
          aVal = Number(a.total_cost_basis || 0);
          bVal = Number(b.total_cost_basis || 0);
          break;
        case 'gain_loss':
          aVal = Number(a.gain_loss || 0);
          bVal = Number(b.gain_loss || 0);
          break;
        case 'gain_loss_percent':
          aVal = Number(a.gain_loss_percent || 0);
          bVal = Number(b.gain_loss_percent || 0);
          break;
        case 'asset_type':
          aVal = a.asset_type?.toLowerCase() || '';
          bVal = b.asset_type?.toLowerCase() || '';
          break;
        default:
          return 0;
      }

      if (aVal < bVal) return sortDirection === 'asc' ? -1 : 1;
      if (aVal > bVal) return sortDirection === 'asc' ? 1 : -1;
      return 0;
    });

    return sorted;
  }, [holdings, searchQuery, assetTypeFilter, sortField, sortDirection]);

  // Export to CSV
  const exportToCSV = () => {
    const headers = [
      'Ticker',
      'Name',
      'Shares',
      'Price',
      'Value',
      'Cost Basis',
      'Gain/Loss',
      'Gain/Loss %',
      'Type',
      'Expense Ratio',
      'Annual Fee',
    ];

    const rows = processedHoldings.map((h) => [
      h.ticker,
      h.name || 'N/A',
      h.total_shares,
      h.current_price_per_share || 0,
      h.current_total_value || 0,
      h.total_cost_basis || 0,
      h.gain_loss || 0,
      h.gain_loss_percent || 0,
      h.asset_type || 'other',
      h.expense_ratio !== null ? (Number(h.expense_ratio) * 100).toFixed(2) + '%' : 'N/A',
      h.annual_fee || 0,
    ]);

    const csv = [
      headers.join(','),
      ...rows.map((row) =>
        row
          .map((cell) =>
            typeof cell === 'string' && cell.includes(',')
              ? `"${cell}"`
              : cell
          )
          .join(',')
      ),
    ].join('\n');

    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `holdings-${new Date().toISOString().split('T')[0]}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  };

  // Render sort icon
  const SortIcon = ({ field }: { field: SortField }) => {
    if (sortField !== field) return null;
    return (
      <Icon
        as={sortDirection === 'asc' ? FiChevronUp : FiChevronDown}
        ml={1}
      />
    );
  };

  // Sortable table header
  const SortableTh = ({
    field,
    children,
    isNumeric,
  }: {
    field: SortField;
    children: React.ReactNode;
    isNumeric?: boolean;
  }) => (
    <Th
      cursor="pointer"
      onClick={() => handleSort(field)}
      isNumeric={isNumeric}
      _hover={{ bg: 'gray.50' }}
      userSelect="none"
    >
      <HStack spacing={1} justify={isNumeric ? 'flex-end' : 'flex-start'}>
        <Text>{children}</Text>
        <SortIcon field={field} />
      </HStack>
    </Th>
  );

  return (
    <Box>
      {/* Filters and Export */}
      <HStack spacing={4} mb={4}>
        <InputGroup flex={1} maxW="400px">
          <InputLeftElement pointerEvents="none">
            <Icon as={FiSearch} color="gray.400" />
          </InputLeftElement>
          <Input
            placeholder="Search by ticker or name..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </InputGroup>

        <Select
          value={assetTypeFilter}
          onChange={(e) => setAssetTypeFilter(e.target.value)}
          maxW="200px"
        >
          <option value="all">All Types</option>
          {assetTypes.map((type) => (
            <option key={type} value={type}>
              {type}
            </option>
          ))}
        </Select>

        <Button
          leftIcon={<Icon as={FiDownload} />}
          onClick={exportToCSV}
          colorScheme="brand"
          variant="outline"
        >
          Export CSV
        </Button>
      </HStack>

      {/* Results count */}
      <Text fontSize="sm" color="gray.600" mb={2}>
        Showing {processedHoldings.length} of {holdings.length} holdings
      </Text>

      {/* Table */}
      <Box overflowX="auto" border="1px" borderColor="gray.200" borderRadius="md">
        <Table variant="simple" size="sm">
          <Thead bg="gray.50">
            <Tr>
              <SortableTh field="ticker">Ticker</SortableTh>
              <SortableTh field="name">Name</SortableTh>
              <SortableTh field="total_shares" isNumeric>
                Shares
              </SortableTh>
              <SortableTh field="current_price_per_share" isNumeric>
                Price
              </SortableTh>
              <SortableTh field="current_total_value" isNumeric>
                Value
              </SortableTh>
              <SortableTh field="total_cost_basis" isNumeric>
                Cost Basis
              </SortableTh>
              <SortableTh field="gain_loss" isNumeric>
                Gain/Loss
              </SortableTh>
              <SortableTh field="gain_loss_percent" isNumeric>
                Gain/Loss %
              </SortableTh>
              <SortableTh field="asset_type">Type</SortableTh>
              <SortableTh field="expense_ratio" isNumeric>
                Expense Ratio
              </SortableTh>
              <SortableTh field="annual_fee" isNumeric>
                Annual Fee
              </SortableTh>
            </Tr>
          </Thead>
          <Tbody>
            {processedHoldings.length === 0 ? (
              <Tr>
                <Td colSpan={11} textAlign="center" py={8} color="gray.500">
                  No holdings match your filters
                </Td>
              </Tr>
            ) : (
              processedHoldings.map((holding, index) => (
                <Tr key={`${holding.ticker}-${index}`} _hover={{ bg: 'gray.50' }}>
                  <Td>
                    <Text fontWeight="bold">{holding.ticker}</Text>
                  </Td>
                  <Td>
                    <Text fontSize="sm" color="gray.600">
                      {holding.name || '-'}
                    </Text>
                  </Td>
                  <Td isNumeric>{formatShares(holding.total_shares)}</Td>
                  <Td isNumeric>
                    {formatCurrency(holding.current_price_per_share)}
                  </Td>
                  <Td isNumeric>
                    <Text fontWeight="semibold">
                      {formatCurrency(holding.current_total_value)}
                    </Text>
                  </Td>
                  <Td isNumeric>
                    {formatCurrency(holding.total_cost_basis)}
                  </Td>
                  <Td isNumeric>
                    <Text
                      color={
                        holding.gain_loss && holding.gain_loss > 0
                          ? 'green.600'
                          : holding.gain_loss && holding.gain_loss < 0
                          ? 'red.600'
                          : 'gray.600'
                      }
                      fontWeight="medium"
                    >
                      {formatCurrency(holding.gain_loss)}
                    </Text>
                  </Td>
                  <Td isNumeric>
                    <Text
                      color={
                        holding.gain_loss_percent &&
                        holding.gain_loss_percent > 0
                          ? 'green.600'
                          : holding.gain_loss_percent &&
                            holding.gain_loss_percent < 0
                          ? 'red.600'
                          : 'gray.600'
                      }
                      fontWeight="medium"
                    >
                      {formatPercent(holding.gain_loss_percent)}
                    </Text>
                  </Td>
                  <Td>
                    {holding.asset_type && (
                      <Badge colorScheme="blue" size="sm">
                        {formatAssetType(holding.asset_type)}
                      </Badge>
                    )}
                  </Td>
                  <Td isNumeric>
                    {holding.expense_ratio !== null && holding.expense_ratio !== undefined
                      ? `${(Number(holding.expense_ratio) * 100).toFixed(2)}%`
                      : '-'}
                  </Td>
                  <Td isNumeric>
                    <Text fontSize="sm" color="gray.600">
                      {formatCurrency(holding.annual_fee)}
                    </Text>
                  </Td>
                </Tr>
              ))
            )}
          </Tbody>
        </Table>
      </Box>
    </Box>
  );
};
