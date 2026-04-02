/**
 * Retirement Hub — unified retirement & income planning hub.
 *
 * Tabs:
 *   - Retirement Planner: scenario-based Monte Carlo retirement projections
 *   - SS Optimizer: Social Security claiming strategy optimizer
 *   - RMD Planner: Required Minimum Distribution projections
 *   - Pension Modeler: pension income modeling
 *   - Variable Income: variable/self-employment income planning
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

const RetirementPage = lazy(() =>
  import("../features/retirement/pages/RetirementPage").then((m) => ({
    default: m.RetirementPage,
  })),
);
const SSClaimingPage = lazy(() => import("./SSClaimingPage"));
const RmdPlannerTab = lazy(() =>
  import("./RmdPlannerTab").then((m) => ({ default: m.RmdPlannerTab })),
);
const PensionModelerTab = lazy(() =>
  import("./PensionModelerTab").then((m) => ({ default: m.PensionModelerTab })),
);
const VariableIncomePage = lazy(() => import("./VariableIncomePage"));

const TabLoader = () => (
  <Center py={12}>
    <Spinner size="lg" color="brand.500" />
  </Center>
);

const TAB_KEY = "nest-egg-tab-retirement-hub";
const getInitialTab = () => {
  try {
    return parseInt(localStorage.getItem(TAB_KEY) ?? "0", 10) || 0;
  } catch {
    return 0;
  }
};

export const RetirementHubPage = () => {
  const [tabIndex, setTabIndex] = useState(getInitialTab);
  const handleTabChange = (idx: number) => {
    setTabIndex(idx);
    try {
      localStorage.setItem(TAB_KEY, String(idx));
    } catch {}
  };

  return (
    <Box pt={4}>
      <Box px={6} mb={2}>
        <Heading size="lg">Retirement & Income</Heading>
        <Text color="text.secondary" mt={1} fontSize="sm">
          Project your retirement readiness, optimize Social Security timing, plan for RMDs, model pension income, and account for variable earnings.
        </Text>
      </Box>
      <Tabs
        colorScheme="brand"
        variant="enclosed"
        px={6}
        index={tabIndex}
        onChange={handleTabChange}
      >
        <TabList>
          <Tab fontSize="sm">Retirement Planner</Tab>
          <Tab fontSize="sm">SS Optimizer</Tab>
          <Tab fontSize="sm">RMD Planner</Tab>
          <Tab fontSize="sm">Pension</Tab>
          <Tab fontSize="sm">Variable Income</Tab>
        </TabList>
        <TabPanels>
          <TabPanel px={0}>
            <Suspense fallback={<TabLoader />}>
              <RetirementPage />
            </Suspense>
          </TabPanel>
          <TabPanel px={0}>
            <Suspense fallback={<TabLoader />}>
              <SSClaimingPage />
            </Suspense>
          </TabPanel>
          <TabPanel px={0}>
            <Suspense fallback={<TabLoader />}>
              <RmdPlannerTab />
            </Suspense>
          </TabPanel>
          <TabPanel px={0}>
            <Suspense fallback={<TabLoader />}>
              <PensionModelerTab />
            </Suspense>
          </TabPanel>
          <TabPanel px={0}>
            <Suspense fallback={<TabLoader />}>
              <VariableIncomePage />
            </Suspense>
          </TabPanel>
        </TabPanels>
      </Tabs>
    </Box>
  );
};

export default RetirementHubPage;
