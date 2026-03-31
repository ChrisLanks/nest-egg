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
import { lazy, Suspense, useState } from "react";

const FinancialRatiosTab = lazy(() =>
  import("./FinancialRatiosTab").then((m) => ({ default: m.FinancialRatiosTab })),
);
const LiquidityDashboardTab = lazy(() =>
  import("./LiquidityDashboardTab").then((m) => ({ default: m.LiquidityDashboardTab })),
);
const CreditScoreTab = lazy(() =>
  import("./CreditScoreTab").then((m) => ({ default: m.CreditScoreTab })),
);
const SmartInsightsPage = lazy(() => import("./SmartInsightsPage"));

const TabLoader = () => (
  <Center py={12}>
    <Spinner size="lg" color="brand.500" />
  </Center>
);

const TAB_KEY = "nest-egg-tab-financial-health";
const getInitialTab = () => {
  try { return parseInt(localStorage.getItem(TAB_KEY) ?? "0", 10) || 0; } catch { return 0; }
};

export const FinancialHealthPage = () => {
  const [tabIndex, setTabIndex] = useState(getInitialTab);
  const handleTabChange = (idx: number) => {
    setTabIndex(idx);
    try { localStorage.setItem(TAB_KEY, String(idx)); } catch {}
  };

  return (
    <Box pt={4}>
      <Box px={6} mb={2}>
        <Heading size="lg">Financial Checkup</Heading>
        <Text color="text.secondary" mt={1} fontSize="sm">
          Are you on track? Savings rate, emergency fund coverage, debt-to-income ratio, credit score, and personalized recommendations.
        </Text>
      </Box>
      <Tabs colorScheme="brand" variant="enclosed" px={6} index={tabIndex} onChange={handleTabChange}>
        <TabList>
          <Tab fontSize="sm">Financial Ratios</Tab>
          <Tab fontSize="sm">Liquidity &amp; Emergency Fund</Tab>
          <Tab fontSize="sm">Credit Score</Tab>
          <Tab fontSize="sm">Recommendations</Tab>
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
          <TabPanel px={0}>
            <Suspense fallback={<TabLoader />}>
              <CreditScoreTab />
            </Suspense>
          </TabPanel>
          <TabPanel px={0}>
              <Suspense fallback={<TabLoader />}>
                <SmartInsightsPage />
              </Suspense>
            </TabPanel>
        </TabPanels>
      </Tabs>
    </Box>
  );
};

export default FinancialHealthPage;
