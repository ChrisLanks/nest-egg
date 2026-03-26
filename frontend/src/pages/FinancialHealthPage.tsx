/**
 * Financial Health — consolidated financial wellness hub.
 * Combines Financial Ratios (DTI, savings rate, housing ratio) and
 * Liquidity / Emergency Fund Dashboard.
 */

import {
  Box,
  Center,
  Heading,
  Spinner,
  Tab,
  TabList,
  TabPanel,
  TabPanels,
  Tabs,
  Text,
} from "@chakra-ui/react";
import { lazy, Suspense } from "react";

const FinancialRatiosTab = lazy(() =>
  import("./FinancialRatiosTab").then((m) => ({ default: m.FinancialRatiosTab })),
);
const LiquidityDashboardTab = lazy(() =>
  import("./LiquidityDashboardTab").then((m) => ({ default: m.LiquidityDashboardTab })),
);

const TabLoader = () => (
  <Center py={12}>
    <Spinner size="lg" color="brand.500" />
  </Center>
);

export const FinancialHealthPage = () => {
  return (
    <Box pt={4}>
      <Box px={6} mb={2}>
        <Heading size="lg">Financial Health</Heading>
        <Text color="text.secondary" mt={1} fontSize="sm">
          Financial ratios, debt-to-income analysis, and emergency fund coverage.
        </Text>
      </Box>
      <Tabs colorScheme="brand" variant="enclosed" px={6}>
        <TabList>
          <Tab fontSize="sm">Financial Ratios</Tab>
          <Tab fontSize="sm">Liquidity &amp; Emergency Fund</Tab>
        </TabList>
        <TabPanels>
          <TabPanel px={0}>
            <Suspense fallback={<TabLoader />}>
              <FinancialRatiosTab />
            </Suspense>
          </TabPanel>
          <TabPanel px={0}>
            <Suspense fallback={<TabLoader />}>
              <LiquidityDashboardTab />
            </Suspense>
          </TabPanel>
        </TabPanels>
      </Tabs>
    </Box>
  );
};

export default FinancialHealthPage;
