/**
 * Style Box Modal - Market Cap and Investment Style Breakdown
 */

import {
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalCloseButton,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Spinner,
  Center,
  Text,
  Box,
} from '@chakra-ui/react';
import { useQuery } from '@tanstack/react-query';
import { holdingsApi } from '../../../api/holdings';

interface StyleBoxModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function StyleBoxModal({ isOpen, onClose }: StyleBoxModalProps) {
  const { data: styleBoxData, isLoading } = useQuery({
    queryKey: ['style-box'],
    queryFn: holdingsApi.getStyleBox,
    enabled: isOpen, // Only fetch when modal is open
  });

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
    }).format(amount);
  };

  const formatPercent = (value: number) => {
    return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;
  };

  // Calculate grand total
  const grandTotal = styleBoxData?.reduce((sum, item) => sum + item.value, 0) || 0;

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="xl">
      <ModalOverlay />
      <ModalContent>
        <ModalHeader>Comprehensive Asset Allocation</ModalHeader>
        <ModalCloseButton />
        <ModalBody pb={6}>
          {isLoading ? (
            <Center py={8}>
              <Spinner size="lg" />
            </Center>
          ) : styleBoxData && styleBoxData.length > 0 ? (
            <Box overflowX="auto">
              <Table variant="simple" size="sm">
                <Thead>
                  <Tr>
                    <Th>Class</Th>
                    <Th isNumeric>% Total</Th>
                    <Th isNumeric>1-Day %</Th>
                    <Th isNumeric>Value</Th>
                  </Tr>
                </Thead>
                <Tbody>
                  {styleBoxData
                    .sort((a, b) => {
                      // Sort order: Domestic caps, International, Cash, Real Estate
                      const getOrder = (item: any) => {
                        if (item.style_class.includes('Large Cap')) return 1;
                        if (item.style_class.includes('Mid Cap')) return 2;
                        if (item.style_class.includes('Small Cap')) return 3;
                        if (item.style_class.includes('International')) return 4;
                        if (item.style_class.includes('Cash')) return 5;
                        if (item.style_class.includes('Real Estate')) return 6;
                        return 7;
                      };
                      return getOrder(a) - getOrder(b);
                    })
                    .map((item, index, array) => {
                      // Add section dividers
                      const prevItem = index > 0 ? array[index - 1] : null;
                      const showDivider = prevItem && (
                        (!prevItem.style_class.includes('Cap') && item.style_class.includes('Cap')) ||
                        (!prevItem.style_class.includes('International') && item.style_class.includes('International')) ||
                        (!prevItem.style_class.includes('Cash') && item.style_class.includes('Cash')) ||
                        (!prevItem.style_class.includes('Real Estate') && item.style_class.includes('Real Estate'))
                      );

                      return (
                        <>
                          {showDivider && (
                            <Tr>
                              <Td colSpan={4} py={0}>
                                <Box borderTop="1px solid" borderColor="border.default" />
                              </Td>
                            </Tr>
                          )}
                          <Tr key={item.style_class}>
                            <Td fontWeight="medium">{item.style_class}</Td>
                            <Td isNumeric>{Number(item.percentage).toFixed(2)}%</Td>
                            <Td
                              isNumeric
                              color={
                                item.one_day_change === null || Number(item.one_day_change) === 0
                                  ? 'text.muted'
                                  : Number(item.one_day_change) >= 0
                                  ? 'finance.positive'
                                  : 'finance.negative'
                              }
                            >
                              {item.one_day_change !== null && Number(item.one_day_change) !== 0
                                ? formatPercent(Number(item.one_day_change))
                                : '—'}
                            </Td>
                            <Td isNumeric>{formatCurrency(item.value)}</Td>
                          </Tr>
                        </>
                      );
                    })}
                  <Tr fontWeight="bold" bg="bg.subtle">
                    <Td>Grand Total</Td>
                    <Td isNumeric>100.00%</Td>
                    <Td isNumeric>—</Td>
                    <Td isNumeric>{formatCurrency(grandTotal)}</Td>
                  </Tr>
                </Tbody>
              </Table>
            </Box>
          ) : (
            <Center py={8}>
              <Text color="text.muted">No style box data available</Text>
            </Center>
          )}
        </ModalBody>
      </ModalContent>
    </Modal>
  );
}
