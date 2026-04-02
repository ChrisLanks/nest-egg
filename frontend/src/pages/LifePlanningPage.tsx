/**
 * Estate & Insurance — estate planning and insurance audit hub.
 *
 * Tabs:
 *   - Estate & Beneficiaries: wills, trusts, beneficiary designations
 *   - Insurance Audit: coverage gap analysis and recommendations
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

const EstatePage = lazy(() => import("./EstatePage"));
const InsuranceAuditTab = lazy(() =>
  import("./InsuranceAuditTab").then((m) => ({ default: m.InsuranceAuditTab })),
);

const TabLoader = () => (
  <Center py={12}>
    <Spinner size="lg" color="brand.500" />
  </Center>
);

const TAB_KEY = "nest-egg-tab-life-planning";
const getInitialTab = () => {
  try {
    return parseInt(localStorage.getItem(TAB_KEY) ?? "0", 10) || 0;
  } catch {
    return 0;
  }
};

export const LifePlanningPage = () => {
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
        <Heading size="lg">Estate & Insurance</Heading>
        <Text color="text.secondary" mt={1} fontSize="sm">
          Plan your estate, manage beneficiary designations, and audit your insurance coverage for gaps.
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
          <Tab fontSize="sm">Estate &amp; Beneficiaries</Tab>
          <Tab fontSize="sm">Insurance Audit</Tab>
        </TabList>
        <TabPanels>
          <TabPanel px={0}>
            <Suspense fallback={<TabLoader />}>
              <EstatePage />
            </Suspense>
          </TabPanel>
          <TabPanel px={0}>
            <Suspense fallback={<TabLoader />}>
              <InsuranceAuditTab />
            </Suspense>
          </TabPanel>
        </TabPanels>
      </Tabs>
    </Box>
  );
};

export default LifePlanningPage;
