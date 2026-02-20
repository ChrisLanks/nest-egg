import {
  Badge,
  Card,
  CardBody,
  Heading,
  HStack,
  Icon,
  Table,
  Tbody,
  Td,
  Text,
  Th,
  Thead,
  Tr,
} from '@chakra-ui/react';
import { useQuery } from '@tanstack/react-query';
import { useMemo, useState } from 'react';
import { MdArrowDownward, MdArrowUpward } from 'react-icons/md';
import { useUserView } from '../../../contexts/UserViewContext';
import api from '../../../services/api';

type SortKey = 'name' | 'type' | 'institution' | 'balance';
type SortDir = 'asc' | 'desc';

const SORT_KEY = 'account-balances-sort-key';
const SORT_DIR = 'account-balances-sort-dir';

const formatCurrency = (amount: number) =>
  new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(amount);

interface Account {
  id: string;
  name: string;
  type: string;
  institution: string | null;
  balance: number;
}

export const AccountBalancesWidget: React.FC = () => {
  const { selectedUserId } = useUserView();

  const [sortKey, setSortKey] = useState<SortKey>(() => {
    return (localStorage.getItem(SORT_KEY) as SortKey) || 'balance';
  });
  const [sortDir, setSortDir] = useState<SortDir>(() => {
    return (localStorage.getItem(SORT_DIR) as SortDir) || 'desc';
  });

  const { data } = useQuery({
    queryKey: ['dashboard', selectedUserId],
    queryFn: async () => {
      const params = selectedUserId ? { user_id: selectedUserId } : {};
      const response = await api.get('/dashboard/', { params });
      return response.data;
    },
  });

  const handleSort = (key: SortKey) => {
    if (key === sortKey) {
      const next: SortDir = sortDir === 'asc' ? 'desc' : 'asc';
      setSortDir(next);
      localStorage.setItem(SORT_DIR, next);
    } else {
      setSortKey(key);
      setSortDir('desc');
      localStorage.setItem(SORT_KEY, key);
      localStorage.setItem(SORT_DIR, 'desc');
    }
  };

  const sortedAccounts = useMemo(() => {
    if (!data?.account_balances) return [];
    return [...data.account_balances].sort((a: Account, b: Account) => {
      let cmp = 0;
      if (sortKey === 'balance') {
        cmp = a.balance - b.balance;
      } else if (sortKey === 'name') {
        cmp = a.name.localeCompare(b.name);
      } else if (sortKey === 'type') {
        cmp = a.type.localeCompare(b.type);
      } else if (sortKey === 'institution') {
        cmp = (a.institution || 'Manual').localeCompare(b.institution || 'Manual');
      }
      return sortDir === 'asc' ? cmp : -cmp;
    });
  }, [data?.account_balances, sortKey, sortDir]);

  if (sortedAccounts.length === 0) return null;

  const SortIcon = ({ col }: { col: SortKey }) => {
    if (col !== sortKey) return null;
    return (
      <Icon
        as={sortDir === 'asc' ? MdArrowUpward : MdArrowDownward}
        boxSize={3}
        ml={1}
        verticalAlign="middle"
      />
    );
  };

  const sortableTh = (col: SortKey, label: string, isNumeric = false) => (
    <Th
      isNumeric={isNumeric}
      cursor="pointer"
      userSelect="none"
      onClick={() => handleSort(col)}
      _hover={{ color: 'brand.500' }}
      color={sortKey === col ? 'brand.600' : undefined}
      whiteSpace="nowrap"
    >
      <HStack spacing={0} justify={isNumeric ? 'flex-end' : 'flex-start'} display="inline-flex">
        <Text as="span">{label}</Text>
        <SortIcon col={col} />
      </HStack>
    </Th>
  );

  return (
    <Card>
      <CardBody>
        <Heading size="md" mb={4}>
          Account Balances
        </Heading>
        <Table variant="simple" size="sm">
          <Thead>
            <Tr>
              {sortableTh('name', 'Account')}
              {sortableTh('type', 'Type')}
              {sortableTh('institution', 'Institution')}
              {sortableTh('balance', 'Balance', true)}
            </Tr>
          </Thead>
          <Tbody>
            {sortedAccounts.map((account: Account) => (
              <Tr key={account.id}>
                <Td fontWeight="medium">{account.name}</Td>
                <Td>
                  <Badge>{account.type.replace(/_/g, ' ')}</Badge>
                </Td>
                <Td color="gray.600">{account.institution || 'Manual'}</Td>
                <Td isNumeric fontWeight="bold">
                  {formatCurrency(account.balance)}
                </Td>
              </Tr>
            ))}
          </Tbody>
        </Table>
      </CardBody>
    </Card>
  );
};
