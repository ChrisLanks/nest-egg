/**
 * Net Worth Timeline — full-page stacked area chart showing historical
 * asset/liability breakdown from /dashboard/net-worth-history.
 */

import {
  Alert,
  AlertIcon,
  Box,
  Button,
  ButtonGroup,
  Card,
  CardBody,
  Container,
  FormControl,
  FormLabel,
  Heading,
  HStack,
  Input,
  Modal,
  ModalBody,
  ModalCloseButton,
  ModalContent,
  ModalFooter,
  ModalHeader,
  ModalOverlay,
  SimpleGrid,
  Spinner,
  Stat,
  StatArrow,
  StatHelpText,
  StatLabel,
  StatNumber,
  Text,
  useColorModeValue,
  useDisclosure,
  VStack,
} from "@chakra-ui/react";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import api from "../services/api";
import { useUserView } from "../contexts/UserViewContext";

type TimeRange = "1M" | "3M" | "6M" | "1Y" | "2Y" | "ALL" | "CUSTOM";

interface NetWorthPoint {
  snapshot_date: string;
  total_net_worth: number;
  total_assets: number;
  total_liabilities: number;
  cash_and_checking: number;
  savings: number;
  investments: number;
  retirement: number;
  property: number;
  vehicles: number;
  other_assets: number;
  credit_cards: number;
  loans: number;
  mortgages: number;
  student_loans: number;
  other_debts: number;
}

const fmt = (v: number) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    notation: "compact",
    maximumFractionDigits: 1,
  }).format(v);

const fmtFull = (v: number) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(v);

const ASSET_LAYERS = [
  { key: "cash_and_checking", label: "Cash & Checking", color: "#38B2AC" },
  { key: "savings", label: "Savings", color: "#4299E1" },
  { key: "investments", label: "Investments", color: "#805AD5" },
  { key: "retirement", label: "Retirement", color: "#6B46C1" },
  { key: "property", label: "Property", color: "#48BB78" },
  { key: "vehicles", label: "Vehicles", color: "#68D391" },
  { key: "other_assets", label: "Other Assets", color: "#A0AEC0" },
] as const;

const DEBT_LAYERS = [
  { key: "mortgages", label: "Mortgages", color: "#FC8181" },
  { key: "credit_cards", label: "Credit Cards", color: "#F56565" },
  { key: "loans", label: "Loans", color: "#FBD38D" },
  { key: "student_loans", label: "Student Loans", color: "#F6AD55" },
  { key: "other_debts", label: "Other Debts", color: "#FED7D7" },
] as const;

function getDateRange(
  range: TimeRange,
  customStart: string,
  customEnd: string,
) {
  const now = new Date();
  let start: Date;
  let end: Date | null = null;

  switch (range) {
    case "1M":
      start = new Date(now.getFullYear(), now.getMonth() - 1, now.getDate());
      break;
    case "3M":
      start = new Date(now.getFullYear(), now.getMonth() - 3, now.getDate());
      break;
    case "6M":
      start = new Date(now.getFullYear(), now.getMonth() - 6, now.getDate());
      break;
    case "1Y":
      start = new Date(now.getFullYear() - 1, now.getMonth(), now.getDate());
      break;
    case "2Y":
      start = new Date(now.getFullYear() - 2, now.getMonth(), now.getDate());
      break;
    case "ALL":
      start = new Date(now.getFullYear() - 20, 0, 1);
      break;
    case "CUSTOM":
      start = customStart
        ? new Date(customStart)
        : new Date(now.getFullYear() - 1, now.getMonth(), now.getDate());
      if (customEnd) end = new Date(customEnd);
      break;
    default:
      start = new Date(now.getFullYear() - 1, now.getMonth(), now.getDate());
  }
  return { start, end };
}

