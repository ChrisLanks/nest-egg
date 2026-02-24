/**
 * Loading skeleton components for various page types
 */

import {
  Box,
  Card,
  CardBody,
  Container,
  HStack,
  SimpleGrid,
  Skeleton,
  Stack,
  VStack,
} from '@chakra-ui/react';

/**
 * Dashboard page loading skeleton with stat cards and charts
 */
export const DashboardSkeleton = () => {
  return (
    <Container maxW="container.xl" py={8}>
      <VStack spacing={8} align="stretch">
        {/* Header */}
        <Box>
          <Skeleton height="32px" width="200px" mb={2} />
          <Skeleton height="20px" width="300px" />
        </Box>

        {/* Summary Stats Grid */}
        <SimpleGrid columns={{ base: 1, md: 2, lg: 4 }} spacing={6}>
          {[1, 2, 3, 4].map((i) => (
            <Card key={i}>
              <CardBody>
                <Stack spacing={3}>
                  <Skeleton height="16px" width="120px" />
                  <Skeleton height="28px" width="150px" />
                  <Skeleton height="14px" width="100px" />
                </Stack>
              </CardBody>
            </Card>
          ))}
        </SimpleGrid>

        {/* Charts Section */}
        <SimpleGrid columns={{ base: 1, lg: 2 }} spacing={6}>
          <Card>
            <CardBody>
              <Skeleton height="24px" width="180px" mb={4} />
              <Skeleton height="300px" />
            </CardBody>
          </Card>

          <Card>
            <CardBody>
              <Skeleton height="24px" width="180px" mb={4} />
              <Skeleton height="300px" />
            </CardBody>
          </Card>
        </SimpleGrid>

        {/* Wide Chart */}
        <Card>
          <CardBody>
            <Skeleton height="24px" width="200px" mb={4} />
            <Skeleton height="350px" />
          </CardBody>
        </Card>
      </VStack>
    </Container>
  );
};

/**
 * Transactions page loading skeleton with filters and table
 */
export const TransactionsSkeleton = () => {
  return (
    <Container maxW="container.xl" py={8}>
      <VStack spacing={6} align="stretch">
        {/* Header */}
        <Box>
          <Skeleton height="32px" width="180px" mb={2} />
          <Skeleton height="20px" width="280px" />
        </Box>

        {/* Filter Controls */}
        <Card>
          <CardBody>
            <HStack spacing={4} flexWrap="wrap">
              <Skeleton height="40px" width="200px" />
              <Skeleton height="40px" width="150px" />
              <Skeleton height="40px" width="150px" />
              <Skeleton height="40px" width="120px" />
            </HStack>
          </CardBody>
        </Card>

        {/* Summary Stats */}
        <SimpleGrid columns={{ base: 1, md: 3 }} spacing={4}>
          {[1, 2, 3].map((i) => (
            <Card key={i}>
              <CardBody>
                <Skeleton height="16px" width="100px" mb={2} />
                <Skeleton height="24px" width="120px" />
              </CardBody>
            </Card>
          ))}
        </SimpleGrid>

        {/* Transaction Groups */}
        {[1, 2, 3].map((group) => (
          <Card key={group}>
            <CardBody>
              <Skeleton height="20px" width="150px" mb={4} />
              <Stack spacing={3}>
                {[1, 2, 3, 4, 5].map((row) => (
                  <HStack key={row} spacing={4} py={2}>
                    <Skeleton height="16px" width="20px" />
                    <Skeleton height="16px" width="100px" />
                    <Skeleton height="16px" flex={1} />
                    <Skeleton height="16px" width="100px" />
                    <Skeleton height="16px" width="80px" />
                  </HStack>
                ))}
              </Stack>
            </CardBody>
          </Card>
        ))}
      </VStack>
    </Container>
  );
};

/**
 * Generic table loading skeleton for list pages
 */
export const TableSkeleton = () => {
  return (
    <Card>
      <CardBody>
        <Stack spacing={3}>
          {/* Table Header */}
          <HStack spacing={4} pb={2} borderBottom="1px solid" borderColor="border.default">
            <Skeleton height="16px" width="20px" />
            <Skeleton height="16px" flex={1} />
            <Skeleton height="16px" width="120px" />
            <Skeleton height="16px" width="100px" />
            <Skeleton height="16px" width="80px" />
          </HStack>

          {/* Table Rows */}
          {[1, 2, 3, 4, 5, 6, 7, 8].map((row) => (
            <HStack key={row} spacing={4} py={2}>
              <Skeleton height="16px" width="20px" />
              <Skeleton height="16px" flex={1} />
              <Skeleton height="16px" width="120px" />
              <Skeleton height="16px" width="100px" />
              <Skeleton height="16px" width="80px" />
            </HStack>
          ))}
        </Stack>
      </CardBody>
    </Card>
  );
};

/**
 * Income/Expenses page loading skeleton with drill-down interface
 */
