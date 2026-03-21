/**
 * Money Flow Sankey diagram widget.
 *
 * Shows income sources flowing into the household and
 * expense categories flowing out, with link widths proportional to amounts.
 * Surplus (or deficit) shown as a distinct output node.
 */

import {
  Box,
  Card,
  CardBody,
  Heading,
  Text,
  HStack,
  Select,
  useColorModeValue,
} from "@chakra-ui/react";
import { memo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Sankey,
  Tooltip,
  Layer,
  Rectangle,
  ResponsiveContainer,
} from "recharts";
import { useUserView } from "../../../contexts/UserViewContext";
import api from "../../../services/api";

interface CategoryBreakdown {
  category: string;
  amount: number;
  count: number;
  percentage: number;
}

interface IncomeExpenseSummary {
  total_income: number;
  total_expenses: number;
  net: number;
  income_categories: CategoryBreakdown[];
  expense_categories: CategoryBreakdown[];
}

const formatCurrency = (amount: number) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount);

/** Build Sankey nodes and links from income/expense summary data. */
function buildSankeyData(summary: IncomeExpenseSummary) {
  const nodes: { name: string }[] = [];
  const links: { source: number; target: number; value: number }[] = [];

  // Filter to meaningful categories (> 0.5% of respective total)
  const incomeCategories = summary.income_categories
    .filter((c) => c.amount > 0 && c.percentage >= 0.5)
    .slice(0, 8);
  const expenseCategories = summary.expense_categories
    .filter((c) => c.amount > 0 && c.percentage >= 0.5)
    .slice(0, 10);

  if (incomeCategories.length === 0 && expenseCategories.length === 0) {
    return null;
  }

  // Nodes: income sources, then "Total Income" hub, then expense categories, then surplus/deficit
  // Index layout: [income_0..income_n, hub, expense_0..expense_m, surplus]

  // Income source nodes
  incomeCategories.forEach((c) => nodes.push({ name: c.category }));
  const hubIndex = nodes.length;
  nodes.push({ name: "Total Income" });

  // Expense category nodes
  const expenseStartIndex = nodes.length;
  expenseCategories.forEach((c) => nodes.push({ name: c.category }));

  // Surplus or deficit node
  const net = summary.total_income - summary.total_expenses;
  const surplusIndex = nodes.length;
  if (net > 0) {
    nodes.push({ name: "Savings" });
  } else if (net < 0) {
    nodes.push({ name: "Deficit" });
  }

  // Links: income sources → hub
  incomeCategories.forEach((c, i) => {
    links.push({ source: i, target: hubIndex, value: c.amount });
  });

  // Aggregate small income categories not shown
  const shownIncomeTotal = incomeCategories.reduce(
    (sum, c) => sum + c.amount,
    0,
  );
  const otherIncome = summary.total_income - shownIncomeTotal;
  if (otherIncome > 0) {
    nodes.splice(hubIndex, 0, { name: "Other Income" });
    // Shift all indices after this insertion
    // Recalculate: hubIndex shifted by 1
    // Simpler: rebuild with the "Other" included in income list
    // Let's just rebuild cleanly
    return buildSankeyDataClean(
      summary,
      incomeCategories,
      expenseCategories,
      otherIncome,
      net,
    );
  }

  // Links: hub → expense categories
  expenseCategories.forEach((c, i) => {
    links.push({
      source: hubIndex,
      target: expenseStartIndex + i,
      value: c.amount,
    });
  });

  // Aggregate small expense categories
  const shownExpenseTotal = expenseCategories.reduce(
    (sum, c) => sum + c.amount,
    0,
  );
  const otherExpenses = summary.total_expenses - shownExpenseTotal;
  if (otherExpenses > 0) {
    return buildSankeyDataClean(
      summary,
      incomeCategories,
      expenseCategories,
      0,
      net,
    );
  }

  // Link: hub → surplus/deficit
  if (net !== 0) {
    links.push({
      source: hubIndex,
      target: surplusIndex,
      value: Math.abs(net),
    });
  }

  return { nodes, links };
}

