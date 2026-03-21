/**
 * Tax lots panel for account detail - shows unrealized/realized gains and tax lot details
 */

import {
  Badge,
  Box,
  Button,
  Card,
  CardBody,
  Heading,
  HStack,
  Select,
  SimpleGrid,
  Spinner,
  Stat,
  StatLabel,
  StatNumber,
  Switch,
  Table,
  Tbody,
  Td,
  Text,
  Th,
  Thead,
  Tr,
  VStack,
  useDisclosure,
  useToast,
  FormControl,
  FormLabel,
  NumberInput,
  NumberInputField,
  Input,
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalCloseButton,
  ModalFooter,
} from "@chakra-ui/react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import {
  taxLotsApi,
  type TaxLot,
  type SaleRequest,
} from "../../../api/taxLots";

const formatCurrency = (amount: number) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(amount);

interface TaxLotsPanelProps {
  accountId: string;
  holdings: Array<{
    id: string;
    ticker: string;
    name: string | null;
    shares: number;
  }>;
  canEdit: boolean;
}

export const TaxLotsPanel = ({
  accountId,
  holdings,
  canEdit,
}: TaxLotsPanelProps) => {
  const [selectedHoldingId, setSelectedHoldingId] = useState<string | null>(
    null,
  );
  const [includeClosed, setIncludeClosed] = useState(false);
  const [gainsYear, setGainsYear] = useState(new Date().getFullYear());
  const queryClient = useQueryClient();
  const toast = useToast();

  // Sale modal state
  const {
    isOpen: isSaleOpen,
    onOpen: onSaleOpen,
    onClose: onSaleClose,
  } = useDisclosure();
  const [saleHoldingId, setSaleHoldingId] = useState("");
  const [saleQuantity, setSaleQuantity] = useState("");
  const [salePrice, setSalePrice] = useState("");
  const [saleDate, setSaleDate] = useState(
    new Date().toISOString().slice(0, 10),
  );
  const [saleMethod, setSaleMethod] =
    useState<SaleRequest["cost_basis_method"]>("FIFO");

  // Unrealized gains
  const { data: unrealizedGains, isLoading: unrealizedLoading } = useQuery({
    queryKey: ["unrealized-gains", accountId],
    queryFn: () => taxLotsApi.getUnrealizedGains(accountId),
  });

  // Realized gains
  const { data: realizedGains, isLoading: realizedLoading } = useQuery({
    queryKey: ["realized-gains", accountId, gainsYear],
    queryFn: () => taxLotsApi.getRealizedGains(accountId, gainsYear),
  });

  // Tax lots for selected holding
  const { data: taxLots, isLoading: lotsLoading } = useQuery({
    queryKey: ["tax-lots", selectedHoldingId, includeClosed],
    queryFn: () =>
      taxLotsApi.getHoldingTaxLots(selectedHoldingId!, includeClosed),
    enabled: !!selectedHoldingId,
  });

  // Record sale mutation
  const saleMutation = useMutation({
    mutationFn: (data: { holdingId: string; sale: SaleRequest }) =>
      taxLotsApi.recordSale(data.holdingId, data.sale),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ["tax-lots"] });
      queryClient.invalidateQueries({
        queryKey: ["unrealized-gains", accountId],
      });
      queryClient.invalidateQueries({
        queryKey: ["realized-gains", accountId],
      });
      queryClient.invalidateQueries({ queryKey: ["holdings"] });
      toast({
        title: "Sale recorded",
        description: `Realized ${formatCurrency(result.realized_gain_loss)} gain/loss`,
        status: "success",
        duration: 5000,
      });
      onSaleClose();
      resetSaleForm();
    },
    onError: (error: unknown) => {
      toast({
        title: "Failed to record sale",
        description:
          (error as { response?: { data?: { detail?: string } } }).response
            ?.data?.detail || "An error occurred",
        status: "error",
        duration: 5000,
      });
    },
  });

  const resetSaleForm = () => {
    setSaleQuantity("");
    setSalePrice("");
    setSaleDate(new Date().toISOString().slice(0, 10));
    setSaleMethod("FIFO");
  };

  const handleRecordSale = () => {
    if (!saleHoldingId || !saleQuantity || !salePrice) return;
    saleMutation.mutate({
      holdingId: saleHoldingId,
      sale: {
        quantity: parseFloat(saleQuantity),
        sale_price_per_share: parseFloat(salePrice),
        sale_date: saleDate,
        cost_basis_method: saleMethod,
      },
    });
  };

  const yearOptions = Array.from(
    { length: 5 },
    (_, i) => new Date().getFullYear() - i,
  );

  return (
    <Card>
      <CardBody>
        <VStack spacing={6} align="stretch">
          <Box>
            <HStack justify="space-between">
              <Heading size="md">Capital Gains & Tax Lots</Heading>
              {canEdit && (
                <Button
                  size="sm"
                  colorScheme="brand"
                  variant="outline"
                  onClick={() => {
                    if (holdings.length > 0) {
                      setSaleHoldingId(holdings[0].id);
                      onSaleOpen();
                    }
                  }}
                  isDisabled={holdings.length === 0}
                >
                  Record Sale
                </Button>
              )}
            </HStack>
            <Text fontSize="xs" color="text.muted" mt={1}>
              Track your investment gains and losses for tax purposes. Each time
              you buy shares at a different price, it creates a "tax lot." When
              you sell, the cost basis method (FIFO, LIFO, HIFO) determines
              which lots are sold first, affecting your tax bill.
            </Text>
          </Box>

          {/* Gains Summary */}
          <SimpleGrid columns={{ base: 1, md: 2 }} spacing={4}>
            {/* Unrealized */}
            <Box bg="bg.subtle" p={4} borderRadius="md">
              <Heading size="sm" mb={3}>
                Unrealized Gains
              </Heading>
              {unrealizedLoading ? (
                <Spinner size="sm" />
              ) : unrealizedGains ? (
                <SimpleGrid columns={2} spacing={2}>
                  <Stat size="sm">
                    <StatLabel>Total Gain/Loss</StatLabel>
                    <StatNumber
                      fontSize="md"
                      color={
                        unrealizedGains.total_unrealized_gain >= 0
                          ? "finance.positive"
                          : "finance.negative"
                      }
                    >
                      {formatCurrency(unrealizedGains.total_unrealized_gain)}
                    </StatNumber>
                  </Stat>
                  <Stat size="sm">
                    <StatLabel>Cost Basis</StatLabel>
                    <StatNumber fontSize="md">
                      {formatCurrency(unrealizedGains.total_cost_basis)}
                    </StatNumber>
                  </Stat>
                </SimpleGrid>
              ) : (
                <Text fontSize="sm" color="text.muted">
                  No tax lot data available
                </Text>
              )}
            </Box>

            {/* Realized */}
            <Box bg="bg.subtle" p={4} borderRadius="md">
              <HStack justify="space-between" mb={3}>
                <Heading size="sm">Realized Gains</Heading>
                <Select
                  size="xs"
                  w="auto"
                  value={gainsYear}
                  onChange={(e) => setGainsYear(parseInt(e.target.value))}
                >
                  {yearOptions.map((y) => (
                    <option key={y} value={y}>
                      {y}
                    </option>
                  ))}
                </Select>
              </HStack>
              {realizedLoading ? (
                <Spinner size="sm" />
              ) : realizedGains ? (
                <SimpleGrid columns={2} spacing={2}>
                  <Stat size="sm">
                    <StatLabel>Total Realized</StatLabel>
                    <StatNumber
                      fontSize="md"
                      color={
                        realizedGains.total_realized >= 0
                          ? "finance.positive"
                          : "finance.negative"
                      }
                    >
                      {formatCurrency(realizedGains.total_realized)}
                    </StatNumber>
                  </Stat>
                  <Stat size="sm">
                    <StatLabel>Short-Term</StatLabel>
                    <StatNumber fontSize="md">
                      {formatCurrency(realizedGains.short_term_gains)}
                    </StatNumber>
                  </Stat>
                  <Stat size="sm">
                    <StatLabel>Long-Term</StatLabel>
                    <StatNumber fontSize="md">
                      {formatCurrency(realizedGains.long_term_gains)}
                    </StatNumber>
                  </Stat>
                </SimpleGrid>
              ) : (
                <Text fontSize="sm" color="text.muted">
                  No realized gains this year
                </Text>
              )}
            </Box>
          </SimpleGrid>

          {/* Per-holding Tax Lots */}
          <Box>
            <HStack justify="space-between" mb={3}>
              <HStack spacing={3}>
                <Text fontWeight="semibold" fontSize="sm">
                  View Lots for:
                </Text>
                <Select
                  size="sm"
                  w="200px"
                  placeholder="Select holding"
                  value={selectedHoldingId || ""}
                  onChange={(e) => setSelectedHoldingId(e.target.value || null)}
                >
                  {holdings.map((h) => (
                    <option key={h.id} value={h.id}>
                      {h.ticker}
                    </option>
                  ))}
                </Select>
              </HStack>
              <HStack spacing={2}>
                <Text fontSize="xs" color="text.secondary">
                  Show closed
                </Text>
                <Switch
                  size="sm"
                  isChecked={includeClosed}
                  onChange={(e) => setIncludeClosed(e.target.checked)}
                />
              </HStack>
            </HStack>

            {selectedHoldingId &&
              (lotsLoading ? (
                <Spinner size="sm" />
              ) : taxLots && taxLots.length > 0 ? (
                <Table variant="simple" size="sm">
                  <Thead>
                    <Tr>
                      <Th>Acquired</Th>
                      <Th isNumeric>Qty</Th>
                      <Th isNumeric>Remaining</Th>
                      <Th isNumeric>Cost/Share</Th>
                      <Th isNumeric>Total Basis</Th>
                      <Th>Period</Th>
                      <Th>Status</Th>
                    </Tr>
                  </Thead>
                  <Tbody>
                    {taxLots.map((lot: TaxLot) => (
                      <Tr key={lot.id} opacity={lot.is_closed ? 0.5 : 1}>
                        <Td>
                          {new Date(lot.acquired_date).toLocaleDateString()}
                        </Td>
                        <Td isNumeric>{lot.quantity}</Td>
                        <Td isNumeric>{lot.remaining_quantity}</Td>
                        <Td isNumeric>
                          {formatCurrency(lot.cost_basis_per_share)}
                        </Td>
                        <Td isNumeric>
                          {formatCurrency(lot.total_cost_basis)}
                        </Td>
                        <Td>
                          <Badge
                            colorScheme={
                              lot.holding_period === "LONG_TERM"
                                ? "green"
                                : "orange"
                            }
                            size="sm"
                          >
                            {lot.holding_period === "LONG_TERM"
                              ? "Long"
                              : "Short"}
                          </Badge>
                        </Td>
                        <Td>
                          <Badge
                            colorScheme={lot.is_closed ? "gray" : "blue"}
                            size="sm"
                          >
                            {lot.is_closed ? "Closed" : "Open"}
                          </Badge>
                        </Td>
                      </Tr>
                    ))}
                  </Tbody>
                </Table>
              ) : (
                <Text
                  fontSize="sm"
                  color="text.muted"
                  textAlign="center"
                  py={4}
                >
                  No tax lots found. Use "Record Sale" to start tracking.
                </Text>
              ))}
          </Box>
        </VStack>

        {/* Record Sale Modal */}
        <Modal isOpen={isSaleOpen} onClose={onSaleClose} size="md">
          <ModalOverlay />
          <ModalContent>
            <ModalHeader>Record Sale</ModalHeader>
            <ModalCloseButton />
            <ModalBody>
              <VStack spacing={4}>
                <FormControl>
                  <FormLabel>Holding</FormLabel>
                  <Select
                    value={saleHoldingId}
                    onChange={(e) => setSaleHoldingId(e.target.value)}
                  >
                    {holdings.map((h) => (
                      <option key={h.id} value={h.id}>
                        {h.ticker} ({h.shares} shares)
                      </option>
                    ))}
                  </Select>
                </FormControl>
                <FormControl>
                  <FormLabel>Quantity</FormLabel>
                  <NumberInput
                    value={saleQuantity}
                    onChange={setSaleQuantity}
                    min={0}
                    precision={6}
                  >
                    <NumberInputField placeholder="Number of shares" />
                  </NumberInput>
                </FormControl>
                <FormControl>
                  <FormLabel>Sale Price per Share</FormLabel>
                  <NumberInput
                    value={salePrice}
                    onChange={setSalePrice}
                    min={0}
                    precision={2}
                  >
                    <NumberInputField placeholder="Price per share" />
                  </NumberInput>
                </FormControl>
                <FormControl>
                  <FormLabel>Sale Date</FormLabel>
                  <Input
                    type="date"
                    value={saleDate}
                    onChange={(e) => setSaleDate(e.target.value)}
                  />
                </FormControl>
                <FormControl>
                  <FormLabel>Cost Basis Method</FormLabel>
                  <Select
                    value={saleMethod}
                    onChange={(e) =>
                      setSaleMethod(
                        e.target.value as SaleRequest["cost_basis_method"],
                      )
                    }
                  >
                    <option value="FIFO">FIFO (First In, First Out)</option>
                    <option value="LIFO">LIFO (Last In, First Out)</option>
                    <option value="HIFO">HIFO (Highest In, First Out)</option>
                  </Select>
                </FormControl>
              </VStack>
            </ModalBody>
            <ModalFooter>
              <Button variant="ghost" mr={3} onClick={onSaleClose}>
                Cancel
              </Button>
              <Button
                colorScheme="brand"
                onClick={handleRecordSale}
                isLoading={saleMutation.isPending}
                isDisabled={!saleQuantity || !salePrice}
              >
                Record Sale
              </Button>
            </ModalFooter>
          </ModalContent>
        </Modal>
      </CardBody>
    </Card>
  );
};
