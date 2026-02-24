import {
  Badge,
  Box,
  Card,
  CardBody,
  Divider,
  Heading,
  HStack,
  Link,
  Spinner,
  Text,
  VStack,
  useColorModeValue,
} from '@chakra-ui/react';
import { useQuery } from '@tanstack/react-query';
import { Link as RouterLink } from 'react-router-dom';
import { recurringTransactionsApi } from '../../../api/recurring-transactions';
import type { UpcomingBill } from '../../../types/recurring-transaction';

const formatCurrency = (amount: number) =>
  new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount);

export const UpcomingBillsWidget: React.FC = () => {
  const isDark = useColorModeValue(false, true);

  const urgencyProps = (
    bill: UpcomingBill
  ): { badge: string; color: string; bg: string } => {
    if (bill.is_overdue) return { badge: 'Overdue', color: isDark ? 'red.200' : 'red.700', bg: isDark ? 'red.900' : 'red.50' };
    if (bill.days_until_due <= 3) return { badge: `${bill.days_until_due}d`, color: isDark ? 'orange.200' : 'orange.700', bg: isDark ? 'orange.900' : 'orange.50' };
    if (bill.days_until_due <= 7) return { badge: `${bill.days_until_due}d`, color: isDark ? 'yellow.200' : 'yellow.700', bg: isDark ? 'yellow.900' : 'yellow.50' };
    return { badge: `${bill.days_until_due}d`, color: 'text.secondary', bg: 'bg.subtle' };
  };
  const { data: bills, isLoading } = useQuery({
    queryKey: ['upcoming-bills'],
    queryFn: () => recurringTransactionsApi.getUpcomingBills(30),
  });

  if (isLoading) {
    return (
      <Card h="100%">
        <CardBody display="flex" alignItems="center" justifyContent="center">
          <Spinner />
        </CardBody>
      </Card>
    );
  }

  const sorted = (bills ?? []).slice().sort((a, b) => {
    if (a.is_overdue && !b.is_overdue) return -1;
    if (!a.is_overdue && b.is_overdue) return 1;
    return a.days_until_due - b.days_until_due;
  });

  return (
    <Card h="100%">
      <CardBody>
        <HStack justify="space-between" mb={4}>
          <Heading size="md">Upcoming Bills</Heading>
          <Link as={RouterLink} to="/bill-calendar" fontSize="sm" color="brand.500">
            Calendar →
          </Link>
        </HStack>

        {sorted.length === 0 ? (
          <Text color="text.muted" fontSize="sm">
            No bills due in the next 30 days.
          </Text>
        ) : (
          <VStack align="stretch" spacing={0}>
            {sorted.slice(0, 6).map((bill, index) => {
              const { badge, color, bg } = urgencyProps(bill);
              return (
                <Box key={bill.recurring_transaction_id}>
                  <HStack justify="space-between" py={2.5} px={1}>
                    <VStack align="start" spacing={0} flex={1} minW={0}>
                      <Text fontWeight="medium" fontSize="sm" noOfLines={1}>
                        {bill.merchant_name}
                      </Text>
                      <Text fontSize="xs" color="text.muted">
                        {bill.is_overdue
                          ? 'Was due ' + new Date(bill.next_expected_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
                          : 'Due ' + new Date(bill.next_expected_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                      </Text>
                    </VStack>
                    <HStack spacing={2} flexShrink={0}>
                      <Text fontWeight="bold" fontSize="sm">
                        {formatCurrency(Math.abs(bill.average_amount))}
                      </Text>
                      <Badge
                        fontSize="xs"
                        px={2}
                        py={0.5}
                        borderRadius="full"
                        color={color}
                        bg={bg}
                        fontWeight="semibold"
                      >
                        {badge}
                      </Badge>
                    </HStack>
                  </HStack>
                  {index < Math.min(sorted.length, 6) - 1 && <Divider />}
                </Box>
              );
            })}
          </VStack>
        )}
      </CardBody>
    </Card>
  );
};
