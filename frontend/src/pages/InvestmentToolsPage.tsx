/**
 * Investment Tools — consolidated advanced investment hub.
 *
 * Combines FIRE metrics, Equity Compensation, and Loan Modeler
 * into a single tabbed view.
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
          FIRE progress, equity compensation modeling, and loan analysis.
        </Text>
      </Box>
      <Tabs colorScheme="brand" variant="enclosed" px={6}>
        <TabList>
          <Tab fontSize="sm">FIRE</Tab>
          <Tab fontSize="sm">Equity Compensation</Tab>
          <Tab fontSize="sm">Loan Modeler</Tab>
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
        </TabPanels>
      </Tabs>
    </Box>
  );
};

export default InvestmentToolsPage;
