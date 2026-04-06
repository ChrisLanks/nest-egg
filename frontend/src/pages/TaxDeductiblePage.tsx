/**
 * Tax-Deductible Transactions Page
 * Track and export tax-deductible expenses for tax preparation
 */

import {
  Alert,
  AlertDescription,
  AlertIcon,
  AlertTitle,
  Box,
  Button,
  Card,
  CardBody,
  CardHeader,
  Container,
  Heading,
  HStack,
  SimpleGrid,
  Spinner,
  Stat,
  StatLabel,
  StatNumber,
  StatHelpText,
  Table,
  Tbody,
  Td,
  Text,
  Th,
  Thead,
  Tr,
  VStack,
  Badge,
  Center,
  useToast,
} from "@chakra-ui/react";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { FiDownload, FiTag } from "react-icons/fi";
import api from "../services/api";
import { useUserView } from "../contexts/UserViewContext";
import HelpHint from "../components/HelpHint";
import { helpContent } from "../constants/helpContent";
import { useCurrency } from "../contexts/CurrencyContext";

interface TaxTransaction {
  id: string;
  date: string;
  merchant_name: string;
  description: string;
  amount: number;
  category: string;
  account_name: string;
}

interface TaxSummary {
  label_id: string;
  label_name: string;
  label_color: string;
  total_amount: number;
  transaction_count: number;
  transactions: TaxTransaction[];
}

interface TaxLabel {
  id: string;
  name: string;
  color: string;
}

