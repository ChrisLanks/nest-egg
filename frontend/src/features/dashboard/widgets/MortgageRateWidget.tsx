/**
 * Mortgage Rate Watch Widget — current market rates vs. user's rate.
 *
 * Fetches 30-yr and 15-yr rates from FRED (via our backend proxy) and
 * compares against the user's linked mortgage account interest rate.
 */

import {
  Alert,
  AlertIcon,
  Card,
  CardBody,
  Heading,
  HStack,
  Link,
  SimpleGrid,
  Spinner,
  Stat,
  StatLabel,
  StatNumber,
  Text,
} from "@chakra-ui/react";
import { useQuery } from "@tanstack/react-query";
import { memo } from "react";
import { Link as RouterLink } from "react-router-dom";
import { useUserView } from "../../../contexts/UserViewContext";
import api from "../../../services/api";

interface MortgageRateData {
  rate_30yr: number | null;
  rate_15yr: number | null;
  as_of_date: string | null;
  source: string;
  your_rate: number | null;
  rate_comparison: "above_market" | "below_market" | "at_market" | null;
}

const fmtPct = (r: number) => `${(r * 100).toFixed(2)}%`;

function comparisonBadge(
  cmp: MortgageRateData["rate_comparison"],
): { label: string; scheme: string } | null {
  if (cmp === "above_market")
    return { label: "Above market — consider refinancing", scheme: "red" };
  if (cmp === "below_market")
    return { label: "Below market — you have a great rate", scheme: "green" };
  if (cmp === "at_market") return { label: "At market rate", scheme: "gray" };
  return null;
}

const MortgageRateWidgetBase: React.FC = () => {
  const { selectedUserId, effectiveUserId } = useUserView();

  const { data, isLoading } = useQuery<MortgageRateData>({
    queryKey: ["mortgage-rate-widget", effectiveUserId],
    queryFn: async () => {
      const params = selectedUserId ? { user_id: effectiveUserId } : {};
      const res = await api.get("/financial-planning/mortgage-rates", {
        params,
      });
      return res.data;
    },
    staleTime: 60 * 60 * 1000, // rates are weekly — cache 1 hour
    retry: false,
  });

  if (isLoading) {
    return (
      <Card h="100%">
        <CardBody display="flex" alignItems="center" justifyContent="center">
          <Spinner />
        </CardBody>
      </Card>
    );
  }

  if (!data || (!data.rate_30yr && !data.rate_15yr)) {
    return (
      <Card h="100%">
        <CardBody>
          <Heading size="md" mb={3}>
            Mortgage Rates
          </Heading>
          <Text fontSize="sm" color="text.muted">
            Market rates temporarily unavailable.
          </Text>
        </CardBody>
      </Card>
    );
  }

  const badge = comparisonBadge(data.rate_comparison);

  return (
    <Card h="100%">
      <CardBody>
        <HStack justify="space-between" mb={4}>
          <Heading size="md">Mortgage Rates</Heading>
          <Link as={RouterLink} to="/mortgage" fontSize="sm" color="brand.500">
            Analyze →
          </Link>
        </HStack>

        <SimpleGrid columns={data.your_rate ? 3 : 2} spacing={3} mb={3}>
          {data.rate_30yr != null && (
            <Stat size="sm">
              <StatLabel>30-yr Fixed</StatLabel>
              <StatNumber fontSize="lg">{fmtPct(data.rate_30yr)}</StatNumber>
            </Stat>
          )}
          {data.rate_15yr != null && (
            <Stat size="sm">
              <StatLabel>15-yr Fixed</StatLabel>
              <StatNumber fontSize="lg">{fmtPct(data.rate_15yr)}</StatNumber>
            </Stat>
          )}
          {data.your_rate != null && (
            <Stat size="sm">
              <StatLabel>Your Rate</StatLabel>
              <StatNumber fontSize="lg">{fmtPct(data.your_rate)}</StatNumber>
            </Stat>
          )}
        </SimpleGrid>

        {badge && (
          <Alert
            status={
              badge.scheme === "red"
                ? "warning"
                : badge.scheme === "green"
                  ? "success"
                  : "info"
            }
            borderRadius="md"
            py={2}
            fontSize="xs"
          >
            <AlertIcon boxSize={3} />
            {badge.label}
          </Alert>
        )}

        {data.as_of_date && (
          <Text fontSize="2xs" color="text.muted" mt={2}>
            {data.source} · as of {data.as_of_date}
          </Text>
        )}
      </CardBody>
    </Card>
  );
};

export const MortgageRateWidget = memo(MortgageRateWidgetBase);
