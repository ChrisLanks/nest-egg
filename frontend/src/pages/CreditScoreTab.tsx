/**
 * Credit Score Tab — manually track and chart credit score history.
 *
 * Users enter scores they pull from Equifax, TransUnion, Experian, FICO,
 * or their bank's built-in credit monitoring tool. Displayed as a line chart
 * with FICO band annotations.
 */

import {
  Alert,
  AlertDescription,
  AlertIcon,
  Badge,
  Box,
  Button,
  Divider,
  FormControl,
  FormLabel,
  HStack,
  IconButton,
  Input,
  Select,
  SimpleGrid,
  Stat,
  StatLabel,
  StatNumber,
  Text,
  Textarea,
  Tooltip,
  VStack,
} from "@chakra-ui/react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip as RechartsTooltip,
  XAxis,
  YAxis,
} from "recharts";
import { DeleteIcon } from "@chakra-ui/icons";
import api from "../services/api";
import { useUserView } from "../contexts/UserViewContext";

interface CreditScoreEntry {
  id: string;
  score: number;
  score_date: string;
  provider: string;
  notes?: string;
  band: string;
  created_at: string;
}

interface CreditScoreHistory {
  entries: CreditScoreEntry[];
  latest_score: number | null;
  latest_band: string | null;
  change_from_previous: number | null;
}

const FICO_BANDS = [
  { label: "Poor", min: 300, max: 579, color: "#E53E3E" },
  { label: "Fair", min: 580, max: 669, color: "#ED8936" },
  { label: "Good", min: 670, max: 739, color: "#ECC94B" },
  { label: "Very Good", min: 740, max: 799, color: "#48BB78" },
  { label: "Exceptional", min: 800, max: 850, color: "#38A169" },
];

const PROVIDERS = ["Equifax", "TransUnion", "Experian", "FICO", "Other"];

const bandColor = (band: string) => {
  switch (band) {
    case "Exceptional": return "green";
    case "Very Good": return "green";
    case "Good": return "yellow";
    case "Fair": return "orange";
    case "Poor": return "red";
    default: return "gray";
  }
};

const formatDate = (dateStr: string) => {
  const [y, m, d] = dateStr.split("-").map(Number);
  return new Date(y, m - 1, d).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
};

const formatShortDate = (dateStr: string) => {
  const [y, m, d] = dateStr.split("-").map(Number);
  return new Date(y, m - 1, d).toLocaleDateString("en-US", { month: "short", year: "numeric" });
};