export default function TaxDeductiblePage() {
  const { currency } = useCurrency();
  const queryClient = useQueryClient();
  const toast = useToast();
  const { selectedUserId, effectiveUserId, canWriteResource } = useUserView();
  const canEdit = canWriteResource("category");

  // Default to current tax year (Jan 1 - Dec 31)
  const currentYear = new Date().getFullYear();
  const [startDate, setStartDate] = useState(`${currentYear}-01-01`);
  const [endDate, setEndDate] = useState(`${currentYear}-12-31`);

  // Check if tax labels exist
  const { data: allLabels = [] } = useQuery<TaxLabel[]>({
    queryKey: ["labels"],
    queryFn: async () => {
      const response = await api.get("/labels/");
      return response.data;
    },
  });

  const taxLabelNames = [
    "Medical & Dental",
    "Charitable Donations",
    "Business Expenses",
    "Education",
    "Home Office",
  ];

  const taxLabelsExist = taxLabelNames.every((name) =>
    allLabels.some((label) => label.name === name),
  );

  const taxLabelDescriptions: Record<string, string> = {
    "Medical & Dental":
      "Deductible if total medical expenses exceed 7.5% of your AGI (Schedule A). Includes doctor visits, prescriptions, dental work, vision care, and health insurance premiums not paid with pre-tax dollars.",
    "Charitable Donations":
      "Deductible up to 60% of AGI for cash donations to qualified 501(c)(3) organizations (Schedule A). Keep receipts for donations over $250.",
    "Business Expenses":
      "Deductible on Schedule C if you are self-employed or have a side business. Includes supplies, software, travel, and professional services.",
    Education:
      "Deductible via Lifetime Learning Credit (up to $2,000) or tuition/fees deduction. Student loan interest is deductible up to $2,500 (above-the-line).",
    "Home Office":
      "Deductible if you use a dedicated space regularly and exclusively for business. Simplified method: $5/sq ft up to 300 sq ft ($1,500 max).",
  };

  const taxLabelColors: Record<string, string> = {
    "Medical & Dental": "#48BB78",
    "Charitable Donations": "#4299E1",
    "Business Expenses": "#9F7AEA",
    Education: "#ED8936",
    "Home Office": "#F56565",
  };

  // Initialize tax labels
  const initializeMutation = useMutation({
    mutationFn: async () => {
      const response = await api.post("/labels/tax-deductible/initialize");
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["labels"] });
      queryClient.invalidateQueries({ queryKey: ["tax-deductible"] });
      toast({
        title: "Tax labels initialized",
        description: "5 tax-deductible labels have been created",
        status: "success",
        duration: 3000,
        isClosable: true,
      });
    },
    onError: () => {
      toast({
        title: "Failed to initialize labels",
        status: "error",
        duration: 5000,
        isClosable: true,
      });
    },
  });

  // Fetch tax-deductible summary
  const {
    data: summaries = [],
    isLoading,
    isError: summariesError,
    refetch: refetchSummaries,
  } = useQuery<TaxSummary[]>({
    queryKey: ["tax-deductible", startDate, endDate, effectiveUserId],
    queryFn: async () => {
      const params = new URLSearchParams({
        start_date: startDate,
        end_date: endDate,
      });
      if (selectedUserId) params.append("user_id", effectiveUserId);

      const response = await api.get(`/labels/tax-deductible?${params}`);
      return response.data;
    },
    enabled: taxLabelsExist,
  });

  // Export to CSV
  const handleExport = async () => {
    try {
      const params = new URLSearchParams({
        start_date: startDate,
        end_date: endDate,
      });
      if (selectedUserId) params.append("user_id", effectiveUserId);

      const url = `/labels/tax-deductible/export?${params}`;

      // Use axios to make authenticated request
      const response = await api.get(url, {
        responseType: "blob", // Important for file download
      });

      // Create blob and download
      const blob = new Blob([response.data], {
        type: "text/csv;charset=utf-8;",
      });
      const downloadUrl = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = downloadUrl;
      link.download = `tax-deductible-${startDate}-to-${endDate}.csv`;
      link.click();
      URL.revokeObjectURL(downloadUrl);

      toast({
        title: "Export successful",
        description: "Your CSV file has been downloaded",
        status: "success",
        duration: 3000,
        isClosable: true,
      });
    } catch {
      toast({
        title: "Export failed",
        description: "Failed to download CSV file",
        status: "error",
        duration: 5000,
        isClosable: true,
      });
    }
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency,
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(amount);
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  };

  const totalDeductible = summaries.reduce((sum, s) => sum + s.total_amount, 0);
  const totalTransactions = summaries.reduce(
    (sum, s) => sum + s.transaction_count,
    0,
  );

  return (
    <Container maxW="container.xl" py={8}>
      <VStack spacing={8} align="stretch">
        {/* Header */}
        <Box>
          <Heading>Tax-Deductible Transactions</Heading>
          <Text color="text.secondary" mt={2}>
            Track and export deductible expenses for tax preparation
            <HelpHint hint={helpContent.tax.taxDeductible} />
          </Text>
        </Box>

        {/* Initialize tax labels if needed */}
        {!taxLabelsExist && !initializeMutation.isPending && canEdit && (
          <Card bg="bg.info" borderColor="blue.200">
            <CardBody>
              <VStack align="start" spacing={3}>
                <HStack>
                  <FiTag />
                  <Text fontWeight="bold">Get Started with Tax Tracking</Text>
                </HStack>
                <Text fontSize="sm">
                  Initialize tax-deductible labels to start tracking expenses by
                  category (Medical & Dental, Charitable Donations, Business
                  Expenses, Education, Home Office).
                </Text>
                <Button
                  colorScheme="blue"
                  size="sm"
                  onClick={() => initializeMutation.mutate()}
                  isLoading={initializeMutation.isPending}
                >
                  Initialize Tax Labels
                </Button>
              </VStack>
            </CardBody>
          </Card>
        )}

        {taxLabelsExist && (
          <>
            {/* Date Range Selector */}
            <Card>
              <CardBody>
                <HStack spacing={4}>
                  <Box>
                    <Text fontSize="sm" fontWeight="semibold" mb={1}>
                      Start Date
                    </Text>
                    <input
                      type="date"
                      value={startDate}
                      onChange={(e) => setStartDate(e.target.value)}
                      style={{
                        padding: "8px",
                        border: "1px solid #E2E8F0",
                        borderRadius: "6px",
                      }}
                    />
                  </Box>
                  <Box>
                    <Text fontSize="sm" fontWeight="semibold" mb={1}>
                      End Date
                    </Text>
                    <input
                      type="date"
                      value={endDate}
                      onChange={(e) => setEndDate(e.target.value)}
                      style={{
                        padding: "8px",
                        border: "1px solid #E2E8F0",
                        borderRadius: "6px",
                      }}
                    />
                  </Box>
                  <Box flex={1} />
                  <Button
                    leftIcon={<FiDownload />}
                    colorScheme="green"
                    onClick={handleExport}
                    isDisabled={totalTransactions === 0}
                  >
                    Export CSV
                  </Button>
                </HStack>
              </CardBody>
            </Card>

            {/* Summary Cards */}
            <SimpleGrid columns={{ base: 1, md: 3 }} spacing={6}>
              <Card>
                <CardBody>
                  <Stat>
                    <StatLabel>Total Deductible</StatLabel>
                    <StatNumber>{formatCurrency(totalDeductible)}</StatNumber>
                    <StatHelpText>{`${startDate} to ${endDate}`}</StatHelpText>
                  </Stat>
                </CardBody>
              </Card>

              <Card>
                <CardBody>
                  <Stat>
                    <StatLabel>Total Transactions</StatLabel>
                    <StatNumber>{totalTransactions}</StatNumber>
                    <StatHelpText>Across all categories</StatHelpText>
                  </Stat>
                </CardBody>
              </Card>

              <Card>
                <CardBody>
                  <Stat>
                    <StatLabel>Tax Categories</StatLabel>
                    <StatNumber>{summaries.length}</StatNumber>
                    <StatHelpText>With transactions</StatHelpText>
                  </Stat>
                </CardBody>
              </Card>
            </SimpleGrid>

            {/* Error State */}
            {summariesError && (
              <Center py={12}>
                <VStack spacing={4}>
                  <Alert status="error" borderRadius="md">
                    <AlertIcon />
                    <AlertTitle>Failed to load tax data.</AlertTitle>
                    <AlertDescription>Please try again.</AlertDescription>
                  </Alert>
                  <Button colorScheme="blue" onClick={() => refetchSummaries()}>
                    Retry
                  </Button>
                </VStack>
              </Center>
            )}

            {/* Loading State */}
            {isLoading && (
              <Center py={12}>
                <Spinner size="xl" color="brand.500" />
              </Center>
            )}

            {/* Empty State */}
            {!isLoading && !summariesError && totalTransactions === 0 && (
              <Card>
                <CardBody>
                  <VStack spacing={6} align="stretch">
                    <VStack spacing={2} textAlign="center">
                      <Heading size="md">
                        No tax-deductible transactions yet
                      </Heading>
                      <Text color="text.secondary" maxW="lg" mx="auto">
                        Label your transactions with tax categories to track
                        deductible expenses. Here are the categories you can
                        use:
                      </Text>
                    </VStack>

                    <SimpleGrid columns={{ base: 1, md: 2 }} spacing={4}>
                      {taxLabelNames.map((name) => (
                        <Box
                          key={name}
                          p={4}
                          borderWidth={1}
                          borderColor="border.default"
                          borderRadius="md"
                          bg="bg.subtle"
                        >
                          <HStack mb={2}>
                            <Box
                              width="10px"
                              height="10px"
                              borderRadius="sm"
                              bg={taxLabelColors[name]}
                              flexShrink={0}
                            />
                            <Text fontWeight="semibold" fontSize="sm">
                              {name}
                            </Text>
                          </HStack>
                          <Text fontSize="xs" color="text.secondary">
                            {taxLabelDescriptions[name]}
                          </Text>
                        </Box>
                      ))}
                    </SimpleGrid>

                    <Box
                      p={4}
                      bg="bg.info"
                      borderRadius="md"
                      borderWidth={1}
                      borderColor="blue.200"
                    >
                      <Text fontWeight="semibold" mb={2} fontSize="sm">
                        How to use
                      </Text>
                      <VStack align="start" spacing={1}>
                        <HStack spacing={2} fontSize="sm" color="text.secondary">
                          <Badge
                            colorScheme="blue"
                            borderRadius="full"
                            minW="20px"
                            textAlign="center"
                          >
                            1
                          </Badge>
                          <Text>
                            Go to the <strong>Transactions</strong> page
                          </Text>
                        </HStack>
                        <HStack spacing={2} fontSize="sm" color="text.secondary">
                          <Badge
                            colorScheme="blue"
                            borderRadius="full"
                            minW="20px"
                            textAlign="center"
                          >
                            2
                          </Badge>
                          <Text>
                            Select a transaction and apply a tax label (e.g.,
                            "Medical & Dental")
                          </Text>
                        </HStack>
                        <HStack spacing={2} fontSize="sm" color="text.secondary">
                          <Badge
                            colorScheme="blue"
                            borderRadius="full"
                            minW="20px"
                            textAlign="center"
                          >
                            3
                          </Badge>
                          <Text>
                            Return here to view totals by category and export a
                            CSV for tax prep
                          </Text>
                        </HStack>
                      </VStack>
                    </Box>
                  </VStack>
                </CardBody>
              </Card>
            )}

            {/* Tax Categories */}
            {!isLoading && summaries.length > 0 && (
              <VStack spacing={6} align="stretch">
                {summaries.map((summary) => (
                  <Card key={summary.label_id}>
                    <CardHeader>
                      <HStack justify="space-between">
                        <HStack>
                          <Box
                            width="12px"
                            height="12px"
                            borderRadius="sm"
                            bg={summary.label_color}
                          />
                          <Heading size="md">
                            {summary.label_name}
                            {taxLabelDescriptions[summary.label_name] && (
                              <HelpHint
                                hint={taxLabelDescriptions[summary.label_name]}
                                size="md"
                                placement="right"
                              />
                            )}
                          </Heading>
                        </HStack>
                        <VStack align="end" spacing={0}>
                          <Text
                            fontSize="2xl"
                            fontWeight="bold"
                            color="finance.positive"
                          >
                            {formatCurrency(summary.total_amount)}
                          </Text>
                          <Text fontSize="sm" color="text.secondary">
                            {summary.transaction_count} transaction
                            {summary.transaction_count !== 1 ? "s" : ""}
                          </Text>
                        </VStack>
                      </HStack>
                    </CardHeader>

                    <CardBody>
                      <Table variant="simple" size="sm">
                        <Thead>
                          <Tr>
                            <Th>Date</Th>
                            <Th>Merchant</Th>
                            <Th>Category</Th>
                            <Th>Account</Th>
                            <Th isNumeric>Amount</Th>
                          </Tr>
                        </Thead>
                        <Tbody>
                          {summary.transactions.map((txn) => (
                            <Tr key={txn.id}>
                              <Td>{formatDate(txn.date)}</Td>
                              <Td>
                                <Text fontWeight="medium">
                                  {txn.merchant_name}
                                </Text>
                                {txn.description && (
                                  <Text
                                    fontSize="xs"
                                    color="text.secondary"
                                    noOfLines={1}
                                  >
                                    {txn.description}
                                  </Text>
                                )}
                              </Td>
                              <Td>
                                <Badge colorScheme="gray" fontSize="xs">
                                  {txn.category}
                                </Badge>
                              </Td>
                              <Td>
                                <Text fontSize="sm" color="text.secondary">
                                  {txn.account_name}
                                </Text>
                              </Td>
                              <Td isNumeric fontWeight="semibold">
                                {formatCurrency(txn.amount)}
                              </Td>
                            </Tr>
                          ))}
                        </Tbody>
                      </Table>
                    </CardBody>
                  </Card>
                ))}
              </VStack>
            )}
          </>
        )}
      </VStack>
    </Container>
  );
}
