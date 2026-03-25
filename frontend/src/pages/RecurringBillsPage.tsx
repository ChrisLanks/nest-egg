/**
 * Recurring & Bills — consolidated scheduled payments hub.
 *
 * Combines Recurring Transactions and Bills into a single tabbed view.
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

const RecurringTransactionsPage = lazy(
  () => import("./RecurringTransactionsPage"),
);
const BillsPage = lazy(() => import("./BillsPage"));

const TabLoader = () => (
  <Center py={12}>
    <Spinner size="lg" color="brand.500" />
  </Center>
);

export const RecurringBillsPage = () => {
  return (
    <Box pt={4}>
      <Box px={6} mb={2}>
        <Heading size="lg">Recurring &amp; Bills</Heading>
        <Text color="text.secondary" mt={1} fontSize="sm">
          Subscriptions, recurring payments, and upcoming bill due dates.
        </Text>
      </Box>
      <Tabs colorScheme="brand" variant="enclosed" px={6}>
        <TabList>
          <Tab fontSize="sm">Recurring</Tab>
          <Tab fontSize="sm">Bills</Tab>
        </TabList>
        <TabPanels>
          <TabPanel px={0}>
            <Suspense fallback={<TabLoader />}>
              <RecurringTransactionsPage />
            </Suspense>
          </TabPanel>
          <TabPanel px={0}>
            <Suspense fallback={<TabLoader />}>
              <BillsPage />
            </Suspense>
          </TabPanel>
        </TabPanels>
      </Tabs>
    </Box>
  );
};

export default RecurringBillsPage;
