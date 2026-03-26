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
import { lazy, Suspense } from "react";

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

export const LifePlanningPage = () => {
  return (
    <Box pt={4}>
      <Box px={6} mb={2}>
        <Heading size="lg">Life Planning</Heading>
        <Text color="text.secondary" mt={1} fontSize="sm">
          Social Security strategy, variable income smoothing, estate planning,
          RMD projections, insurance coverage audit, and pension modeling.
        </Text>
      </Box>
      <Tabs colorScheme="brand" variant="enclosed" px={6}>
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
