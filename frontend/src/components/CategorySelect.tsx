/**
 * Category select with autocomplete and create new option
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
import { useState, useRef, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import api from '../services/api';
import { categoriesApi } from '../api/categories';

interface CategorySelectProps {
  value: string;
  onChange: (value: string) => void;
  label?: string;
  placeholder?: string;
  isRequired?: boolean;
  size?: 'sm' | 'md' | 'lg';
}

export const CategorySelect = ({
  value,
  onChange,
  label = 'Category',
  placeholder = 'Type or select category',
  isRequired = false,
  size = 'md',
}: CategorySelectProps) => {
  const [isOpen, setIsOpen] = useState(false);
  const [inputValue, setInputValue] = useState(value);
  const wrapperRef = useRef<HTMLDivElement>(null);

  // Fetch registered categories (shared cache with BudgetForm)
  const { data: registeredCategories = [] } = useQuery({
    queryKey: ['categories'],
    queryFn: categoriesApi.getCategories,
    staleTime: 5 * 60 * 1000,
  });

  // Fetch category names that appear in transactions
  const { data: transactionCategoryNames = [] } = useQuery({
    queryKey: ['transaction-category-names'],
    queryFn: async () => {
      const response = await api.get('/transactions', {
        params: { page_size: 1000 },
      });
      const transactions = response.data.transactions;
      const uniqueNames = new Set<string>();
      transactions.forEach((txn: any) => {
        if (txn.category_primary) {
          uniqueNames.add(txn.category_primary);
        }
      });
      return Array.from(uniqueNames);
    },
    staleTime: 5 * 60 * 1000,
  });

  // Merge and deduplicate: registered category names + transaction-derived names
  const categories = useMemo(() => {
    const names = new Set<string>([
      ...registeredCategories.map((c) => c.name),
      ...transactionCategoryNames,
    ]);
    return Array.from(names).sort();
  }, [registeredCategories, transactionCategoryNames]);

  // Filter categories based on input
  const filteredCategories = useMemo(() => {
    if (!categories.length) return [];
    if (!inputValue.trim()) return categories;

    const searchTerm = inputValue.toLowerCase();
    return categories.filter((cat) =>
      cat.toLowerCase().includes(searchTerm)
    );
  }, [categories, inputValue]);

  // Check if current input is a new category
  const isNewCategory = useMemo(() => {
    if (!inputValue.trim()) return false;
    return !categories?.some(
      (cat) => cat.toLowerCase() === inputValue.toLowerCase()
    );
  }, [categories, inputValue]);

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

  const handleSelectCategory = (category: string) => {
    setInputValue(category);
    onChange(category);
    setIsOpen(false);
  };

  const handleInputFocus = () => {
    setIsOpen(true);
  };

  // Update input value when prop value changes
  useMemo(() => {
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
      {isOpen && (filteredCategories.length > 0 || isNewCategory) && (
        <Box
          position="absolute"
          top="100%"
          left={0}
          right={0}
          mt={1}
          bg="white"
          borderWidth={1}
          borderRadius="md"
          boxShadow="lg"
          maxH="200px"
          overflowY="auto"
          zIndex={1000}
        >
          <List>
            {isNewCategory && inputValue.trim() && (
              <ListItem
                px={4}
                py={2}
                cursor="pointer"
                bg="blue.50"
                borderBottomWidth={filteredCategories.length > 0 ? 1 : 0}
                _hover={{ bg: 'blue.100' }}
                onClick={() => handleSelectCategory(inputValue)}
              >
                <Text fontWeight="medium" color="blue.600">
                  Create new: "{inputValue}"
                </Text>
              </ListItem>
            )}

            {filteredCategories.map((category) => (
              <ListItem
                key={category}
                px={4}
                py={2}
                cursor="pointer"
                _hover={{ bg: 'gray.100' }}
                onClick={() => handleSelectCategory(category)}
              >
                <Text>{category}</Text>
              </ListItem>
            ))}
          </List>
        </Box>
      )}
    </FormControl>
  );
};