/** Clean builder that handles "Other" aggregates properly. */
function buildSankeyDataClean(
  summary: IncomeExpenseSummary,
  incomeCategories: CategoryBreakdown[],
  expenseCategories: CategoryBreakdown[],
  _otherIncome: number,
  net: number,
) {
  const nodes: { name: string }[] = [];
  const links: { source: number; target: number; value: number }[] = [];

  // Income nodes
  incomeCategories.forEach((c) => nodes.push({ name: c.category }));
  const shownIncomeTotal = incomeCategories.reduce(
    (sum, c) => sum + c.amount,
    0,
  );
  const otherIncome = summary.total_income - shownIncomeTotal;
  let otherIncomeIdx = -1;
  if (otherIncome > 0) {
    otherIncomeIdx = nodes.length;
    nodes.push({ name: "Other Income" });
  }

  // Hub node
  const hubIndex = nodes.length;
  nodes.push({ name: "Total Income" });

  // Expense nodes
  const expenseStartIndex = nodes.length;
  expenseCategories.forEach((c) => nodes.push({ name: c.category }));
  const shownExpenseTotal = expenseCategories.reduce(
    (sum, c) => sum + c.amount,
    0,
  );
  const otherExpenses = summary.total_expenses - shownExpenseTotal;
  let otherExpenseIdx = -1;
  if (otherExpenses > 0) {
    otherExpenseIdx = nodes.length;
    nodes.push({ name: "Other Expenses" });
  }

  // Surplus/deficit node
  let surplusIdx = -1;
  if (net > 0) {
    surplusIdx = nodes.length;
    nodes.push({ name: "Savings" });
  } else if (net < 0) {
    surplusIdx = nodes.length;
    nodes.push({ name: "Deficit" });
  }

  // Income → hub links
  incomeCategories.forEach((c, i) => {
    links.push({ source: i, target: hubIndex, value: c.amount });
  });
  if (otherIncomeIdx >= 0) {
    links.push({
      source: otherIncomeIdx,
      target: hubIndex,
      value: otherIncome,
    });
  }

  // Hub → expense links
  expenseCategories.forEach((c, i) => {
    links.push({
      source: hubIndex,
      target: expenseStartIndex + i,
      value: c.amount,
    });
  });
  if (otherExpenseIdx >= 0) {
    links.push({
      source: hubIndex,
      target: otherExpenseIdx,
      value: otherExpenses,
    });
  }

  // Hub → surplus/deficit
  if (surplusIdx >= 0 && net !== 0) {
    links.push({
      source: hubIndex,
      target: surplusIdx,
      value: Math.abs(net),
    });
  }

  return { nodes, links };
}

/** Color palette for Sankey nodes. */
const INCOME_COLOR = "#48BB78"; // green
const EXPENSE_COLOR = "#F56565"; // red
const HUB_COLOR = "#4299E1"; // blue
const SAVINGS_COLOR = "#38B2AC"; // teal
const DEFICIT_COLOR = "#E53E3E"; // darker red

const INCOME_COLORS = [
  "#48BB78",
  "#68D391",
  "#9AE6B4",
  "#2F855A",
  "#276749",
  "#22543D",
  "#38A169",
  "#C6F6D5",
];
const EXPENSE_COLORS = [
  "#F56565",
  "#FC8181",
  "#FEB2B2",
  "#E53E3E",
  "#C53030",
  "#9B2C2C",
  "#DD6B20",
  "#ED8936",
  "#F6AD55",
  "#FEEBC8",
];

function getNodeColor(
  node: { name: string },
  nodeIndex: number,
  data: ReturnType<typeof buildSankeyDataClean>,
) {
  if (!data) return "#A0AEC0";
  const name = node.name;

  if (name === "Total Income") return HUB_COLOR;
  if (name === "Savings") return SAVINGS_COLOR;
  if (name === "Deficit") return DEFICIT_COLOR;

  // Find hub index
  const hubIdx = data.nodes.findIndex((n) => n.name === "Total Income");

  if (nodeIndex < hubIdx) {
    // Income node
    return INCOME_COLORS[nodeIndex % INCOME_COLORS.length];
  }
  // Expense node (or Other Expenses)
  const expIdx = nodeIndex - hubIdx - 1;
  return EXPENSE_COLORS[expIdx % EXPENSE_COLORS.length];
}

