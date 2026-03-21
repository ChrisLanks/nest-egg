/**
 * Year-over-year income/expense comparison widget.
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

interface YoYMonth {
  month: number;
  month_name: string;
  data: Record<string, { income: number; expenses: number; net: number }>;
}

const fmt = (n: number): string =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(n);

const COLORS: Record<string, string[]> = {
  expenses: ["#F56565", "#FC8181", "#FEB2B2"],
  income: ["#48BB78", "#68D391", "#9AE6B4"],
};

const YearOverYearWidgetBase: React.FC = () => {
  const { selectedUserId } = useUserView();
  const tooltipBg = useColorModeValue("#FFFFFF", "#2D3748");
  const tooltipBorder = useColorModeValue("#E2E8F0", "#4A5568");

  const currentYear = new Date().getFullYear();
  const years = [currentYear, currentYear - 1];

  const { data, isLoading, isError } = useQuery<YoYMonth[]>({
    queryKey: ["yoy-widget", selectedUserId, years],
    queryFn: async () => {
      const params = new URLSearchParams();
      years.forEach((y) => params.append("years", String(y)));
      if (selectedUserId) params.set("user_id", selectedUserId);
      const res = await api.get("/income-expenses/year-over-year", { params });
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
            Year over Year
          </Heading>
          <Text color="text.muted" fontSize="sm">
            Not enough data for year-over-year comparison yet.
          </Text>
        </CardBody>
      </Card>
    );
  }

  const chartData = data.map((m) => {
    const row: Record<string, string | number> = {
      month: m.month_name.slice(0, 3),
    };
    years.forEach((y) => {
      const d = m.data[String(y)];
      if (d) {
        row[`expenses_${y}`] = Math.abs(d.expenses);
      }
    });
    return row;
  });

  return (
    <Card h="100%">
      <CardBody>
        <HStack justify="space-between" mb={4}>
          <Heading size="md">Year over Year</Heading>
          <Link
            as={RouterLink}
            to="/income-expenses"
            fontSize="sm"
            color="brand.500"
          >
            View details →
          </Link>
        </HStack>

        <ResponsiveContainer width="100%" height={280}>
          <BarChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="month" fontSize={12} />
            <YAxis fontSize={12} />
            <Tooltip
              formatter={((v: number) => fmt(v)) as any}
              contentStyle={{
                backgroundColor: tooltipBg,
                border: `1px solid ${tooltipBorder}`,
              }}
            />
            <Legend />
            {years.map((y, i) => (
              <Bar
                key={y}
                dataKey={`expenses_${y}`}
                fill={COLORS.expenses[i]}
                name={`${y} Spending`}
              />
            ))}
          </BarChart>
        </ResponsiveContainer>
      </CardBody>
    </Card>
  );
};

export const YearOverYearWidget = memo(YearOverYearWidgetBase);
