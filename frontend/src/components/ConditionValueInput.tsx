/**
 * Smart condition value input with autocomplete based on field type
 */

import { Input, FormControl } from '@chakra-ui/react';
import { ConditionField } from '../types/rule';
import { CategorySelect } from './CategorySelect';
import { MerchantSelect } from './MerchantSelect';

interface ConditionValueInputProps {
  field: ConditionField;
  value: string;
  onChange: (value: string) => void;
  size?: 'sm' | 'md' | 'lg';
}

export const ConditionValueInput = ({
  field,
  value,
  onChange,
  size = 'sm',
}: ConditionValueInputProps) => {
  // Use autocomplete for merchant and category fields
  if (field === ConditionField.MERCHANT_NAME) {
    return (
      <FormControl flex={2}>
        <MerchantSelect
          value={value}
          onChange={onChange}
          label=""
          placeholder="Merchant name"
          size={size}
        />
      </FormControl>
    );
  }

  if (field === ConditionField.CATEGORY) {
    return (
      <FormControl flex={2}>
        <CategorySelect
          value={value}
          onChange={onChange}
          label=""
          placeholder="Category"
          size={size}
        />
      </FormControl>
    );
  }

  // For amount fields, use number input
  if (
    field === ConditionField.AMOUNT ||
    field === ConditionField.AMOUNT_EXACT
  ) {
    return (
      <FormControl flex={2}>
        <Input
          size={size}
          type="number"
          step="0.01"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder="Amount"
        />
      </FormControl>
    );
  }

  // Default to text input
  return (
    <FormControl flex={2}>
      <Input
        size={size}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="Value"
      />
    </FormControl>
  );
};