export const CreditScoreTab = () => {
  const { selectedUserId, effectiveUserId } = useUserView();
  const queryClient = useQueryClient();
  const today = new Date().toISOString().split("T")[0];

  const [score, setScore] = useState("");
  const [scoreDate, setScoreDate] = useState(today);
  const [provider, setProvider] = useState("Equifax");
  const [notes, setNotes] = useState("");
  const [formError, setFormError] = useState("");

  const params: Record<string, string> = {};
  if (selectedUserId) params.user_id = effectiveUserId;

  const { data, isLoading, isError } = useQuery<CreditScoreHistory>({
    queryKey: ["credit-scores", effectiveUserId],
    queryFn: () =>
      api.get<CreditScoreHistory>("/credit-scores", { params }).then((r) => r.data),
  });

  const addMutation = useMutation({
    mutationFn: (body: { score: number; score_date: string; provider: string; notes?: string }) =>
      api.post("/credit-scores", body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["credit-scores"] });
      setScore("");
      setScoreDate(today);
      setProvider("Equifax");
      setNotes("");
      setFormError("");
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.delete(`/credit-scores/${id}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["credit-scores"] }),
  });

  const handleSubmit = () => {
    const numScore = parseInt(score, 10);
    if (!score || isNaN(numScore) || numScore < 300 || numScore > 850) {
      setFormError("Score must be between 300 and 850.");
      return;
    }
    if (!scoreDate) {
      setFormError("Date is required.");
      return;
    }
    setFormError("");
    addMutation.mutate({
      score: numScore,
      score_date: scoreDate,
      provider,
      notes: notes || undefined,
    });
  };

  // Chart data — chronological order
  const chartData = [...(data?.entries ?? [])]
    .sort((a, b) => a.score_date.localeCompare(b.score_date))
    .map((e) => ({ date: e.score_date, score: e.score, provider: e.provider }));

  return (
    <VStack spacing={6} align="stretch">
      {/* Summary */}
      {data && data.latest_score !== null && (
        <SimpleGrid columns={{ base: 1, md: 3 }} spacing={4}>
          <Stat bg="bg.card" borderRadius="lg" p={4} borderWidth="1px" borderColor="border.subtle">
            <Tooltip label="Your most recently recorded credit score. Ranges: 800–850 Exceptional, 740–799 Very Good, 670–739 Good, 580–669 Fair, 300–579 Poor." hasArrow placement="top">
              <StatLabel fontSize="xs" color="text.secondary" cursor="help" textDecoration="underline dotted" display="inline-block">Latest Score</StatLabel>
            </Tooltip>
            <HStack align="baseline" spacing={2}>
              <StatNumber fontSize="2xl">{data.latest_score}</StatNumber>
              {data.latest_band && (
                <Badge colorScheme={bandColor(data.latest_band)} fontSize="xs">
                  {data.latest_band}
                </Badge>
              )}
            </HStack>
          </Stat>
          <Stat bg="bg.card" borderRadius="lg" p={4} borderWidth="1px" borderColor="border.subtle">
            <Tooltip label="How many points your score moved since the previous entry — positive is an improvement." hasArrow placement="top">
              <StatLabel fontSize="xs" color="text.secondary" cursor="help" textDecoration="underline dotted" display="inline-block">Change (last entry)</StatLabel>
            </Tooltip>
            <StatNumber
              fontSize="xl"
              color={
                data.change_from_previous === null
                  ? "text.secondary"
                  : data.change_from_previous > 0
                  ? "green.500"
                  : data.change_from_previous < 0
                  ? "red.500"
                  : "text.secondary"
              }
            >
              {data.change_from_previous === null
                ? "—"
                : `${data.change_from_previous > 0 ? "+" : ""}${data.change_from_previous} pts`}
            </StatNumber>
          </Stat>
          <Stat bg="bg.card" borderRadius="lg" p={4} borderWidth="1px" borderColor="border.subtle">
            <Tooltip label="Total number of score records you have entered. More data points give a better picture of your credit trend." hasArrow placement="top">
              <StatLabel fontSize="xs" color="text.secondary" cursor="help" textDecoration="underline dotted" display="inline-block">Entries Tracked</StatLabel>
            </Tooltip>
            <StatNumber fontSize="xl">{data.entries.length}</StatNumber>
          </Stat>
        </SimpleGrid>
      )}

      {/* Chart */}
      {chartData.length >= 2 && (
        <Box>
          <Text fontSize="sm" fontWeight="medium" mb={3}>Score History</Text>
          <Box borderWidth="1px" borderColor="border.subtle" borderRadius="lg" p={4}>
            <ResponsiveContainer width="100%" height={240}>
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
                <XAxis
                  dataKey="date"
                  tickFormatter={formatShortDate}
                  stroke="#718096"
                  style={{ fontSize: "11px" }}
                />
                <YAxis
                  domain={[300, 850]}
                  ticks={[300, 580, 670, 740, 800, 850]}
                  stroke="#718096"
                  style={{ fontSize: "11px" }}
                />
                <RechartsTooltip
                  formatter={(val: number) => [`${val}`, "Score"]}
                  labelFormatter={(d: string) => formatDate(d)}
                  contentStyle={{ borderRadius: "8px", fontSize: "12px" }}
                />
                {/* FICO band reference lines */}
                <ReferenceLine y={580} stroke="#ED8936" strokeDasharray="3 3" label={{ value: "Fair", position: "insideTopRight", fontSize: 10, fill: "#ED8936" }} />
                <ReferenceLine y={670} stroke="#ECC94B" strokeDasharray="3 3" label={{ value: "Good", position: "insideTopRight", fontSize: 10, fill: "#718096" }} />
                <ReferenceLine y={740} stroke="#48BB78" strokeDasharray="3 3" label={{ value: "Very Good", position: "insideTopRight", fontSize: 10, fill: "#48BB78" }} />
                <ReferenceLine y={800} stroke="#38A169" strokeDasharray="3 3" label={{ value: "Exceptional", position: "insideTopRight", fontSize: 10, fill: "#38A169" }} />
                <Line
                  type="monotone"
                  dataKey="score"
                  stroke="#3182CE"
                  strokeWidth={2}
                  dot={{ fill: "#3182CE", r: 4 }}
                  activeDot={{ r: 6 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </Box>
        </Box>
      )}

      <Divider />

      {/* Add entry form */}
      <Box>
        <Text fontSize="sm" fontWeight="medium" mb={3}>Log a Score</Text>
        <SimpleGrid columns={{ base: 1, md: 2 }} spacing={3}>
          <FormControl isRequired>
            <Tooltip label="FICO scores range from 300–850. Get yours free from AnnualCreditReport.com, your bank's app, or your credit card issuer." hasArrow placement="top">
              <FormLabel fontSize="sm" cursor="help" textDecoration="underline dotted" display="inline-block">Score (300–850)</FormLabel>
            </Tooltip>
            <Input
              size="sm"
              type="number"
              min={300}
              max={850}
              placeholder="e.g. 742"
              value={score}
              onChange={(e) => setScore(e.target.value)}
            />
          </FormControl>
          <FormControl isRequired>
            <Tooltip label="The date the score was pulled. Lenders typically use scores from the past 30 days, so recent entries are most relevant." hasArrow placement="top">
              <FormLabel fontSize="sm" cursor="help" textDecoration="underline dotted" display="inline-block">Date Pulled</FormLabel>
            </Tooltip>
            <Input
              size="sm"
              type="date"
              value={scoreDate}
              onChange={(e) => setScoreDate(e.target.value)}
            />
          </FormControl>
          <FormControl isRequired>
            <Tooltip label="Equifax, Experian, and TransUnion each maintain separate credit files — scores can differ slightly between bureaus. FICO is a scoring model used by most lenders." hasArrow placement="top">
              <FormLabel fontSize="sm" cursor="help" textDecoration="underline dotted" display="inline-block">Bureau / Source</FormLabel>
            </Tooltip>
            <Select size="sm" value={provider} onChange={(e) => setProvider(e.target.value)}>
              {PROVIDERS.map((p) => (
                <option key={p} value={p}>{p}</option>
              ))}
            </Select>
          </FormControl>
          <FormControl>
            <Tooltip label="Optional context — e.g. which app you used, whether you applied for credit recently, or any changes you made that may have affected your score." hasArrow placement="top">
              <FormLabel fontSize="sm" cursor="help" textDecoration="underline dotted" display="inline-block">Notes (optional)</FormLabel>
            </Tooltip>
            <Textarea
              size="sm"
              rows={1}
              placeholder="e.g. pulled from Chase credit journey"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
            />
          </FormControl>
        </SimpleGrid>
        {formError && (
          <Alert status="error" mt={2} borderRadius="md" py={2}>
            <AlertIcon />
            <AlertDescription fontSize="sm">{formError}</AlertDescription>
          </Alert>
        )}
        <Button
          mt={3}
          size="sm"
          colorScheme="brand"
          isLoading={addMutation.isPending}
          onClick={handleSubmit}
        >
          Add Score
        </Button>
      </Box>

      {/* History table */}
      {data && data.entries.length > 0 && (
        <Box>
          <Text fontSize="sm" fontWeight="medium" mb={2}>History</Text>
          <VStack spacing={2} align="stretch">
            {data.entries.map((entry) => (
              <HStack
                key={entry.id}
                justify="space-between"
                p={3}
                borderWidth="1px"
                borderColor="border.subtle"
                borderRadius="md"
              >
                <HStack spacing={3}>
                  <Text fontSize="lg" fontWeight="bold">{entry.score}</Text>
                  <Badge colorScheme={bandColor(entry.band)} fontSize="xs">{entry.band}</Badge>
                  <Text fontSize="xs" color="text.secondary">{entry.provider}</Text>
                </HStack>
                <HStack spacing={3}>
                  <Text fontSize="xs" color="text.muted">{formatDate(entry.score_date)}</Text>
                  {entry.notes && (
                    <Text fontSize="xs" color="text.secondary" maxW="200px" noOfLines={1}>{entry.notes}</Text>
                  )}
                  <IconButton
                    aria-label="Delete entry"
                    icon={<DeleteIcon />}
                    size="xs"
                    variant="ghost"
                    colorScheme="red"
                    isLoading={deleteMutation.isPending}
                    onClick={() => deleteMutation.mutate(entry.id)}
                  />
                </HStack>
              </HStack>
            ))}
          </VStack>
        </Box>
      )}

      {isLoading && <Text color="text.secondary" fontSize="sm">Loading…</Text>}
      {isError && (
        <Alert status="error" borderRadius="md">
          <AlertIcon />
          <Text fontSize="sm">Unable to load credit score history.</Text>
        </Alert>
      )}

      {data && data.entries.length === 0 && !isLoading && (
        <Alert status="info" borderRadius="md">
          <AlertIcon />
          <AlertDescription fontSize="sm">
            No scores logged yet. Pull your score from Equifax, TransUnion, Experian, or your bank's free credit monitoring tool and enter it above.
          </AlertDescription>
        </Alert>
      )}

      {/* FICO bands reference */}
      <Box>
        <Text fontSize="xs" color="text.muted" mb={2}>FICO score ranges:</Text>
        <HStack spacing={2} flexWrap="wrap">
          {FICO_BANDS.map((band) => (
            <Badge
              key={band.label}
              colorScheme={bandColor(band.label)}
              variant="subtle"
              fontSize="xs"
            >
              {band.label}: {band.min}–{band.max}
            </Badge>
          ))}
        </HStack>
      </Box>
    </VStack>
  );
};