export default function NetWorthTimelinePage() {
  const { selectedUserId } = useUserView();
  const tooltipBg = useColorModeValue("#FFFFFF", "#2D3748");
  const tooltipBorder = useColorModeValue("#E2E8F0", "#4A5568");

  const [timeRange, setTimeRange] = useState<TimeRange>("1Y");
  const [customStart, setCustomStart] = useState("");
  const [customEnd, setCustomEnd] = useState("");
  const [viewMode, setViewMode] = useState<"breakdown" | "summary">(
    "breakdown",
  );
  const { isOpen, onOpen, onClose } = useDisclosure();

  const { data: rawData, isLoading, isError } = useQuery<NetWorthPoint[]>({
    queryKey: [
      "net-worth-history",
      timeRange,
      customStart,
      customEnd,
      selectedUserId,
    ],
    queryFn: async () => {
      const { start, end } = getDateRange(timeRange, customStart, customEnd);
      const params: Record<string, string> = {
        start_date: start.toISOString().split("T")[0],
      };
      if (end) params.end_date = end.toISOString().split("T")[0];
      if (selectedUserId) params.user_id = selectedUserId;
      const response = await api.get("/dashboard/net-worth-history", {
        params,
      });
      return response.data;
    },
  });

  const data = rawData ?? [];

  const chartData = data.map((pt) => ({
    date: new Date(pt.snapshot_date + "T00:00:00").toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
    }),
    ...Object.fromEntries(
      ASSET_LAYERS.map(({ key }) => [
        key,
        pt[key as keyof NetWorthPoint] as number,
      ]),
    ),
    ...Object.fromEntries(
      DEBT_LAYERS.map(({ key }) => [
        key,
        -Math.abs(pt[key as keyof NetWorthPoint] as number),
      ]),
    ),
    total_net_worth: pt.total_net_worth,
    total_assets: pt.total_assets,
    total_liabilities: pt.total_liabilities,
  }));

  const latest = data[data.length - 1];
  const earliest = data[0];
  const netWorthChange =
    latest && earliest
      ? latest.total_net_worth - earliest.total_net_worth
      : null;
  const netWorthChangePct =
    netWorthChange !== null && earliest && earliest.total_net_worth !== 0
      ? (netWorthChange / Math.abs(earliest.total_net_worth)) * 100
      : null;

  return (
    <Container maxW="container.xl" py={8}>
      <VStack spacing={6} align="stretch">
        <HStack justify="space-between" align="start" flexWrap="wrap" gap={3}>
          <Box>
            <Heading size="lg">Net Worth Timeline</Heading>
            <Text color="text.secondary" mt={1} fontSize="sm">
              Historical breakdown of your assets and liabilities over time.
            </Text>
          </Box>
          <HStack spacing={2} flexWrap="wrap">
            <ButtonGroup size="sm" isAttached variant="outline">
              <Button
                colorScheme={viewMode === "breakdown" ? "brand" : "gray"}
                onClick={() => setViewMode("breakdown")}
              >
                Breakdown
              </Button>
              <Button
                colorScheme={viewMode === "summary" ? "brand" : "gray"}
                onClick={() => setViewMode("summary")}
              >
                Summary
              </Button>
            </ButtonGroup>
            <ButtonGroup size="sm" isAttached variant="outline">
              {(["1M", "3M", "6M", "1Y", "2Y", "ALL"] as TimeRange[]).map(
                (r) => (
                  <Button
                    key={r}
                    colorScheme={timeRange === r ? "brand" : "gray"}
                    onClick={() => setTimeRange(r)}
                  >
                    {r}
                  </Button>
                ),
              )}
              <Button
                colorScheme={timeRange === "CUSTOM" ? "brand" : "gray"}
                onClick={onOpen}
              >
                Custom
              </Button>
            </ButtonGroup>
          </HStack>
        </HStack>

        {/* Summary stat cards */}
        {latest && (
          <SimpleGrid columns={{ base: 2, md: 4 }} spacing={4}>
            <Card>
              <CardBody py={4}>
                <Stat>
                  <StatLabel fontSize="xs" color="text.secondary">
                    Net Worth
                  </StatLabel>
                  <StatNumber fontSize="lg">
                    {fmtFull(latest.total_net_worth)}
                  </StatNumber>
                  {netWorthChangePct !== null && (
                    <StatHelpText mb={0}>
                      <StatArrow
                        type={netWorthChange! >= 0 ? "increase" : "decrease"}
                      />
                      {Math.abs(netWorthChangePct).toFixed(1)}% in period
                    </StatHelpText>
                  )}
                </Stat>
              </CardBody>
            </Card>
            <Card>
              <CardBody py={4}>
                <Stat>
                  <StatLabel fontSize="xs" color="text.secondary">
                    Total Assets
                  </StatLabel>
                  <StatNumber fontSize="lg" color="green.500">
                    {fmtFull(latest.total_assets)}
                  </StatNumber>
                </Stat>
              </CardBody>
            </Card>
            <Card>
              <CardBody py={4}>
                <Stat>
                  <StatLabel fontSize="xs" color="text.secondary">
                    Total Liabilities
                  </StatLabel>
                  <StatNumber fontSize="lg" color="red.500">
                    {fmtFull(latest.total_liabilities)}
                  </StatNumber>
                </Stat>
              </CardBody>
            </Card>
            <Card>
              <CardBody py={4}>
                <Stat>
                  <StatLabel fontSize="xs" color="text.secondary">
                    Change
                  </StatLabel>
                  <StatNumber
                    fontSize="lg"
                    color={
                      netWorthChange === null
                        ? "inherit"
                        : netWorthChange >= 0
                          ? "green.500"
                          : "red.500"
                    }
                  >
                    {netWorthChange !== null ? fmtFull(netWorthChange) : "—"}
                  </StatNumber>
                  {data.length > 1 && (
                    <StatHelpText mb={0} fontSize="xs" color="text.muted">
                      since{" "}
                      {new Date(
                        earliest.snapshot_date + "T00:00:00",
                      ).toLocaleDateString("en-US", {
                        month: "short",
                        day: "numeric",
                        year: "numeric",
                      })}
                    </StatHelpText>
                  )}
                </Stat>
              </CardBody>
            </Card>
          </SimpleGrid>
        )}

        {/* Main chart */}
        <Card>
          <CardBody>
            {isLoading ? (
              <Box
                height={400}
                display="flex"
                alignItems="center"
                justifyContent="center"
              >
                <Spinner size="xl" color="brand.500" />
              </Box>
            ) : isError ? (
              <Alert status="error" borderRadius="md">
                <AlertIcon />
                Unable to load net worth history. Please try again.
              </Alert>
            ) : chartData.length === 0 ? (
              <Box
                height={400}
                display="flex"
                alignItems="center"
                justifyContent="center"
              >
                <VStack>
                  <Text color="text.muted">
                    No net worth snapshots found for this period.
                  </Text>
                  <Text fontSize="sm" color="text.muted">
                    Snapshots are recorded daily. Check back after tomorrow.
                  </Text>
                </VStack>
              </Box>
            ) : viewMode === "breakdown" ? (
              <ResponsiveContainer width="100%" height={420}>
                <AreaChart data={chartData} stackOffset="sign">
                  <CartesianGrid strokeDasharray="3 3" opacity={0.4} />
                  <XAxis dataKey="date" tick={{ fontSize: 11 }} />
                  <YAxis tickFormatter={fmt} tick={{ fontSize: 11 }} />
                  <Tooltip
                    formatter={(v: number, name: string) => [fmtFull(v), name]}
                    contentStyle={{
                      backgroundColor: tooltipBg,
                      border: `1px solid ${tooltipBorder}`,
                      fontSize: 12,
                    }}
                  />
                  <Legend iconSize={10} wrapperStyle={{ fontSize: 12 }} />
                  <defs>
                    {ASSET_LAYERS.map(({ key, color }) => (
                      <linearGradient
                        key={key}
                        id={`grad-${key}`}
                        x1="0"
                        y1="0"
                        x2="0"
                        y2="1"
                      >
                        <stop offset="5%" stopColor={color} stopOpacity={0.8} />
                        <stop
                          offset="95%"
                          stopColor={color}
                          stopOpacity={0.2}
                        />
                      </linearGradient>
                    ))}
                    {DEBT_LAYERS.map(({ key, color }) => (
                      <linearGradient
                        key={key}
                        id={`grad-${key}`}
                        x1="0"
                        y1="0"
                        x2="0"
                        y2="1"
                      >
                        <stop offset="5%" stopColor={color} stopOpacity={0.8} />
                        <stop
                          offset="95%"
                          stopColor={color}
                          stopOpacity={0.2}
                        />
                      </linearGradient>
                    ))}
                  </defs>
                  {ASSET_LAYERS.map(({ key, label, color }) => (
                    <Area
                      key={key}
                      type="monotone"
                      dataKey={key}
                      name={label}
                      stackId="1"
                      stroke={color}
                      fill={`url(#grad-${key})`}
                    />
                  ))}
                  {DEBT_LAYERS.map(({ key, label, color }) => (
                    <Area
                      key={key}
                      type="monotone"
                      dataKey={key}
                      name={label}
                      stackId="2"
                      stroke={color}
                      fill={`url(#grad-${key})`}
                    />
                  ))}
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <ResponsiveContainer width="100%" height={420}>
                <AreaChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" opacity={0.4} />
                  <XAxis dataKey="date" tick={{ fontSize: 11 }} />
                  <YAxis tickFormatter={fmt} tick={{ fontSize: 11 }} />
                  <Tooltip
                    formatter={(v: number, name: string) => [fmtFull(v), name]}
                    contentStyle={{
                      backgroundColor: tooltipBg,
                      border: `1px solid ${tooltipBorder}`,
                      fontSize: 12,
                    }}
                  />
                  <Legend iconSize={10} wrapperStyle={{ fontSize: 12 }} />
                  <defs>
                    <linearGradient
                      id="grad-assets"
                      x1="0"
                      y1="0"
                      x2="0"
                      y2="1"
                    >
                      <stop offset="5%" stopColor="#48BB78" stopOpacity={0.7} />
                      <stop
                        offset="95%"
                        stopColor="#48BB78"
                        stopOpacity={0.1}
                      />
                    </linearGradient>
                    <linearGradient
                      id="grad-liabilities"
                      x1="0"
                      y1="0"
                      x2="0"
                      y2="1"
                    >
                      <stop offset="5%" stopColor="#FC8181" stopOpacity={0.7} />
                      <stop
                        offset="95%"
                        stopColor="#FC8181"
                        stopOpacity={0.1}
                      />
                    </linearGradient>
                    <linearGradient
                      id="grad-networth"
                      x1="0"
                      y1="0"
                      x2="0"
                      y2="1"
                    >
                      <stop offset="5%" stopColor="#3182CE" stopOpacity={0.8} />
                      <stop
                        offset="95%"
                        stopColor="#3182CE"
                        stopOpacity={0.1}
                      />
                    </linearGradient>
                  </defs>
                  <Area
                    type="monotone"
                    dataKey="total_assets"
                    name="Total Assets"
                    stroke="#48BB78"
                    fill="url(#grad-assets)"
                    strokeWidth={1.5}
                  />
                  <Area
                    type="monotone"
                    dataKey="total_liabilities"
                    name="Total Liabilities"
                    stroke="#FC8181"
                    fill="url(#grad-liabilities)"
                    strokeWidth={1.5}
                  />
                  <Area
                    type="monotone"
                    dataKey="total_net_worth"
                    name="Net Worth"
                    stroke="#3182CE"
                    fill="url(#grad-networth)"
                    strokeWidth={2.5}
                  />
                </AreaChart>
              </ResponsiveContainer>
            )}
          </CardBody>
        </Card>
      </VStack>

      {/* Custom date range modal */}
      <Modal isOpen={isOpen} onClose={onClose} size="md">
        <ModalOverlay />
        <ModalContent>
          <ModalHeader>Custom Date Range</ModalHeader>
          <ModalCloseButton />
          <ModalBody pb={6}>
            <VStack spacing={4}>
              <FormControl>
                <FormLabel>Start Date</FormLabel>
                <Input
                  type="date"
                  value={customStart}
                  onChange={(e) => setCustomStart(e.target.value)}
                />
              </FormControl>
              <FormControl>
                <FormLabel>End Date (optional)</FormLabel>
                <Input
                  type="date"
                  value={customEnd}
                  onChange={(e) => setCustomEnd(e.target.value)}
                />
              </FormControl>
            </VStack>
          </ModalBody>
          <ModalFooter>
            <Button
              colorScheme="brand"
              mr={3}
              isDisabled={!customStart}
              onClick={() => {
                setTimeRange("CUSTOM");
                onClose();
              }}
            >
              Apply
            </Button>
            <Button variant="ghost" onClick={onClose}>
              Cancel
            </Button>
          </ModalFooter>
        </ModalContent>
      </Modal>
    </Container>
  );
}
