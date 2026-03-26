/**
 * Tax Center — consolidated tax planning hub.
 *
 * Combines Tax Projection, Tax Buckets (three-bucket strategy), Charitable Giving,
 * Medicare & IRMAA planning, Backdoor Roth wizard, and Contribution Headroom
 * into a single tabbed view to reduce nav clutter.
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

// Import existing pages as tab content — each manages its own state/data fetching
const TaxProjectionPage = lazy(() => import("./TaxProjectionPage"));
const TaxBucketsPage = lazy(() => import("./TaxBucketsPage"));
const CharitableGivingPage = lazy(() => import("./CharitableGivingPage"));
const IrmaaMedicareTab = lazy(() =>
  import("./IrmaaMedicareTab").then((m) => ({ default: m.IrmaaMedicareTab })),
);
const BackdoorRothTab = lazy(() =>
  import("./BackdoorRothTab").then((m) => ({ default: m.BackdoorRothTab })),
);
const ContributionHeadroomTab = lazy(() =>
  import("./ContributionHeadroomTab").then((m) => ({
    default: m.ContributionHeadroomTab,
  })),
);

const TabLoader = () => (
  <Center py={12}>
    <Spinner size="lg" color="brand.500" />
  </Center>
);

const TAB_KEY = "nest-egg-tab-tax-center";
const getInitialTab = () => {
  try { return parseInt(localStorage.getItem(TAB_KEY) ?? "0", 10) || 0; } catch { return 0; }
};

export const TaxCenterPage = () => {
  const [tabIndex, setTabIndex] = useState(getInitialTab);
  const handleTabChange = (idx: number) => {
    setTabIndex(idx);
    try { localStorage.setItem(TAB_KEY, String(idx)); } catch {}
  };

  return (
    <Box pt={4}>
      <Box px={6} mb={2}>
        <Heading size="lg">Tax Center</Heading>
        <Text color="text.secondary" mt={1} fontSize="sm">
          Tax projection, bucket optimization, charitable giving, Medicare
          planning, Roth strategies, and contribution headroom.
        </Text>
      </Box>
      <Tabs colorScheme="brand" variant="enclosed" px={6} index={tabIndex} onChange={handleTabChange}>
        <TabList>
          <Tab fontSize="sm">Tax Projection</Tab>
          <Tab fontSize="sm">Tax Buckets</Tab>
          <Tab fontSize="sm">Charitable Giving</Tab>
          <Tab fontSize="sm">Medicare &amp; IRMAA</Tab>
          <Tab fontSize="sm">Roth Wizard</Tab>
          <Tab fontSize="sm">Contribution Headroom</Tab>
        </TabList>
        <TabPanels>
          <TabPanel px={0}>
            <Suspense fallback={<TabLoader />}>
              <TaxProjectionPage />
            </Suspense>
          </TabPanel>
          <TabPanel px={0}>
            <Suspense fallback={<TabLoader />}>
              <TaxBucketsPage />
            </Suspense>
          </TabPanel>
          <TabPanel px={0}>
            <Suspense fallback={<TabLoader />}>
              <CharitableGivingPage />
            </Suspense>
          </TabPanel>
          <TabPanel px={0}>
            <Suspense fallback={<TabLoader />}>
              <IrmaaMedicareTab />
            </Suspense>
          </TabPanel>
          <TabPanel px={0}>
            <Suspense fallback={<TabLoader />}>
              <BackdoorRothTab />
            </Suspense>
          </TabPanel>
          <TabPanel px={0}>
            <Suspense fallback={<TabLoader />}>
              <ContributionHeadroomTab />
            </Suspense>
          </TabPanel>
        </TabPanels>
      </Tabs>
    </Box>
  );
};

export default TaxCenterPage;
