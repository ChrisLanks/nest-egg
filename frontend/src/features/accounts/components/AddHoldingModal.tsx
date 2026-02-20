import {
  Button,
  FormControl,
  FormLabel,
  HStack,
  Input,
  Modal,
  ModalBody,
  ModalCloseButton,
  ModalContent,
  ModalFooter,
  ModalHeader,
  ModalOverlay,
  NumberInput,
  NumberInputField,
  Select,
  Text,
  VStack,
  useToast,
} from '@chakra-ui/react';
import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../../../services/api';

interface AddHoldingModalProps {
  isOpen: boolean;
  onClose: () => void;
  accountId: string;
  accountName: string;
}

export const AddHoldingModal = ({
  isOpen,
  onClose,
  accountId,
  accountName,
}: AddHoldingModalProps) => {
  const toast = useToast();
  const queryClient = useQueryClient();

  const [ticker, setTicker] = useState('');
  const [name, setName] = useState('');
  const [shares, setShares] = useState('');
  const [costBasis, setCostBasis] = useState('');
  const [assetType, setAssetType] = useState('');

  const reset = () => {
    setTicker('');
    setName('');
    setShares('');
    setCostBasis('');
    setAssetType('');
  };

  const mutation = useMutation({
    mutationFn: async () => {
      const response = await api.post('/holdings/', {
        account_id: accountId,
        ticker: ticker.toUpperCase(),
        name: name || undefined,
        shares: parseFloat(shares),
        cost_basis_per_share: costBasis ? parseFloat(costBasis) : undefined,
        asset_type: assetType || undefined,
      });
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['holdings', accountId] });
      queryClient.invalidateQueries({ queryKey: ['portfolio-widget'] });
      toast({ title: 'Holding added', status: 'success', duration: 3000 });
      reset();
      onClose();
    },
    onError: (error: any) => {
      toast({
        title: 'Failed to add holding',
        description: error.response?.data?.detail || 'An error occurred',
        status: 'error',
        duration: 5000,
      });
    },
  });

  return (
    <Modal isOpen={isOpen} onClose={onClose}>
      <ModalOverlay />
      <ModalContent>
        <ModalHeader>Add Holding — {accountName}</ModalHeader>
        <ModalCloseButton />
        <ModalBody>
          <VStack spacing={4}>
            <FormControl isRequired>
              <FormLabel fontSize="sm">Ticker Symbol</FormLabel>
              <Input
                size="sm"
                value={ticker}
                onChange={(e) => setTicker(e.target.value.toUpperCase())}
                placeholder="e.g., AAPL, VTI, BND"
              />
            </FormControl>

            <FormControl>
              <FormLabel fontSize="sm">Name (optional)</FormLabel>
              <Input
                size="sm"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g., Vanguard Total Market ETF"
              />
            </FormControl>

            <FormControl isRequired>
              <FormLabel fontSize="sm">Shares</FormLabel>
              <NumberInput
                value={shares}
                onChange={setShares}
                min={0.000001}
                precision={6}
                size="sm"
              >
                <NumberInputField placeholder="0.000000" />
              </NumberInput>
            </FormControl>

            <FormControl>
              <FormLabel fontSize="sm">Cost Basis per Share (optional)</FormLabel>
              <HStack>
                <Text fontSize="sm">$</Text>
                <NumberInput
                  value={costBasis}
                  onChange={setCostBasis}
                  min={0}
                  precision={4}
                  size="sm"
                >
                  <NumberInputField placeholder="0.0000" />
                </NumberInput>
              </HStack>
            </FormControl>

            <FormControl>
              <FormLabel fontSize="sm">Asset Type (optional)</FormLabel>
              <Select
                size="sm"
                value={assetType}
                onChange={(e) => setAssetType(e.target.value)}
                placeholder="Select type"
              >
                <option value="stock">Stock</option>
                <option value="etf">ETF</option>
                <option value="mutual_fund">Mutual Fund</option>
                <option value="bond">Bond</option>
                <option value="cash">Cash</option>
                <option value="other">Other</option>
              </Select>
            </FormControl>
          </VStack>
        </ModalBody>

        <ModalFooter>
          <Button
            variant="ghost"
            mr={3}
            onClick={onClose}
            isDisabled={mutation.isPending}
          >
            Cancel
          </Button>
          <Button
            colorScheme="brand"
            onClick={() => mutation.mutate()}
            isLoading={mutation.isPending}
            isDisabled={!ticker || !shares}
          >
            Add Holding
          </Button>
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
};
