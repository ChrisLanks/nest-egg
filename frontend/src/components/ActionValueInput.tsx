/**
 * Smart action value input with autocomplete based on action type
 */

import { Input, FormControl } from '@chakra-ui/react';
import { ActionType } from '../types/rule';
import { CategorySelect } from './CategorySelect';
import { MerchantSelect } from './MerchantSelect';

interface ActionValueInputProps {
  actionType: ActionType;
  value: string;
  onChange: (value: string) => void;
  size?: 'sm' | 'md' | 'lg';
}

export const ActionValueInput = ({
  actionType,
  value,
  onChange,
  size = 'sm',
}: ActionValueInputProps) => {
  // Use CategorySelect for SET_CATEGORY action
  if (actionType === ActionType.SET_CATEGORY) {
    return (
      <FormControl flex={2}>
        <CategorySelect
          value={value}
          onChange={onChange}
          label=""
          placeholder="Category name"
          size={size}
        />
      </FormControl>
    );
  }

  // Use MerchantSelect for SET_MERCHANT action
  if (actionType === ActionType.SET_MERCHANT) {
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

  // For label actions, use text input (could enhance with label selector later)
  return (
    <FormControl flex={2}>
      <Input
        size={size}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={
          actionType === ActionType.ADD_LABEL ||
          actionType === ActionType.REMOVE_LABEL
            ? 'Label name'
            : 'Value'
        }
      />
    </FormControl>
  );
};
