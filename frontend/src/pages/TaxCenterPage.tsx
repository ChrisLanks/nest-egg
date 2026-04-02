/**
 * Tax Center — consolidated tax planning hub.
 *
 * Combines Tax Projection, Tax Buckets (three-bucket strategy), Charitable Giving,
 * Medicare & IRMAA planning, Backdoor Roth wizard, and Contribution Headroom
 * into a single tabbed view to reduce nav clutter.
 *
 * Tab labels include plain-English tooltips for beginners unfamiliar with tax jargon.
 * Advanced tabs (Charitable Giving) are hidden in simple mode (showAdvancedNav = false).
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
const RothConversionPage = lazy(() => import("./RothConversionPage"));

const TabLoader = () => (
  <Center py={12}>
    <Spinner size="lg" color="brand.500" />
  </Center>
);

const TAB_KEY = "nest-egg-tab-tax-center";
const getInitialTab = () => {
  try { return parseInt(localStorage.getItem(TAB_KEY) ?? "0", 10) || 0; } catch { return 0; }
};

const getShowAdvancedNav = () => {
  try { return localStorage.getItem("nest-egg-show-advanced-nav") === "true"; } catch { return false; }
};

/** Tabs with jargon tooltips. Each label wraps with a Tooltip so beginners can hover to learn. */
const TAB_TOOLTIPS: Record<string, string> = {
  "Tax Projection": "Estimate your total federal + state tax bill for the year based on your income — so you're not surprised in April.",
  "Tax Buckets": "Your money split into three buckets: taxable (brokerage), tax-deferred (401k/IRA), and tax-free (Roth). Pulling from the right bucket in retirement can save you thousands.",
  "Charitable Giving": "Track donations to charities, churches, and nonprofits — and see how they reduce your taxable income.",
  "Medicare & IRMAA": "If your income is above ~$103K/yr, Medicare charges you more for Part B and Part D premiums. IRMAA = Income-Related Monthly Adjustment Amount. Planning ahead can lower these costs.",
  "Roth Wizard": "A Roth IRA grows tax-free, but high earners can't contribute directly. This wizard shows you the 'backdoor' workaround and whether it applies to you.",
  "Roth Conversion": "Model the optimal amount to convert from a traditional IRA or 401(k) to Roth each year — filling bracket headroom while minimizing IRMAA surcharges.",
  "Contribution Headroom": "How much more you can still contribute to your 401(k), IRA, and HSA this year before hitting IRS limits — maxing these out lowers your taxable income.",
};

const TooltipTab = ({ label }: { label: string }) => (
  <Tab fontSize="sm">
    <Tooltip label={TAB_TOOLTIPS[label]} hasArrow placement="top" openDelay={300}>
      <span>{label}</span>
    </Tooltip>
  </Tab>
);

export const TaxCenterPage = () => {
  const [tabIndex, setTabIndex] = useState(getInitialTab);
  const showAdvancedNav = getShowAdvancedNav();

  // In simple mode, Charitable Giving is hidden — adjust stored index if needed
  const effectiveTabIndex = !showAdvancedNav && tabIndex === 2
    ? 0
    : !showAdvancedNav && tabIndex > 2
    ? tabIndex - 1
    : tabIndex;

  const handleTabChange = (idx: number) => {
    // Map visible index back to full index for storage
    const storageIdx = !showAdvancedNav && idx >= 2 ? idx + 1 : idx;
    setTabIndex(storageIdx);
    try { localStorage.setItem(TAB_KEY, String(storageIdx)); } catch {}
  };

  return (
    <Box pt={4}>
      <Box px={6} mb={2}>
        <Heading size="lg">Tax Center</Heading>
        <Text color="text.secondary" mt={1} fontSize="sm">
          Tax projection, bucket optimization, Medicare planning, Roth strategies, conversion optimizer, and contribution headroom.
          {!showAdvancedNav && (
            <Text as="span" color="text.muted"> Charitable Giving is available in Advanced mode (Preferences).</Text>
          )}
        </Text>
      </Box>
      <Tabs colorScheme="brand" variant="enclosed" px={6} index={effectiveTabIndex} onChange={handleTabChange}>
        <TabList>
          <TooltipTab label="Tax Projection" />
          <TooltipTab label="Tax Buckets" />
          {showAdvancedNav && <TooltipTab label="Charitable Giving" />}
          <TooltipTab label="Medicare & IRMAA" />
          <TooltipTab label="Roth Wizard" />
          <TooltipTab label="Roth Conversion" />
          <TooltipTab label="Contribution Headroom" />
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
          {showAdvancedNav && (
            <TabPanel px={0}>
              <Suspense fallback={<TabLoader />}>
                <CharitableGivingPage />
              </Suspense>
            </TabPanel>
          )}
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
              <RothConversionPage />
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
