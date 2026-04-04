/**
 * Quarterly income/expense performance widget.
 */

import { memo } from "react";
import {
  Card,
  CardBody,
  Heading,
  HStack,
  Link,
  Spinner,
  Text,
  useColorModeValue,
} from "@chakra-ui/react";
import { useQuery } from "@tanstack/react-query";
import { Link as RouterLink } from "react-router-dom";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { useUserView } from "../../../contexts/UserViewContext";
import api from "../../../services/api";

interface QuarterData {
  quarter: number;
  quarter_name: string;
  data: Record<string, { income: number; expenses: number; net: number }>;
}

const fmt = (n: number): string =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(n);

const QuarterlyPerformanceWidgetBase: React.FC = () => {
  const { selectedUserId, effectiveUserId } = useUserView();
  const tooltipBg = useColorModeValue("#FFFFFF", "#2D3748");
  const tooltipBorder = useColorModeValue("#E2E8F0", "#4A5568");

  const currentYear = new Date().getFullYear();
  const years = [currentYear, currentYear - 1];

  const { data, isLoading, isError } = useQuery<QuarterData[]>({
    queryKey: ["quarterly-widget", effectiveUserId, years],
    queryFn: async () => {
      const params = new URLSearchParams();
      years.forEach((y) => params.append("years", String(y)));
      if (effectiveUserId) params.set("user_id", effectiveUserId);
      const res = await api.get("/income-expenses/quarterly-summary", {
        params,
      });
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

  if (isError || !data || data.length === 0) {
    return (
      <Card h="100%">
        <CardBody>
          <Heading size="md" mb={4}>
            Quarterly Performance
          </Heading>
          <Text color="text.muted" fontSize="sm">
            Not enough data for quarterly comparison yet.
          </Text>
        </CardBody>
      </Card>
    );
  }

  const chartData = data.map((q) => {
    const row: Record<string, string | number> = {
      quarter: q.quarter_name,
    };
    years.forEach((y) => {
      const d = q.data[String(y)];
      if (d) {
        row[`net_${y}`] = d.net;
      }
    });
    return row;
  });

  return (
    <Card h="100%">
      <CardBody>
        <HStack justify="space-between" mb={4}>
          <Heading size="md">Quarterly Performance</Heading>
          <Link
            as={RouterLink}
            to="/cash-flow"
            fontSize="sm"
            color="brand.500"
          >
            View details →
          </Link>
        </HStack>

        <ResponsiveContainer width="100%" height={250}>
          <BarChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="quarter" fontSize={12} />
            <YAxis fontSize={12} />
            <Tooltip
              formatter={((v: number) => fmt(v)) as any}
              contentStyle={{
                backgroundColor: tooltipBg,
                border: `1px solid ${tooltipBorder}`,
              }}
            />
            <Legend />
            <Bar
              dataKey={`net_${years[0]}`}
              fill="#4299E1"
              name={`${years[0]} Net`}
            />
            <Bar
              dataKey={`net_${years[1]}`}
              fill="#A0AEC0"
              name={`${years[1]} Net`}
            />
          </BarChart>
        </ResponsiveContainer>
      </CardBody>
    </Card>
  );
};

export const QuarterlyPerformanceWidget = memo(QuarterlyPerformanceWidgetBase);