function getLinkColor(
  link: { source: number; target: number },
  data: ReturnType<typeof buildSankeyDataClean>,
) {
  if (!data) return "#A0AEC0";
  const hubIdx = data.nodes.findIndex((n) => n.name === "Total Income");
  const targetName = data.nodes[link.target]?.name;

  if (link.target === hubIdx) {
    // Income → hub: green tint
    return "rgba(72, 187, 120, 0.3)";
  }
  if (targetName === "Savings") return "rgba(56, 178, 172, 0.4)";
  if (targetName === "Deficit") return "rgba(229, 62, 62, 0.4)";
  // Hub → expense: red tint
  return "rgba(245, 101, 101, 0.3)";
}

/** Date range options for the widget. */
const DATE_RANGES = [
  { label: "This Month", getValue: () => getCurrentMonth() },
  { label: "Last Month", getValue: () => getLastMonth() },
  { label: "Last 3 Months", getValue: () => getLastNMonths(3) },
  { label: "Last 6 Months", getValue: () => getLastNMonths(6) },
  { label: "Year to Date", getValue: () => getYearToDate() },
];

function getCurrentMonth() {
  const now = new Date();
  const start = new Date(now.getFullYear(), now.getMonth(), 1);
  const end = new Date(now.getFullYear(), now.getMonth() + 1, 0);
  return { start: fmt(start), end: fmt(end) };
}

function getLastMonth() {
  const now = new Date();
  const start = new Date(now.getFullYear(), now.getMonth() - 1, 1);
  const end = new Date(now.getFullYear(), now.getMonth(), 0);
  return { start: fmt(start), end: fmt(end) };
}

function getLastNMonths(n: number) {
  const now = new Date();
  const end = new Date(now.getFullYear(), now.getMonth() + 1, 0);
  const start = new Date(now.getFullYear(), now.getMonth() - n + 1, 1);
  return { start: fmt(start), end: fmt(end) };
}

function getYearToDate() {
  const now = new Date();
  const start = new Date(now.getFullYear(), 0, 1);
  const end = new Date(now.getFullYear(), now.getMonth() + 1, 0);
  return { start: fmt(start), end: fmt(end) };
}

function fmt(d: Date) {
  return d.toISOString().split("T")[0];
}

/* Custom node renderer for colored rectangles with labels */
function SankeyNode({
  x,
  y,
  width,
  height,
  index,
  payload,
  sankeyData,
}: {
  x: number;
  y: number;
  width: number;
  height: number;
  index: number;
  payload: { name: string; value: number };
  sankeyData: ReturnType<typeof buildSankeyDataClean>;
}) {
  const color = getNodeColor(payload, index, sankeyData);
  const isHub = payload.name === "Total Income";

  return (
    <Layer key={`sankey-node-${index}`}>
      <Rectangle
        x={x}
        y={y}
        width={width}
        height={height}
        fill={color}
        fillOpacity={isHub ? 0.9 : 0.8}
      />
      {height > 14 && (
        <text
          x={x + width + 6}
          y={y + height / 2}
          textAnchor="start"
          dominantBaseline="central"
          fontSize={11}
          fill="#718096"
        >
          {payload.name}
        </text>
      )}
    </Layer>
  );
}

/* Custom link renderer for colored flows */
function SankeyLink({
  sourceX,
  targetX,
  sourceY,
  targetY,
  sourceControlX,
  targetControlX,
  linkWidth,
  index,
  payload,
  sankeyData,
}: {
  sourceX: number;
  targetX: number;
  sourceY: number;
  targetY: number;
  sourceControlX: number;
  targetControlX: number;
  linkWidth: number;
  index: number;
  payload: { source: number; target: number; value: number };
  sankeyData: ReturnType<typeof buildSankeyDataClean>;
}) {
  const color = getLinkColor(payload, sankeyData);

  return (
    <Layer key={`sankey-link-${index}`}>
      <path
        d={`
          M${sourceX},${sourceY + linkWidth / 2}
          C${sourceControlX},${sourceY + linkWidth / 2}
            ${targetControlX},${targetY + linkWidth / 2}
            ${targetX},${targetY + linkWidth / 2}
          L${targetX},${targetY - linkWidth / 2}
          C${targetControlX},${targetY - linkWidth / 2}
            ${sourceControlX},${sourceY - linkWidth / 2}
            ${sourceX},${sourceY - linkWidth / 2}
          Z
        `}
        fill={color}
        strokeWidth={0}
      />
    </Layer>
  );
}

