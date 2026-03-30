/**
 * Calculators — consolidated advanced planning calculators hub.
 *
 * Combines FIRE metrics, Loan Modeler, HSA Optimizer, Employer Match,
 * What-If Scenarios, Bond Ladder, Equity Compensation, Tax-Equivalent Yield,
 * Asset Location, and Cost Basis Aging into a single tabbed view.
 *
 * Tab order: approachable tools first (FIRE, Loan, HSA, Match, What-If),
 * advanced tools last (Equity Comp, Tax-Equiv, Asset Location, Cost Basis, Bond Ladder).
 *
 * Note: Dividend Calendar has moved to the main Calendar page.
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

const FireMetricsPage = lazy(() =>
  import("./FireMetricsPage").then((m) => ({ default: m.FireMetricsPage })),
);
const EquityPage = lazy(() => import("./EquityPage"));
const LoanModelerPage = lazy(() => import("./LoanModelerPage"));
const HsaPage = lazy(() => import("./HsaPage"));
const TaxEquivYieldTab = lazy(() =>
  import("./TaxEquivYieldTab").then((m) => ({ default: m.TaxEquivYieldTab })),
);
const AssetLocationTab = lazy(() =>
  import("./AssetLocationTab").then((m) => ({ default: m.AssetLocationTab })),
);
const EmployerMatchTab = lazy(() =>
  import("./EmployerMatchTab").then((m) => ({ default: m.EmployerMatchTab })),
);
const CostBasisAgingTab = lazy(() =>
  import("./CostBasisAgingTab").then((m) => ({ default: m.CostBasisAgingTab })),
);
const WhatIfPage = lazy(() => import("./WhatIfPage"));
const BondLadderPage = lazy(() => import("./BondLadderPage"));

const TabLoader = () => (
  <Center py={12}>
    <Spinner size="lg" color="brand.500" />
  </Center>
);

const TAB_KEY = "nest-egg-tab-investment-tools";
const getInitialTab = () => {
  try { return parseInt(localStorage.getItem(TAB_KEY) ?? "0", 10) || 0; } catch { return 0; }
};

export const InvestmentToolsPage = () => {
  const [tabIndex, setTabIndex] = useState(getInitialTab);
  const handleTabChange = (idx: number) => {
    setTabIndex(idx);
    try { localStorage.setItem(TAB_KEY, String(idx)); } catch {}
  };

  return (
    <Box pt={4}>
      <Box px={6} mb={2}>
        <Heading size="lg">Calculators</Heading>
        <Text color="text.secondary" mt={1} fontSize="sm">
          FIRE progress, loan analysis, HSA strategy, employer match optimization,
          what-if scenarios, bond ladder builder, equity compensation modeling,
          tax-equivalent yield, asset location, and cost basis aging.
        </Text>
      </Box>
      <Tabs colorScheme="brand" variant="enclosed" px={6} index={tabIndex} onChange={handleTabChange}>
        <TabList>
          {/* ── Approachable first ── */}
          <Tab fontSize="sm">FIRE</Tab>
          <Tab fontSize="sm">Loan Modeler</Tab>
          <Tab fontSize="sm">HSA Optimizer</Tab>
          <Tab fontSize="sm">Employer Match</Tab>
          <Tab fontSize="sm">What-If</Tab>
          {/* ── Advanced ── */}
          <Tab fontSize="sm">Bond Ladder</Tab>
          <Tab fontSize="sm">Equity Compensation</Tab>
          <Tab fontSize="sm">Tax-Equiv Yield</Tab>
          <Tab fontSize="sm">Asset Location</Tab>
          <Tab fontSize="sm">Cost Basis</Tab>
        </TabList>
        <TabPanels>
          <TabPanel px={0}>
            <Suspense fallback={<TabLoader />}>
              <FireMetricsPage />
            </Suspense>
          </TabPanel>
          <TabPanel px={0}>
            <Suspense fallback={<TabLoader />}>
              <LoanModelerPage />
            </Suspense>
          </TabPanel>
          <TabPanel px={0}>
            <Suspense fallback={<TabLoader />}>
              <HsaPage />
            </Suspense>
          </TabPanel>
          <TabPanel px={0}>
            <Suspense fallback={<TabLoader />}>
              <EmployerMatchTab />
            </Suspense>
          </TabPanel>
          <TabPanel px={0}>
            <Suspense fallback={<TabLoader />}>
              <WhatIfPage />
            </Suspense>
          </TabPanel>
          <TabPanel px={0}>
            <Suspense fallback={<TabLoader />}>
              <BondLadderPage />
            </Suspense>
          </TabPanel>
          <TabPanel px={0}>
            <Suspense fallback={<TabLoader />}>
              <EquityPage />
            </Suspense>
          </TabPanel>
          <TabPanel px={0}>
            <Suspense fallback={<TabLoader />}>
              <TaxEquivYieldTab />
            </Suspense>
          </TabPanel>
          <TabPanel px={0}>
            <Suspense fallback={<TabLoader />}>
              <AssetLocationTab />
            </Suspense>
          </TabPanel>
          <TabPanel px={0}>
            <Suspense fallback={<TabLoader />}>
              <CostBasisAgingTab />
            </Suspense>
          </TabPanel>
        </TabPanels>
      </Tabs>
    </Box>
  );
};

export default InvestmentToolsPage;