export const IncomeExpensesSkeleton = () => {
  return (
    <Container maxW="container.xl" py={8}>
      <VStack spacing={6} align="stretch">
        {/* Header */}
        <Box>
          <Skeleton height="32px" width="200px" mb={2} />
          <Skeleton height="20px" width="320px" />
        </Box>

        {/* Controls Row */}
        <HStack spacing={4} flexWrap="wrap">
          <Skeleton height="40px" width="150px" />
          <Skeleton height="40px" width="150px" />
          <Skeleton height="40px" width="200px" />
        </HStack>

        {/* Summary Cards */}
        <SimpleGrid columns={{ base: 1, md: 4 }} spacing={4}>
          {[1, 2, 3, 4].map((i) => (
            <Card key={i}>
              <CardBody>
                <Skeleton height="14px" width="80px" mb={2} />
                <Skeleton height="24px" width="100px" />
              </CardBody>
            </Card>
          ))}
        </SimpleGrid>

        {/* Main Chart */}
        <Card>
          <CardBody>
            <Skeleton height="24px" width="180px" mb={4} />
            <Skeleton height="400px" />
          </CardBody>
        </Card>

        {/* Breakdown Table */}
        <Card>
          <CardBody>
            <Skeleton height="24px" width="160px" mb={4} />
            <Stack spacing={3}>
              {[1, 2, 3, 4, 5, 6].map((row) => (
                <HStack key={row} spacing={4} py={2}>
                  <Skeleton height="16px" flex={1} />
                  <Skeleton height="16px" width="120px" />
                  <Skeleton height="16px" width="80px" />
                  <Skeleton height="16px" width="60px" />
                </HStack>
              ))}
            </Stack>
          </CardBody>
        </Card>
      </VStack>
    </Container>
  );
};

/**
 * Budgets page loading skeleton with progress bars
 */
export const BudgetsSkeleton = () => {
  return (
    <Container maxW="container.xl" py={8}>
      <VStack spacing={6} align="stretch">
        {/* Header */}
        <HStack justify="space-between">
          <Box>
            <Skeleton height="32px" width="150px" mb={2} />
            <Skeleton height="20px" width="250px" />
          </Box>
          <Skeleton height="40px" width="120px" />
        </HStack>

        {/* Summary Stats */}
        <SimpleGrid columns={{ base: 1, md: 3 }} spacing={4}>
          {[1, 2, 3].map((i) => (
            <Card key={i}>
              <CardBody>
                <Skeleton height="16px" width="100px" mb={2} />
                <Skeleton height="28px" width="120px" />
              </CardBody>
            </Card>
          ))}
        </SimpleGrid>

        {/* Budget Cards */}
        {[1, 2, 3, 4].map((i) => (
          <Card key={i}>
            <CardBody>
              <Stack spacing={4}>
                <HStack justify="space-between">
                  <Skeleton height="20px" width="150px" />
                  <Skeleton height="20px" width="100px" />
                </HStack>
                <Skeleton height="8px" />
                <HStack justify="space-between">
                  <Skeleton height="14px" width="120px" />
                  <Skeleton height="14px" width="80px" />
                </HStack>
              </Stack>
            </CardBody>
          </Card>
        ))}
      </VStack>
    </Container>
  );
};

/**
 * Accounts page loading skeleton
 */
export const AccountsSkeleton = () => {
  return (
    <Container maxW="container.xl" py={8}>
      <VStack spacing={6} align="stretch">
        {/* Header */}
        <HStack justify="space-between">
          <Box>
            <Skeleton height="32px" width="150px" mb={2} />
            <Skeleton height="20px" width="280px" />
          </Box>
          <Skeleton height="40px" width="140px" />
        </HStack>

        {/* Net Worth Card */}
        <Card>
          <CardBody>
            <Skeleton height="24px" width="120px" mb={4} />
            <SimpleGrid columns={{ base: 1, md: 3 }} spacing={6}>
              {[1, 2, 3].map((i) => (
                <Box key={i}>
                  <Skeleton height="16px" width="100px" mb={2} />
                  <Skeleton height="32px" width="150px" />
                </Box>
              ))}
            </SimpleGrid>
          </CardBody>
        </Card>

        {/* Account Groups */}
        {['Cash', 'Investment', 'Credit Card', 'Loan'].map((type) => (
          <Box key={type}>
            <Skeleton height="20px" width="120px" mb={3} />
            <SimpleGrid columns={{ base: 1, md: 2 }} spacing={4}>
              {[1, 2].map((i) => (
                <Card key={i}>
                  <CardBody>
                    <HStack justify="space-between" mb={2}>
                      <Skeleton height="20px" width="150px" />
                      <Skeleton height="16px" width="60px" />
                    </HStack>
                    <Skeleton height="28px" width="120px" mb={1} />
                    <Skeleton height="14px" width="100px" />
                  </CardBody>
                </Card>
              ))}
            </SimpleGrid>
          </Box>
        ))}
      </VStack>
    </Container>
  );
};
