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
  Tooltip,
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
          Model what-if scenarios, check if you're on track to retire early, optimize your HSA and employer match, and run advanced analysis on loans, bonds, equity compensation, and taxes — all based on your actual account data.
        </Text>
      </Box>
      <Tabs colorScheme="brand" variant="enclosed" px={6} index={tabIndex} onChange={handleTabChange}>
        <TabList>
          {/* ── Approachable first ── */}
          <Tooltip label="Financial Independence / Retire Early — see how close you are to your FIRE number and projected retirement date based on your savings rate and portfolio." placement="bottom" hasArrow>
            <Tab fontSize="sm">FIRE</Tab>
          </Tooltip>
          <Tooltip label="Compare loans side-by-side: fixed vs variable rate, different terms, extra payments, and total interest paid." placement="bottom" hasArrow>
            <Tab fontSize="sm">Loan Modeler</Tab>
          </Tooltip>
          <Tooltip label="Model HSA triple-tax-advantage: invest vs spend, project growth to retirement, and see your cumulative tax savings." placement="bottom" hasArrow>
            <Tab fontSize="sm">HSA Optimizer</Tab>
          </Tooltip>
          <Tooltip label="See if you are capturing your full employer 401k match and how much you may be leaving on the table." placement="bottom" hasArrow>
            <Tab fontSize="sm">Employer Match</Tab>
          </Tooltip>
          <Tooltip label="Run hypothetical scenarios — what if you increased savings, paid off debt early, or changed your allocation?" placement="bottom" hasArrow>
            <Tab fontSize="sm">What-If</Tab>
          </Tooltip>
          {/* ── Advanced ── */}
          <Tooltip label="Build a bond ladder — staggered maturities to generate predictable income while reducing reinvestment risk." placement="bottom" hasArrow>
            <Tab fontSize="sm">Bond Ladder</Tab>
          </Tooltip>
          <Tooltip label="Model stock options and RSUs — vesting schedules, exercise strategies, and tax impact under different scenarios." placement="bottom" hasArrow>
            <Tab fontSize="sm">Equity Compensation</Tab>
          </Tooltip>
          <Tooltip label="Calculate the taxable yield a muni bond needs to match after accounting for your federal and state tax rate." placement="bottom" hasArrow>
            <Tab fontSize="sm">Tax-Equiv Yield</Tab>
          </Tooltip>
          <Tooltip label="Optimize which accounts hold which asset classes to minimize your overall tax drag." placement="bottom" hasArrow>
            <Tab fontSize="sm">Asset Location</Tab>
          </Tooltip>
          <Tooltip label="Review unrealized gains and losses by lot age — identify tax-loss harvesting candidates and avoid wash sales." placement="bottom" hasArrow>
            <Tab fontSize="sm">Cost Basis</Tab>
          </Tooltip>
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
