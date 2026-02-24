/**
 * Merchant select with autocomplete
 */

import {
  FormControl,
  FormLabel,
  Input,
  List,
  ListItem,
  Box,
  Text,
  useOutsideClick,
} from '@chakra-ui/react';
import { useState, useRef, useMemo, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import api from '../services/api';

interface MerchantSelectProps {
  value: string;
  onChange: (value: string) => void;
  label?: string;
  placeholder?: string;
  isRequired?: boolean;
  size?: 'sm' | 'md' | 'lg';
}

export const MerchantSelect = ({
  value,
  onChange,
  label = 'Merchant Name',
  placeholder = 'Type or select merchant',
  isRequired = false,
  size = 'md',
}: MerchantSelectProps) => {
  const [isOpen, setIsOpen] = useState(false);
  const [inputValue, setInputValue] = useState(value);
  const wrapperRef = useRef<HTMLDivElement>(null);

  // Fetch all unique merchant names via dedicated endpoint (up to 500, sorted)
  const { data: merchants } = useQuery({
    queryKey: ['merchants'],
    queryFn: async () => {
      const response = await api.get('/transactions/merchants');
      return response.data.merchants as string[];
    },
    staleTime: 5 * 60 * 1000, // Cache for 5 minutes
  });

  // Filter merchants based on input
  const filteredMerchants = useMemo(() => {
    if (!merchants) return [];
    if (!inputValue.trim()) return merchants.slice(0, 20); // Show only 20 when empty

    const searchTerm = inputValue.toLowerCase();
    return merchants
      .filter((merchant) =>
        merchant.toLowerCase().includes(searchTerm)
      )
      .slice(0, 20); // Limit to 20 results
  }, [merchants, inputValue]);

  useOutsideClick({
    ref: wrapperRef,
    handler: () => setIsOpen(false),
  });

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newValue = e.target.value;
    setInputValue(newValue);
    setIsOpen(true);
    onChange(newValue);
  };

  const handleSelectMerchant = (merchant: string) => {
    setInputValue(merchant);
    onChange(merchant);
    setIsOpen(false);
  };

  const handleInputFocus = () => {
    setIsOpen(true);
  };

  // Sync controlled value into local input state
  useEffect(() => {
    setInputValue(value);
  }, [value]);

  return (
    <FormControl isRequired={isRequired} ref={wrapperRef} position="relative">
      {label && <FormLabel>{label}</FormLabel>}
      <Input
        size={size}
        value={inputValue}
        onChange={handleInputChange}
        onFocus={handleInputFocus}
        placeholder={placeholder}
        autoComplete="off"
      />

      {/* Dropdown menu */}
      {isOpen && filteredMerchants.length > 0 && (
        <Box
          position="absolute"
          top="100%"
          left={0}
          right={0}
          mt={1}
          bg="bg.surface"
          borderWidth={1}
          borderRadius="md"
          boxShadow="lg"
          maxH="300px"
          overflowY="auto"
          zIndex={1000}
        >
          <List>
            {filteredMerchants.map((merchant) => (
              <ListItem
                key={merchant}
                px={4}
                py={2}
                cursor="pointer"
                _hover={{ bg: 'bg.muted' }}
                onClick={() => handleSelectMerchant(merchant)}
              >
                <Text>{merchant}</Text>
              </ListItem>
            ))}
          </List>
        </Box>
      )}
    </FormControl>
  );
};
