/**
 * Tax loss harvesting opportunities widget.
 */

import { memo } from "react";
import {
  Badge,
  Box,
  Card,
  CardBody,
  Divider,
  Heading,
  HStack,
  Link,
  SimpleGrid,
  Spinner,
  Stat,
  StatLabel,
  StatNumber,
  Text,
  VStack,
} from "@chakra-ui/react";
import { useQuery } from "@tanstack/react-query";
import { Link as RouterLink } from "react-router-dom";
import { useUserView } from "../../../contexts/UserViewContext";
import api from "../../../services/api";

interface TaxLossOpportunity {
  holding_id: string;
  ticker: string;
  name: string | null;
  unrealized_loss: number;
  loss_percentage: number;
  estimated_tax_savings: number;
  wash_sale_risk: boolean;
  is_crypto?: boolean;
  no_wash_sale_rule?: boolean;
}

interface TaxLossHarvestingData {
  opportunities: TaxLossOpportunity[];
  total_harvestable_losses: number;
  total_estimated_tax_savings: number;
}

const fmt = (n: number): string =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(n);

const TaxLossHarvestingWidgetBase: React.FC = () => {
  const { selectedUserId, effectiveUserId } = useUserView();

  const { data, isLoading, isError } = useQuery<TaxLossHarvestingData>({
    queryKey: ["tlh-widget", effectiveUserId],
    queryFn: async () => {
      const params = selectedUserId ? { user_id: effectiveUserId } : {};
      const res = await api.get("/reports/tax-loss-harvesting", { params });
      return res.data;
    },
    retry: false,
    staleTime: 10 * 60 * 1000,
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

  if (isError || !data || data.opportunities.length === 0) {
    return (
      <Card h="100%">
        <CardBody>
          <Heading size="md" mb={4}>
            Tax Loss Harvesting
          </Heading>
          <Text color="text.muted" fontSize="sm">
            No tax loss harvesting opportunities found right now.
          </Text>
        </CardBody>
      </Card>
    );
  }

  return (
    <Card h="100%">
      <CardBody>
        <HStack justify="space-between" mb={4}>
          <HStack spacing={2}>
            <Heading size="md">Tax Loss Harvesting</Heading>
            <Badge colorScheme="green" fontSize="xs">
              {data.opportunities.length} opportunit
              {data.opportunities.length === 1 ? "y" : "ies"}
            </Badge>
          </HStack>
          <Link
            as={RouterLink}
            to="/investments"
            fontSize="sm"
            color="brand.500"
          >
            View details →
          </Link>
        </HStack>

        <SimpleGrid columns={2} spacing={3} mb={4}>
          <Stat size="sm">
            <StatLabel>Harvestable Losses</StatLabel>
            <StatNumber fontSize="lg" color="finance.negative">
              {fmt(Number(data.total_harvestable_losses))}
            </StatNumber>
          </Stat>
          <Stat size="sm">
            <StatLabel>Est. Tax Savings</StatLabel>
            <StatNumber fontSize="lg" color="green.500">
              {fmt(Number(data.total_estimated_tax_savings))}
            </StatNumber>
          </Stat>
        </SimpleGrid>

        <VStack align="stretch" spacing={1}>
          <Text fontSize="xs" fontWeight="semibold" color="text.secondary">
            Top Opportunities
          </Text>
          {data.opportunities.slice(0, 4).map((opp, idx) => (
            <Box key={opp.holding_id}>
              <HStack justify="space-between" py={1}>
                <HStack spacing={2}>
                  <Text fontSize="sm" fontWeight="medium">
                    {opp.ticker}
                  </Text>
                  {opp.wash_sale_risk && (
                    <Badge colorScheme="yellow" fontSize="2xs">
                      Wash sale risk
                    </Badge>
                  )}
                  {opp.no_wash_sale_rule && (
                    <Badge colorScheme="orange" fontSize="xs">No Wash-Sale Rule (Crypto)</Badge>
                  )}
                </HStack>
                <HStack spacing={2}>
                  <Text fontSize="sm" color="finance.negative">
                    {fmt(Number(opp.unrealized_loss))}
                  </Text>
                  <Badge colorScheme="red" variant="subtle" fontSize="2xs">
                    {Number(opp.loss_percentage).toFixed(1)}%
                  </Badge>
                </HStack>
              </HStack>
              {idx < data.opportunities.slice(0, 4).length - 1 && <Divider />}
            </Box>
          ))}
        </VStack>
      </CardBody>
    </Card>
  );
};

export const TaxLossHarvestingWidget = memo(TaxLossHarvestingWidgetBase);
