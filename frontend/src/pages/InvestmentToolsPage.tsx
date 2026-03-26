/**
 * Investment Tools — consolidated advanced investment hub.
 *
 * Combines FIRE metrics, Equity Compensation, Loan Modeler, HSA Optimizer,
 * Tax-Equivalent Yield, Asset Location, Employer Match, Dividend Calendar,
 * and Cost Basis Aging into a single tabbed view.
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
const DividendCalendarTab = lazy(() =>
  import("./DividendCalendarTab").then((m) => ({ default: m.DividendCalendarTab })),
);
const CostBasisAgingTab = lazy(() =>
  import("./CostBasisAgingTab").then((m) => ({ default: m.CostBasisAgingTab })),
);

const TabLoader = () => (
  <Center py={12}>
    <Spinner size="lg" color="brand.500" />
  </Center>
);

export const InvestmentToolsPage = () => {
  return (
    <Box pt={4}>
      <Box px={6} mb={2}>
        <Heading size="lg">Investment Tools</Heading>
        <Text color="text.secondary" mt={1} fontSize="sm">
          FIRE progress, equity compensation modeling, loan analysis, HSA
          strategy, tax-equivalent yield, asset location, employer match
          optimization, dividend calendar, and cost basis aging.
        </Text>
      </Box>
      <Tabs colorScheme="brand" variant="enclosed" px={6}>
        <TabList>
          <Tab fontSize="sm">FIRE</Tab>
          <Tab fontSize="sm">Equity Compensation</Tab>
          <Tab fontSize="sm">Loan Modeler</Tab>
          <Tab fontSize="sm">HSA Optimizer</Tab>
          <Tab fontSize="sm">Tax-Equiv Yield</Tab>
          <Tab fontSize="sm">Asset Location</Tab>
          <Tab fontSize="sm">Employer Match</Tab>
          <Tab fontSize="sm">Dividend Calendar</Tab>
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
              <EquityPage />
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
              <EmployerMatchTab />
            </Suspense>
          </TabPanel>
          <TabPanel px={0}>
            <Suspense fallback={<TabLoader />}>
              <DividendCalendarTab />
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