const MoneyFlowWidgetBase: React.FC = () => {
  const { selectedUserId } = useUserView();
  const cardBg = useColorModeValue("white", "gray.800");
  const [rangeIndex, setRangeIndex] = useState(0);

  const range = DATE_RANGES[rangeIndex].getValue();

  const { data: summary, isLoading } = useQuery<IncomeExpenseSummary>({
    queryKey: [
      "income-expenses-summary",
      range.start,
      range.end,
      selectedUserId,
    ],
    queryFn: async () => {
      const params: Record<string, string> = {
        start_date: range.start,
        end_date: range.end,
      };
      if (selectedUserId) params.user_id = selectedUserId;
      const response = await api.get("/income-expenses/summary", { params });
      return response.data;
    },
  });

  const sankeyData = summary ? buildSankeyData(summary) : null;

  if (isLoading) {
    return (
      <Card bg={cardBg}>
        <CardBody>
          <Heading size="md" mb={4}>
            Money Flow
          </Heading>
          <Box
            h="300px"
            display="flex"
            alignItems="center"
            justifyContent="center"
          >
            <Text color="gray.500">Loading...</Text>
          </Box>
        </CardBody>
      </Card>
    );
  }

  if (!summary || !sankeyData) {
    return (
      <Card bg={cardBg}>
        <CardBody>
          <Heading size="md" mb={4}>
            Money Flow
          </Heading>
          <Box
            h="200px"
            display="flex"
            alignItems="center"
            justifyContent="center"
          >
            <Text color="gray.500">
              No transaction data available for this period.
            </Text>
          </Box>
        </CardBody>
      </Card>
    );
  }

  return (
    <Card bg={cardBg}>
      <CardBody>
        <HStack justify="space-between" mb={4}>
          <Heading size="md">Money Flow</Heading>
          <Select
            size="sm"
            w="160px"
            value={rangeIndex}
            onChange={(e) => setRangeIndex(Number(e.target.value))}
          >
            {DATE_RANGES.map((r, i) => (
              <option key={r.label} value={i}>
                {r.label}
              </option>
            ))}
          </Select>
        </HStack>

        <HStack spacing={6} mb={3} justify="center" fontSize="sm">
          <HStack>
            <Box w={3} h={3} borderRadius="sm" bg={INCOME_COLOR} />
            <Text>Income: {formatCurrency(summary.total_income)}</Text>
          </HStack>
          <HStack>
            <Box w={3} h={3} borderRadius="sm" bg={EXPENSE_COLOR} />
            <Text>Expenses: {formatCurrency(summary.total_expenses)}</Text>
          </HStack>
          <HStack>
            <Box
              w={3}
              h={3}
              borderRadius="sm"
              bg={summary.net >= 0 ? SAVINGS_COLOR : DEFICIT_COLOR}
            />
            <Text>
              {summary.net >= 0 ? "Savings" : "Deficit"}:{" "}
              {formatCurrency(Math.abs(summary.net))}
            </Text>
          </HStack>
        </HStack>

        <Box
          role="img"
          aria-label="Sankey diagram showing money flow from income sources to expense categories"
        >
          <ResponsiveContainer width="100%" height={400}>
            <Sankey
              data={sankeyData}
              nodePadding={24}
              nodeWidth={10}
              linkCurvature={0.5}
              margin={{ top: 10, right: 160, bottom: 10, left: 10 }}
              node={(props: any) => (
                <SankeyNode {...props} sankeyData={sankeyData} />
              )}
              link={(props: any) => (
                <SankeyLink {...props} sankeyData={sankeyData} />
              )}
            >
              <Tooltip
                formatter={(value: number) => formatCurrency(value)}
                contentStyle={{
                  backgroundColor: "white",
                  border: "1px solid #E2E8F0",
                  borderRadius: "6px",
                  fontSize: "12px",
                }}
              />
            </Sankey>
          </ResponsiveContainer>
        </Box>
      </CardBody>
    </Card>
  );
};

export const MoneyFlowWidget = memo(MoneyFlowWidgetBase);
