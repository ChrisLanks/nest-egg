/**
 * Life Planning — consolidated life events hub.
 *
 * Combines Social Security Optimizer, Variable Income Planner,
 * Estate & Beneficiary Planning, RMD Planner, Insurance Audit,
 * and Pension Modeler into a single tabbed view.
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

const SSClaimingPage = lazy(() => import("./SSClaimingPage"));
const VariableIncomePage = lazy(() => import("./VariableIncomePage"));
const EstatePage = lazy(() => import("./EstatePage"));
const RmdPlannerTab = lazy(() =>
  import("./RmdPlannerTab").then((m) => ({ default: m.RmdPlannerTab })),
);
const InsuranceAuditTab = lazy(() =>
  import("./InsuranceAuditTab").then((m) => ({ default: m.InsuranceAuditTab })),
);
const PensionModelerTab = lazy(() =>
  import("./PensionModelerTab").then((m) => ({ default: m.PensionModelerTab })),
);

const TabLoader = () => (
  <Center py={12}>
    <Spinner size="lg" color="brand.500" />
  </Center>
);

const TAB_KEY = "nest-egg-tab-life-planning";
const getInitialTab = () => {
  try { return parseInt(localStorage.getItem(TAB_KEY) ?? "0", 10) || 0; } catch { return 0; }
};

export const LifePlanningPage = () => {
  const [tabIndex, setTabIndex] = useState(getInitialTab);
  const handleTabChange = (idx: number) => {
    setTabIndex(idx);
    try { localStorage.setItem(TAB_KEY, String(idx)); } catch {}
  };

  return (
    <Box pt={4}>
      <Box px={6} mb={2}>
        <Heading size="lg">Life Planning</Heading>
        <Text color="text.secondary" mt={1} fontSize="sm">
          Social Security strategy, RMD projections, pension modeling, estate & beneficiary planning, and insurance audit.
        </Text>
      </Box>
      <Tabs colorScheme="brand" variant="enclosed" px={6} index={tabIndex} onChange={handleTabChange}>
        <TabList>
          <Tab fontSize="sm">SS Optimizer</Tab>
          <Tab fontSize="sm">Variable Income</Tab>
          <Tab fontSize="sm">Estate &amp; Beneficiaries</Tab>
          <Tab fontSize="sm">RMD Planner</Tab>
          <Tab fontSize="sm">Insurance Audit</Tab>
          <Tab fontSize="sm">Pension Modeler</Tab>
        </TabList>
        <TabPanels>
          <TabPanel px={0}>
            <Suspense fallback={<TabLoader />}>
              <SSClaimingPage />
            </Suspense>
          </TabPanel>
          <TabPanel px={0}>
            <Suspense fallback={<TabLoader />}>
              <VariableIncomePage />
            </Suspense>
          </TabPanel>
          <TabPanel px={0}>
            <Suspense fallback={<TabLoader />}>
              <EstatePage />
            </Suspense>
          </TabPanel>
          <TabPanel px={0}>
            <Suspense fallback={<TabLoader />}>
              <RmdPlannerTab />
            </Suspense>
          </TabPanel>
          <TabPanel px={0}>
            <Suspense fallback={<TabLoader />}>
              <InsuranceAuditTab />
            </Suspense>
          </TabPanel>
          <TabPanel px={0}>
            <Suspense fallback={<TabLoader />}>
              <PensionModelerTab />
            </Suspense>
          </TabPanel>
        </TabPanels>
      </Tabs>
    </Box>
  );
};

export default LifePlanningPage;
