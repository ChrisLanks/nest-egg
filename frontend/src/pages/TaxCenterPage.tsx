/**
 * Tax Center — consolidated tax planning hub.
 *
 * Combines Tax Projection, Tax Buckets (three-bucket strategy), and
 * Charitable Giving into a single tabbed view to reduce nav clutter.
 */

import {
  Box,
  Heading,
  Tab,
  TabList,
  TabPanel,
  TabPanels,
  Tabs,
  Text,
} from "@chakra-ui/react";
import { lazy, Suspense } from "react";
import { Center, Spinner } from "@chakra-ui/react";

// Import existing pages as tab content — each manages its own state/data fetching
const TaxProjectionPage = lazy(() => import("./TaxProjectionPage"));
const TaxBucketsPage = lazy(() => import("./TaxBucketsPage"));
const CharitableGivingPage = lazy(() => import("./CharitableGivingPage"));

const TabLoader = () => (
  <Center py={12}>
    <Spinner size="lg" color="brand.500" />
  </Center>
);

export const TaxCenterPage = () => {
  return (
    <Box pt={4}>
      <Box px={6} mb={2}>
        <Heading size="lg">Tax Center</Heading>
        <Text color="text.secondary" mt={1} fontSize="sm">
          Tax projection, bucket optimization, and charitable giving strategy.
        </Text>
      </Box>
      <Tabs colorScheme="brand" variant="enclosed" px={6}>
        <TabList>
          <Tab fontSize="sm">Tax Projection</Tab>
          <Tab fontSize="sm">Tax Buckets</Tab>
          <Tab fontSize="sm">Charitable Giving</Tab>
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
        </TabPanels>
      </Tabs>
    </Box>
  );
};

export default TaxCenterPage;
